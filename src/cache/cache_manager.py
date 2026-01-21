"""
Cache Manager - 统一缓存管理
提供统一的缓存接口，支持 TTL、缓存预热等功能
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

from .cache_strategy import CacheStrategy, DatabaseCacheStrategy
from ..logging_config import get_logger
from ..config_manager import ConfigManager

logger = get_logger(__name__)


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, strategy: Optional[CacheStrategy] = None, config: Optional[ConfigManager] = None):
        """
        初始化缓存管理器
        
        Args:
            strategy: 缓存策略，如果为 None 则使用 DatabaseCacheStrategy
            config: 配置管理器，如果为 None 则创建新实例
        """
        if strategy is None:
            self.strategy = DatabaseCacheStrategy()
        else:
            self.strategy = strategy
        
        if config is None:
            self.config = ConfigManager()
        else:
            self.config = config
        
        # 默认 TTL（天）
        self._default_ttl_days = self.config.get('cache.default_ttl_days', 30)
        
        # 缓存元数据（用于 TTL 管理）
        self._cache_metadata: Dict[str, datetime] = {}
        
        logger.info("CacheManager 初始化完成")
    
    def _generate_key(self, cache_type: str, *args, **kwargs) -> str:
        """
        生成缓存键
        
        Args:
            cache_type: 缓存类型（'constituents', 'daily_history'）
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            缓存键字符串
        """
        if cache_type == 'constituents':
            index_code = kwargs.get('index_code', args[0] if args else '')
            trade_date = kwargs.get('trade_date', args[1] if len(args) > 1 else '')
            return f"constituents:{index_code}:{trade_date}"
        
        elif cache_type == 'daily_history':
            ts_codes = kwargs.get('ts_codes', args[0] if args else [])
            start_date = kwargs.get('start_date', args[1] if len(args) > 1 else '')
            end_date = kwargs.get('end_date', args[2] if len(args) > 2 else '')
            ts_codes_str = ','.join(sorted(ts_codes)) if isinstance(ts_codes, list) else str(ts_codes)
            return f"daily_history:{ts_codes_str}:{start_date}:{end_date}"
        
        else:
            raise ValueError(f"不支持的缓存类型: {cache_type}")
    
    def get(
        self,
        cache_type: str,
        ttl_days: Optional[int] = None,
        **kwargs
    ) -> Optional[pd.DataFrame]:
        """
        获取缓存数据
        
        Args:
            cache_type: 缓存类型（'constituents', 'daily_history'）
            ttl_days: TTL（天），如果为 None 则使用默认值
            **kwargs: 缓存参数
                - constituents: index_code, trade_date
                - daily_history: ts_codes, start_date, end_date
                
        Returns:
            缓存的数据，如果不存在或已过期则返回 None
        """
        key = self._generate_key(cache_type, **kwargs)
        
        # 检查 TTL
        if ttl_days is None:
            ttl_days = self._default_ttl_days
        
        if key in self._cache_metadata:
            cache_time = self._cache_metadata[key]
            age = (datetime.now() - cache_time).days
            if age > ttl_days:
                logger.debug(f"缓存已过期: {key}, 年龄: {age} 天, TTL: {ttl_days} 天")
                del self._cache_metadata[key]
                return None
        
        # 从策略获取数据
        result = self.strategy.get(key, **kwargs)
        
        if result is not None and not result.empty:
            # 更新元数据
            self._cache_metadata[key] = datetime.now()
            logger.debug(f"缓存命中: {key}")
        else:
            logger.debug(f"缓存未命中: {key}")
        
        return result
    
    def set(
        self,
        cache_type: str,
        data: pd.DataFrame,
        ttl_days: Optional[int] = None,
        **kwargs
    ) -> None:
        """
        设置缓存数据
        
        Args:
            cache_type: 缓存类型（'constituents', 'daily_history'）
            data: 要缓存的数据
            ttl_days: TTL（天），如果为 None 则使用默认值
            **kwargs: 缓存参数
                - constituents: index_code, trade_date
                - daily_history: ts_codes (可选，从 data 中提取)
        """
        if data.empty:
            logger.warning(f"尝试缓存空数据: {cache_type}")
            return
        
        key = self._generate_key(cache_type, **kwargs)
        
        # 保存到策略
        if cache_type == 'constituents':
            self.strategy.set(key, data, **kwargs)
        elif cache_type == 'daily_history':
            self.strategy.set('daily_history', data, **kwargs)
        else:
            raise ValueError(f"不支持的缓存类型: {cache_type}")
        
        # 更新元数据
        self._cache_metadata[key] = datetime.now()
        
        if ttl_days is None:
            ttl_days = self._default_ttl_days
        
        logger.debug(f"缓存已保存: {key}, TTL: {ttl_days} 天")
    
    def invalidate(self, pattern: str) -> None:
        """
        使缓存失效
        
        Args:
            pattern: 匹配模式
                - 'constituents:{index_code}:*' - 清除指定指数的所有成分股缓存
                - 'constituents:{index_code}:{before_date}' - 清除指定日期之前的成分股缓存
                - 'daily_history:{before_date}' - 清除指定日期之前的历史数据缓存
        """
        self.strategy.invalidate(pattern)
        
        # 清除相关元数据
        if pattern.startswith('constituents:'):
            parts = pattern.split(':')
            if len(parts) >= 2:
                index_code = parts[1]
                keys_to_remove = [
                    k for k in self._cache_metadata.keys()
                    if k.startswith(f"constituents:{index_code}:")
                ]
                for k in keys_to_remove:
                    del self._cache_metadata[k]
        
        elif pattern.startswith('daily_history:'):
            keys_to_remove = [
                k for k in self._cache_metadata.keys()
                if k.startswith("daily_history:")
            ]
            for k in keys_to_remove:
                del self._cache_metadata[k]
    
    def warm_up(self, keys: List[str]) -> None:
        """
        缓存预热（预加载常用数据）
        
        Args:
            keys: 缓存键列表
        """
        logger.info(f"开始缓存预热，共 {len(keys)} 个键")
        
        for key in keys:
            try:
                # 尝试获取缓存（如果不存在则不会报错）
                if key.startswith('constituents:'):
                    parts = key.split(':')
                    if len(parts) >= 3:
                        index_code = parts[1]
                        trade_date = parts[2]
                        self.get('constituents', index_code=index_code, trade_date=trade_date)
                
                elif key.startswith('daily_history:'):
                    parts = key.split(':')
                    if len(parts) >= 4:
                        ts_codes_str = parts[1]
                        start_date = parts[2]
                        end_date = parts[3]
                        ts_codes = ts_codes_str.split(',') if ts_codes_str else []
                        self.get('daily_history', ts_codes=ts_codes, start_date=start_date, end_date=end_date)
                
            except Exception as e:
                logger.warning(f"缓存预热失败 ({key}): {e}")
        
        logger.info("缓存预热完成")
    
    def get_constituents(self, index_code: str, trade_date: str, ttl_days: Optional[int] = None) -> Optional[List[str]]:
        """
        获取指数成分股（便捷方法）
        
        Args:
            index_code: 指数代码
            trade_date: 交易日期
            ttl_days: TTL（天）
            
        Returns:
            成分股代码列表，如果不存在则返回 None
        """
        df = self.get('constituents', index_code=index_code, trade_date=trade_date, ttl_days=ttl_days)
        if df is not None and not df.empty and 'ts_code' in df.columns:
            return df['ts_code'].tolist()
        return None
    
    def set_constituents(
        self,
        index_code: str,
        trade_date: str,
        constituents: List[str],
        weights: Optional[List[float]] = None,
        ttl_days: Optional[int] = None
    ) -> None:
        """
        保存指数成分股（便捷方法）
        
        Args:
            index_code: 指数代码
            trade_date: 交易日期
            constituents: 成分股代码列表
            weights: 权重列表（可选）
            ttl_days: TTL（天）
        """
        data = {'ts_code': constituents}
        if weights:
            data['weight'] = weights
        
        df = pd.DataFrame(data)
        self.set('constituents', df, index_code=index_code, trade_date=trade_date, ttl_days=ttl_days)
    
    def get_daily_history(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: str,
        ttl_days: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取历史日线数据（便捷方法）
        
        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            ttl_days: TTL（天）
            
        Returns:
            历史数据 DataFrame，如果不存在则返回 None
        """
        return self.get(
            'daily_history',
            ts_codes=ts_codes,
            start_date=start_date,
            end_date=end_date,
            ttl_days=ttl_days
        )
    
    def set_daily_history(
        self,
        data: pd.DataFrame,
        ttl_days: Optional[int] = None
    ) -> None:
        """
        保存历史日线数据（便捷方法）
        
        Args:
            data: 历史数据 DataFrame
            ttl_days: TTL（天）
        """
        self.set('daily_history', data, ttl_days=ttl_days)
