"""
History Repository - 历史数据访问
"""

from typing import List, Optional
import pandas as pd
from ..database import (
    get_cached_daily_history,
    save_daily_history_batch,
    clear_old_daily_history
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class HistoryRepository:
    """历史数据Repository"""
    
    def get_cached(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        从缓存获取历史数据
        
        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            
        Returns:
            历史数据DataFrame
        """
        return get_cached_daily_history(ts_codes, start_date, end_date)
    
    def save_batch(self, df: pd.DataFrame) -> None:
        """
        批量保存历史数据到缓存
        
        Args:
            df: 历史数据DataFrame
        """
        save_daily_history_batch(df)
        logger.debug(f"保存 {len(df)} 条历史数据到缓存")
    
    def clear_old(self, before_date: str) -> None:
        """
        清理指定日期之前的旧数据
        
        Args:
            before_date: 清理此日期之前的数据 (YYYYMMDD)
        """
        clear_old_daily_history(before_date)
