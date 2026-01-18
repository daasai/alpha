"""
数据缓存模块
"""

import hashlib
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from .logging_config import get_logger

logger = get_logger(__name__)


class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, cache_dir: str = 'data/cache'):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录路径
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"缓存目录: {self.cache_dir}")
    
    def _get_cache_key(self, func_name: str, params: dict) -> str:
        """
        生成缓存键
        
        Args:
            func_name: 函数名称
            params: 参数字典
        
        Returns:
            缓存键（MD5哈希）
        """
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{func_name}:{params_str}".encode()).hexdigest()
    
    def get(self, func_name: str, params: dict, max_age_hours: int = 24) -> Optional[pd.DataFrame]:
        """
        获取缓存数据
        
        Args:
            func_name: 函数名称
            params: 参数字典
            max_age_hours: 最大缓存时长（小时）
        
        Returns:
            缓存的数据（如果存在且未过期），否则返回 None
        """
        cache_key = self._get_cache_key(func_name, params)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if not cache_file.exists():
            logger.debug(f"缓存未找到: {cache_key}")
            return None
        
        # 检查缓存是否过期
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > timedelta(hours=max_age_hours):
            logger.debug(f"缓存已过期: {cache_key}, 年龄: {file_age}")
            return None
        
        # 读取缓存
        try:
            result = pd.read_pickle(cache_file)
            logger.info(f"缓存命中: {cache_key}")
            return result
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            return None
    
    def set(self, func_name: str, params: dict, data: pd.DataFrame):
        """
        设置缓存
        
        Args:
            func_name: 函数名称
            params: 参数字典
            data: 要缓存的数据
        """
        cache_key = self._get_cache_key(func_name, params)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        try:
            data.to_pickle(cache_file)
            logger.debug(f"缓存已保存: {cache_key}")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def clear(self, pattern: Optional[str] = None):
        """
        清除缓存
        
        Args:
            pattern: 可选的文件名模式，如果提供则只清除匹配的缓存
        """
        if pattern:
            cache_files = list(self.cache_dir.glob(f"{pattern}*"))
            for cache_file in cache_files:
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.error(f"删除缓存文件失败: {cache_file}: {e}")
        else:
            # 清除所有缓存
            for cache_file in self.cache_dir.iterdir():
                if cache_file.is_file() and cache_file.suffix == '.pkl':
                    try:
                        cache_file.unlink()
                    except Exception as e:
                        logger.error(f"删除缓存文件失败: {cache_file}: {e}")
        
        logger.info("缓存已清除")
