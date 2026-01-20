"""
Prediction Repository - 预测记录数据访问
"""

from typing import List, Dict, Any, Optional
from ..database import (
    save_daily_predictions,
    get_all_predictions,
    get_pending_predictions,
    get_verified_predictions,
    update_prediction_price,
    update_prediction_price_at_prediction,
    update_actual_performance
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class PredictionRepository:
    """预测记录Repository"""
    
    def save_predictions(self, predictions: List[Dict[str, Any]]) -> None:
        """
        保存预测记录
        
        Args:
            predictions: 预测记录列表
        """
        save_daily_predictions(predictions)
        logger.debug(f"保存 {len(predictions)} 条预测记录")
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        获取所有预测记录
        
        Returns:
            预测记录列表
        """
        return get_all_predictions()
    
    def get_pending(self) -> List[Dict[str, Any]]:
        """
        获取待验证的预测记录（actual_chg为NULL）
        
        Returns:
            预测记录列表
        """
        return get_pending_predictions()
    
    def get_verified(self) -> List[Dict[str, Any]]:
        """
        获取已验证的预测记录（actual_chg非NULL）
        
        Returns:
            预测记录列表
        """
        return get_verified_predictions()
    
    def update_price(
        self,
        trade_date: str,
        ts_code: str,
        current_price: float,
        return_pct: float
    ) -> None:
        """
        更新预测记录的最新价格和收益率
        
        Args:
            trade_date: 交易日期
            ts_code: 股票代码
            current_price: 最新价格
            return_pct: 收益率百分比
        """
        update_prediction_price(trade_date, ts_code, current_price, return_pct)
    
    def update_price_at_prediction(
        self,
        trade_date: str,
        ts_code: str,
        price: float
    ) -> None:
        """
        更新预测时的价格
        
        Args:
            trade_date: 交易日期
            ts_code: 股票代码
            price: 预测时的价格
        """
        update_prediction_price_at_prediction(trade_date, ts_code, price)
    
    def update_performance(
        self,
        trade_date: str,
        ts_code: str,
        chg: float
    ) -> None:
        """
        更新实际表现
        
        Args:
            trade_date: 交易日期
            ts_code: 股票代码
            chg: 涨跌幅百分比
        """
        update_actual_performance(trade_date, ts_code, chg)
