"""
Truth Service - 复盘验证业务逻辑
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import time

from .base_service import BaseService
from ..strategy import get_trade_date
from ..database import (
    get_all_predictions,
    update_prediction_price,
    update_prediction_price_at_prediction
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class TruthResult:
    """Truth更新结果"""
    
    def __init__(
        self,
        success: bool,
        updated_count: int = 0,
        total_count: int = 0,
        error: Optional[str] = None
    ):
        self.success = success
        self.updated_count = updated_count
        self.total_count = total_count
        self.error = error


class TruthService(BaseService):
    """Truth服务 - 复盘验证业务逻辑"""
    
    def update_prices(self) -> TruthResult:
        """
        更新所有预测记录的最新价格
        
        Returns:
            TruthResult: 更新结果
        """
        try:
            logger.info("Truth 更新开始")
            
            # 从数据库读取预测记录
            all_predictions = get_all_predictions()
            
            if not all_predictions:
                return TruthResult(
                    success=True,
                    updated_count=0,
                    total_count=0
                )
            
            # 获取当前交易日期
            current_trade_date = get_trade_date()
            
            # 从配置获取API延迟
            api_delay = self.config.get('api_rate_limit.tushare_delay', 0.1)
            
            updated_count = 0
            for i, pred in enumerate(all_predictions):
                ts_code = pred["ts_code"]
                pred_date = pred["trade_date"]
                
                try:
                    # 获取预测日期的价格（作为当时价格）
                    pred_daily = self.data_provider._pro.daily(
                        ts_code=ts_code,
                        trade_date=pred_date,
                        fields="ts_code,trade_date,close"
                    )
                    
                    # 获取最新价格
                    latest_daily = self.data_provider._pro.daily(
                        ts_code=ts_code,
                        trade_date=current_trade_date,
                        fields="ts_code,trade_date,close"
                    )
                    
                    if not pred_daily.empty and not latest_daily.empty:
                        price_at_pred = pred_daily.iloc[0]["close"]
                        current_price = latest_daily.iloc[0]["close"]
                        
                        # 计算收益率
                        if price_at_pred > 0:
                            return_pct = (current_price - price_at_pred) / price_at_pred * 100
                            
                            # 如果 price_at_prediction 为空，先更新它
                            if pd.isna(pred.get("price_at_prediction")):
                                update_prediction_price_at_prediction(
                                    pred_date, 
                                    ts_code, 
                                    price_at_pred
                                )
                            
                            # 更新最新价格和收益率
                            update_prediction_price(
                                pred_date, 
                                ts_code, 
                                current_price, 
                                return_pct
                            )
                            updated_count += 1
                    
                    # API 限流
                    time.sleep(api_delay)
                    
                    if (i + 1) % 10 == 0:
                        logger.debug(f"已处理 {i+1}/{len(all_predictions)} 条记录...")
                
                except Exception as e:
                    logger.debug(f"更新 {ts_code} 失败: {e}")
                    continue
            
            logger.info(f"Truth 更新完成: 更新 {updated_count} 条")
            
            return TruthResult(
                success=True,
                updated_count=updated_count,
                total_count=len(all_predictions)
            )
            
        except Exception as e:
            logger.exception("Truth 更新异常")
            return TruthResult(
                success=False,
                error=f"更新过程出错: {str(e)}"
            )
    
    def get_verification_data(self) -> pd.DataFrame:
        """
        获取验证数据（所有预测记录）
        
        Returns:
            DataFrame: 包含所有预测记录的DataFrame
        """
        all_predictions = get_all_predictions()
        if not all_predictions:
            return pd.DataFrame()
        
        return pd.DataFrame(all_predictions)
    
    def calculate_win_rate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算胜率
        
        Args:
            df: 包含预测记录的DataFrame
            
        Returns:
            Dict包含: win_rate, win_count, total_count
        """
        verified_df = df[df["actual_chg"].notna()]
        if verified_df.empty:
            return {
                'win_rate': 0.0,
                'win_count': 0,
                'total_count': 0
            }
        
        win_count = len(verified_df[verified_df["actual_chg"] > 0])
        total_count = len(verified_df)
        win_rate = (win_count / total_count * 100) if total_count > 0 else 0.0
        
        return {
            'win_rate': win_rate,
            'win_count': win_count,
            'total_count': total_count
        }
