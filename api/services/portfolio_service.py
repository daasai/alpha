"""
Portfolio Service - 模拟盘业务逻辑
"""
from typing import Dict, Any, List, Optional
import uuid
from datetime import datetime
import pandas as pd
import numpy as np

from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.logging_config import get_logger

logger = get_logger(__name__)

# 内存存储（临时方案，后续可改为数据库）
_portfolio_storage: Dict[str, Dict[str, Any]] = {}


class PortfolioService:
    """Portfolio服务"""
    
    def __init__(self, data_provider: DataProvider, config: ConfigManager):
        self.data_provider = data_provider
        self.config = config
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        获取持仓列表
        
        Returns:
            持仓列表
        """
        positions = list(_portfolio_storage.values())
        
        # 更新当前价格
        for pos in positions:
            current_price = self._get_current_price(pos['code'])
            if current_price:
                pos['current_price'] = current_price
        
        return positions
    
    def add_position(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加持仓
        
        Args:
            position_data: 持仓数据
            
        Returns:
            添加的持仓
        """
        position_id = str(uuid.uuid4())
        
        # 获取当前价格
        current_price = self._get_current_price(position_data['code'])
        if not current_price:
            current_price = position_data.get('cost', 0)
        
        # 从配置读取默认值
        default_shares = self.config.get('portfolio.default_shares', 100)
        default_stop_loss_ratio = self.config.get('portfolio.default_stop_loss_ratio', 0.9)
        
        # 如果未提供shares，使用配置默认值
        shares = position_data.get('shares')
        if shares is None:
            shares = default_shares
            logger.debug(f"使用配置默认持仓数量: {shares}")
        
        # 如果未提供stop_loss_price，使用配置默认比例计算
        stop_loss_price = position_data.get('stop_loss_price')
        if stop_loss_price is None:
            cost = position_data['cost']
            stop_loss_price = cost * default_stop_loss_ratio
            logger.debug(f"使用配置默认止损比例计算止损价: {stop_loss_price} (成本价: {cost}, 比例: {default_stop_loss_ratio})")
        
        position = {
            'id': position_id,
            'code': position_data['code'],
            'name': position_data['name'],
            'cost': position_data['cost'],
            'current_price': current_price,
            'shares': shares,
            'stop_loss_price': stop_loss_price,
            'created_at': datetime.now().isoformat()
        }
        
        _portfolio_storage[position_id] = position
        logger.info(f"添加持仓: {position_data['code']} - {position_data['name']}, 数量: {shares}, 止损价: {stop_loss_price}")
        
        return position
    
    def update_position(self, position_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新持仓
        
        Args:
            position_id: 持仓ID
            update_data: 更新数据
            
        Returns:
            更新后的持仓，如果不存在则返回None
        """
        if position_id not in _portfolio_storage:
            return None
        
        position = _portfolio_storage[position_id]
        
        if 'cost' in update_data:
            position['cost'] = update_data['cost']
        if 'shares' in update_data:
            position['shares'] = update_data['shares']
        if 'stop_loss_price' in update_data:
            position['stop_loss_price'] = update_data['stop_loss_price']
        
        position['updated_at'] = datetime.now().isoformat()
        
        logger.info(f"更新持仓: {position_id}")
        return position
    
    def delete_position(self, position_id: str) -> bool:
        """
        删除持仓
        
        Args:
            position_id: 持仓ID
            
        Returns:
            是否成功删除
        """
        if position_id in _portfolio_storage:
            del _portfolio_storage[position_id]
            logger.info(f"删除持仓: {position_id}")
            return True
        return False
    
    def refresh_prices(self) -> Dict[str, Any]:
        """
        刷新所有持仓的价格
        
        Returns:
            刷新结果
        """
        updated_count = 0
        for position_id, position in _portfolio_storage.items():
            current_price = self._get_current_price(position['code'])
            if current_price:
                position['current_price'] = current_price
                position['updated_at'] = datetime.now().isoformat()
                updated_count += 1
        
        logger.info(f"刷新价格: {updated_count} 个持仓")
        return {
            "updated_count": updated_count,
            "total_positions": len(_portfolio_storage)
        }
    
    def get_metrics(self) -> Dict[str, float]:
        """
        计算组合指标
        
        Returns:
            组合指标字典
        """
        positions = self.get_positions()
        
        if not positions:
            return {
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0
            }
        
        # 计算总收益
        total_cost = sum(pos['cost'] * pos['shares'] for pos in positions)
        total_value = sum(pos['current_price'] * pos['shares'] for pos in positions)
        total_return = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
        
        # 计算最大回撤（简化：基于当前持仓）
        max_drawdown = self._calculate_max_drawdown(positions)
        
        # 计算夏普比率（简化：基于总收益）
        sharpe_ratio = self._calculate_sharpe_ratio(total_return)
        
        return {
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2)
        }
    
    def _get_current_price(self, code: str) -> Optional[float]:
        """
        获取股票当前价格
        
        Args:
            code: 股票代码
            
        Returns:
            当前价格，如果获取失败则返回None
        """
        try:
            from src.strategy import get_trade_date
            trade_date = get_trade_date()
            
            # 获取最新价格
            daily = self.data_provider._pro.daily(
                ts_code=code,
                trade_date=trade_date,
                fields="close"
            )
            
            if not daily.empty:
                return float(daily.iloc[0]['close'])
            
            # 如果当天没有数据，获取最近的数据
            daily = self.data_provider._pro.daily(
                ts_code=code,
                end_date=trade_date,
                limit=1,
                fields="close"
            )
            
            if not daily.empty:
                return float(daily.iloc[0]['close'])
            
            return None
            
        except Exception as e:
            logger.warning(f"获取股票价格失败 {code}: {e}")
            return None
    
    def _calculate_max_drawdown(self, positions: List[Dict[str, Any]]) -> float:
        """
        计算最大回撤（简化实现）
        
        实际应该基于历史净值曲线计算
        """
        if not positions:
            return 0.0
        
        # 简化：基于当前持仓的盈亏计算
        drawdowns = []
        for pos in positions:
            if pos['cost'] > 0:
                pnl_pct = (pos['current_price'] - pos['cost']) / pos['cost'] * 100
                if pnl_pct < 0:
                    drawdowns.append(abs(pnl_pct))
        
        return max(drawdowns) if drawdowns else 0.0
    
    def _calculate_sharpe_ratio(self, total_return: float) -> float:
        """
        计算夏普比率（简化实现）
        
        实际应该基于历史收益率序列计算
        """
        # 简化：基于总收益估算
        if total_return <= 0:
            return 0.0
        
        # 假设年化收益率为总收益，无风险利率为3%，波动率为15%
        annual_return = total_return
        risk_free_rate = 3.0
        volatility = 15.0
        
        sharpe = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0.0
        return max(0.0, sharpe)
