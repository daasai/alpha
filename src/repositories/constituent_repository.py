"""
Constituent Repository - 指数成分股数据访问
"""

from typing import List, Dict, Any
from ..database import (
    get_cached_constituents,
    save_constituents,
    get_latest_constituents_date,
    clear_old_constituents
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class ConstituentRepository:
    """指数成分股Repository"""
    
    def get_cached(
        self,
        index_code: str,
        trade_date: str
    ) -> List[str]:
        """
        从缓存获取成分股列表
        
        Args:
            index_code: 指数代码
            trade_date: 交易日期 (YYYYMMDD)
            
        Returns:
            成分股代码列表
        """
        return get_cached_constituents(index_code, trade_date)
    
    def save(
        self,
        index_code: str,
        trade_date: str,
        constituents_data: List[Dict[str, Any]]
    ) -> None:
        """
        保存成分股数据到缓存
        
        Args:
            index_code: 指数代码
            trade_date: 生效日期 (YYYYMMDD)
            constituents_data: 成分股数据列表
        """
        save_constituents(index_code, trade_date, constituents_data)
        logger.debug(f"保存 {len(constituents_data)} 条成分股数据: {index_code}, {trade_date}")
    
    def get_latest_date(self, index_code: str) -> str:
        """
        获取缓存中最新一期的生效日期
        
        Args:
            index_code: 指数代码
            
        Returns:
            最新生效日期 (YYYYMMDD)，如果不存在返回空字符串
        """
        return get_latest_constituents_date(index_code)
    
    def clear_old(self, index_code: str, before_date: str) -> None:
        """
        清理指定日期之前的旧数据
        
        Args:
            index_code: 指数代码
            before_date: 清理此日期之前的数据 (YYYYMMDD)
        """
        clear_old_constituents(index_code, before_date)
