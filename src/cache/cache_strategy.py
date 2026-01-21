"""
Cache Strategy - 缓存策略接口和实现
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
import pandas as pd

from ..logging_config import get_logger

logger = get_logger(__name__)


class CacheStrategy(ABC):
    """缓存策略抽象基类"""
    
    @abstractmethod
    def get(self, key: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            **kwargs: 其他参数
            
        Returns:
            缓存的数据，如果不存在则返回 None
        """
        pass
    
    @abstractmethod
    def set(self, key: str, data: pd.DataFrame, **kwargs) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            **kwargs: 其他参数（如 ttl）
        """
        pass
    
    @abstractmethod
    def invalidate(self, pattern: str) -> None:
        """
        使缓存失效
        
        Args:
            pattern: 匹配模式
        """
        pass


class DatabaseCacheStrategy(CacheStrategy):
    """数据库缓存策略"""
    
    def __init__(self):
        """初始化数据库缓存策略"""
        from ..database import (
            get_cached_constituents,
            save_constituents,
            get_cached_daily_history,
            save_daily_history_batch,
            clear_old_constituents,
            clear_old_daily_history,
        )
        self._get_cached_constituents = get_cached_constituents
        self._save_constituents = save_constituents
        self._get_cached_daily_history = get_cached_daily_history
        self._save_daily_history_batch = save_daily_history_batch
        self._clear_old_constituents = clear_old_constituents
        self._clear_old_daily_history = clear_old_daily_history
    
    def get(self, key: str, **kwargs) -> Optional[pd.DataFrame]:
        """
        获取缓存数据
        
        支持的 key 格式:
        - 'constituents:{index_code}:{trade_date}' - 获取指数成分股
        - 'daily_history:{ts_codes}:{start_date}:{end_date}' - 获取历史日线数据
        
        Args:
            key: 缓存键
            **kwargs: 其他参数
            
        Returns:
            缓存的数据，如果不存在则返回 None
        """
        try:
            if key.startswith('constituents:'):
                # 解析成分股缓存键
                parts = key.split(':')
                if len(parts) >= 3:
                    index_code = parts[1]
                    trade_date = parts[2]
                    constituents = self._get_cached_constituents(index_code, trade_date)
                    if constituents:
                        # 转换为 DataFrame
                        df = pd.DataFrame({'ts_code': constituents})
                        return df
                return None
            
            elif key.startswith('daily_history:'):
                # 解析历史数据缓存键
                parts = key.split(':')
                if len(parts) >= 4:
                    ts_codes_str = parts[1]
                    start_date = parts[2]
                    end_date = parts[3]
                    ts_codes = ts_codes_str.split(',') if ts_codes_str else []
                    df = self._get_cached_daily_history(ts_codes, start_date, end_date)
                    return df if not df.empty else None
                return None
            
            else:
                logger.warning(f"不支持的缓存键格式: {key}")
                return None
                
        except Exception as e:
            logger.error(f"获取缓存失败 ({key}): {e}")
            return None
    
    def set(self, key: str, data: pd.DataFrame, **kwargs) -> None:
        """
        设置缓存数据
        
        支持的 key 格式:
        - 'constituents:{index_code}:{trade_date}' - 保存指数成分股
        - 'daily_history' - 保存历史日线数据（需要额外参数）
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            **kwargs: 其他参数
                - index_code: 指数代码（用于成分股）
                - trade_date: 交易日期（用于成分股）
                - ts_codes: 股票代码列表（用于历史数据）
        """
        try:
            if key.startswith('constituents:'):
                # 保存成分股
                parts = key.split(':')
                if len(parts) >= 3:
                    index_code = parts[1]
                    trade_date = parts[2]
                    
                    # 将 DataFrame 转换为字典列表
                    constituents_data = []
                    if 'ts_code' in data.columns:
                        for _, row in data.iterrows():
                            constituents_data.append({
                                'ts_code': str(row['ts_code']),
                                'weight': float(row['weight']) if 'weight' in data.columns and pd.notna(row.get('weight')) else None
                            })
                    
                    if constituents_data:
                        self._save_constituents(index_code, trade_date, constituents_data)
                        logger.debug(f"保存成分股缓存: {key}, 数量: {len(constituents_data)}")
            
            elif key == 'daily_history':
                # 保存历史数据
                if not data.empty:
                    self._save_daily_history_batch(data)
                    logger.debug(f"保存历史数据缓存: {len(data)} 条记录")
            
            else:
                logger.warning(f"不支持的缓存键格式: {key}")
                
        except Exception as e:
            logger.error(f"保存缓存失败 ({key}): {e}")
            raise
    
    def invalidate(self, pattern: str) -> None:
        """
        使缓存失效
        
        Args:
            pattern: 匹配模式
                - 'constituents:{index_code}:*' - 清除指定指数的所有成分股缓存
                - 'constituents:{index_code}:{before_date}' - 清除指定日期之前的成分股缓存
                - 'daily_history:{before_date}' - 清除指定日期之前的历史数据缓存
        """
        try:
            if pattern.startswith('constituents:'):
                parts = pattern.split(':')
                if len(parts) >= 2:
                    index_code = parts[1]
                    if len(parts) >= 3 and parts[2] != '*':
                        before_date = parts[2]
                        self._clear_old_constituents(index_code, before_date)
                        logger.info(f"清除成分股缓存: {index_code}, 日期 < {before_date}")
                    else:
                        # 清除所有（需要实现，暂时不支持）
                        logger.warning("清除所有成分股缓存暂不支持，请指定日期")
            
            elif pattern.startswith('daily_history:'):
                parts = pattern.split(':')
                if len(parts) >= 2:
                    before_date = parts[1]
                    self._clear_old_daily_history(before_date)
                    logger.info(f"清除历史数据缓存: 日期 < {before_date}")
            
            else:
                logger.warning(f"不支持的缓存失效模式: {pattern}")
                
        except Exception as e:
            logger.error(f"清除缓存失败 ({pattern}): {e}")
