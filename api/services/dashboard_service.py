"""
Dashboard Service - 驾驶舱业务逻辑
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.logging_config import get_logger

logger = get_logger(__name__)


class DashboardService:
    """Dashboard服务"""
    
    def __init__(self, data_provider: DataProvider, config: ConfigManager):
        self.data_provider = data_provider
        self.config = config
    
    def get_overview(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取市场概览
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)，如果为None则使用最新交易日
            
        Returns:
            包含市场状态、赚钱效应、建议仓位、组合净值的字典
        """
        if trade_date is None:
            from src.strategy import get_trade_date
            trade_date = get_trade_date()
        
        logger.info(f"获取Dashboard概览，交易日期: {trade_date}")
        
        # 获取指数数据计算市场状态
        index_code = "000001.SH"  # 上证指数
        end_date = trade_date
        start_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=60)).strftime("%Y%m%d")
        
        try:
            # 获取指数日线数据
            index_df = self.data_provider._pro.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date,
                fields="trade_date,close"
            )
            
            if index_df.empty:
                logger.warning("无法获取指数数据，使用默认值")
                return self._get_default_overview()
            
            # 计算BBI
            index_df = index_df.sort_values('trade_date').reset_index(drop=True)
            index_df['close'] = pd.to_numeric(index_df['close'], errors='coerce')
            
            # BBI = (MA3 + MA6 + MA12 + MA24) / 4
            ma3 = index_df['close'].rolling(window=3, min_periods=1).mean()
            ma6 = index_df['close'].rolling(window=6, min_periods=1).mean()
            ma12 = index_df['close'].rolling(window=12, min_periods=1).mean()
            ma24 = index_df['close'].rolling(window=24, min_periods=1).mean()
            bbi = (ma3 + ma6 + ma12 + ma24) / 4
            
            # 获取最新数据
            latest_price = float(index_df.iloc[-1]['close'])
            latest_bbi = float(bbi.iloc[-1])
            
            # 判断市场状态
            is_bull = bool(latest_price > latest_bbi)
            regime = "多头 (进攻)" if is_bull else "空头 (防守)"
            
            # 计算赚钱效应（简化：基于上涨股票比例）
            # 这里使用模拟数据，实际应该从市场数据计算
            sentiment = self._calculate_sentiment(trade_date)
            
            # 建议仓位
            target_position = 100 if is_bull else 25
            position_label = "Full On" if target_position == 100 else "Defensive"
            
            # 组合净值（模拟数据，实际应从数据库获取）
            portfolio_nav = self._get_portfolio_nav()
            nav_change = np.random.uniform(-0.02, 0.03)  # -2% to +3%
            
            return {
                "market_regime": {
                    "regime": regime,
                    "is_bull": bool(is_bull)  # Convert numpy bool_ to Python bool
                },
                "sentiment": {
                    "sentiment": float(round(sentiment, 1)),
                    "change": float(round(np.random.uniform(-5, 5), 1))
                },
                "target_position": {
                    "position": int(target_position),
                    "label": position_label
                },
                "portfolio_nav": {
                    "nav": float(round(portfolio_nav, 2)),
                    "change_percent": float(round(nav_change * 100, 2))
                }
            }
            
        except Exception as e:
            logger.error(f"获取Dashboard概览失败: {e}")
            return self._get_default_overview()
    
    def get_market_trend(self, days: int = 60, index_code: str = "000001.SH") -> Dict[str, Any]:
        """
        获取市场趋势数据（指数价格和BBI）
        
        Args:
            days: 获取天数
            index_code: 指数代码，默认上证指数
            
        Returns:
            包含指数代码、名称和趋势数据的字典
        """
        logger.info(f"获取市场趋势数据，指数: {index_code}, 天数: {days}")
        
        try:
            # 计算日期范围
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")  # 多取一些以过滤交易日
            
            # 获取指数日线数据
            index_df = self.data_provider._pro.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date,
                fields="trade_date,close"
            )
            
            if index_df.empty:
                logger.warning("无法获取指数数据")
                return {
                    "index_code": index_code,
                    "index_name": "上证指数",
                    "data": []
                }
            
            # 处理数据
            index_df = index_df.sort_values('trade_date').reset_index(drop=True)
            index_df['close'] = pd.to_numeric(index_df['close'], errors='coerce')
            
            # 只取最近days条数据
            index_df = index_df.tail(days).reset_index(drop=True)
            
            # 计算BBI
            ma3 = index_df['close'].rolling(window=3, min_periods=1).mean()
            ma6 = index_df['close'].rolling(window=6, min_periods=1).mean()
            ma12 = index_df['close'].rolling(window=12, min_periods=1).mean()
            ma24 = index_df['close'].rolling(window=24, min_periods=1).mean()
            bbi = (ma3 + ma6 + ma12 + ma24) / 4
            
            # 转换为日期格式
            index_df['trade_date'] = pd.to_datetime(index_df['trade_date'], format='%Y%m%d', errors='coerce')
            
            # 构建响应数据
            data = []
            for _, row in index_df.iterrows():
                data.append({
                    "date": row['trade_date'].strftime("%Y-%m-%d"),
                    "price": round(float(row['close']), 2),
                    "bbi": round(float(bbi[row.name]), 2)
                })
            
            # 获取指数名称
            index_name_map = {
                "000001.SH": "上证指数",
                "000300.SH": "沪深300",
                "000852.SH": "中证1000"
            }
            index_name = index_name_map.get(index_code, "指数")
            
            return {
                "index_code": index_code,
                "index_name": index_name,
                "data": data
            }
            
        except Exception as e:
            logger.error(f"获取市场趋势数据失败: {e}")
            return {
                "index_code": index_code,
                "index_name": "上证指数",
                "data": []
            }
    
    def _calculate_sentiment(self, trade_date: str) -> float:
        """
        计算赚钱效应（简化实现）
        
        实际应该计算上涨股票比例等指标
        """
        # 这里使用模拟数据，实际应该从市场数据计算
        return float(round(np.random.uniform(30, 70), 1))
    
    def _get_portfolio_nav(self) -> float:
        """
        获取组合净值（模拟数据）
        
        实际应该从数据库获取
        """
        base_nav = 1000000
        variation = float(np.random.uniform(-0.1, 0.25))
        return float(round(base_nav * (1 + variation), 2))
    
    def _get_default_overview(self) -> Dict[str, Any]:
        """获取默认概览数据（当数据获取失败时）"""
        return {
            "market_regime": {
                "regime": "多头 (进攻)",
                "is_bull": True
            },
            "sentiment": {
                "sentiment": float(45.0),
                "change": float(5.0)
            },
            "target_position": {
                "position": int(100),
                "label": "Full On"
            },
            "portfolio_nav": {
                "nav": float(1245300.0),
                "change_percent": float(1.2)
            }
        }
