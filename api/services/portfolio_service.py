"""
Portfolio Service - 组合管理业务逻辑层
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.repositories.portfolio_repository import PortfolioRepository
from src.database import DailyNav, _SessionLocal
from src.logging_config import get_logger
from api.utils.exceptions import (
    AccountNotInitializedError,
    InsufficientFundsError,
    PositionNotFoundError,
    InsufficientVolumeError,
)

logger = get_logger(__name__)


class PortfolioService:
    """组合管理服务"""
    
    def __init__(
        self,
        data_provider: DataProvider,
        config: ConfigManager,
        repository: Optional[PortfolioRepository] = None
    ):
        """
        初始化 PortfolioService
        
        Args:
            data_provider: 数据提供者
            config: 配置管理器
            repository: 组合Repository，如果为None则创建新实例
        """
        self.data_provider = data_provider
        self.config = config
        
        if repository is None:
            self.repository = PortfolioRepository()
        else:
            self.repository = repository
    
    def get_account(self) -> Optional[Dict[str, Any]]:
        """
        获取账户信息
        
        Returns:
            账户字典，如果不存在则返回 None
        """
        account = self.repository.get_account()
        if account:
            # 获取初始资产（账户创建时的资产，或最早的DailyNav记录）
            initial_asset = self._get_initial_asset(account)
            # 获取昨日净值（用于计算日盈亏）
            yesterday_nav = self._get_yesterday_nav()
            
            return {
                'id': account.id,
                'total_asset': account.total_asset,
                'cash': account.cash,
                'market_value': account.market_value,
                'frozen_cash': account.frozen_cash,
                'initial_asset': initial_asset,
                'yesterday_nav': yesterday_nav,
                'created_at': account.created_at.isoformat() if account.created_at else None,
                'updated_at': account.updated_at.isoformat() if account.updated_at else None,
            }
        return None
    
    def _get_initial_asset(self, account) -> float:
        """
        获取初始资产
        
        优先从最早的DailyNav记录获取，如果没有则使用账户创建时的资产
        """
        try:
            with _SessionLocal() as s:
                # 获取最早的DailyNav记录
                earliest_nav = s.query(DailyNav).order_by(DailyNav.trade_date.asc()).first()
                if earliest_nav:
                    return float(earliest_nav.total_asset)
                
                # 如果没有DailyNav记录，使用账户创建时的资产
                # 如果账户刚创建，初始资产就是当前的total_asset
                return float(account.total_asset)
        except Exception as e:
            logger.warning(f"获取初始资产失败: {e}，使用当前总资产")
            return float(account.total_asset)
    
    def _get_yesterday_nav(self) -> Optional[float]:
        """
        获取昨日净值（用于计算日盈亏）
        
        Returns:
            昨日总资产，如果不存在则返回None
        """
        try:
            from src.strategy import get_trade_date
            today = get_trade_date()
            
            # 获取昨天的日期（简化：假设是连续交易日）
            # 实际应该使用交易日历，这里先简化处理
            with _SessionLocal() as s:
                # 获取今天之前的最近一条记录
                yesterday_nav = s.query(DailyNav).filter(
                    DailyNav.trade_date < today
                ).order_by(DailyNav.trade_date.desc()).first()
                
                if yesterday_nav:
                    return float(yesterday_nav.total_asset)
                return None
        except Exception as e:
            logger.warning(f"获取昨日净值失败: {e}")
            return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        获取持仓列表
        
        Returns:
            持仓列表（字典格式）
        """
        positions = self.repository.get_positions()
        return [self._position_to_dict(pos) for pos in positions]
    
    def get_position(self, ts_code: str) -> Optional[Dict[str, Any]]:
        """
        按股票代码获取持仓
        
        Args:
            ts_code: 股票代码
            
        Returns:
            持仓字典，如果不存在则返回 None
        """
        position = self.repository.get_position(ts_code)
        if position:
            return self._position_to_dict(position)
        return None
    
    def execute_buy(
        self,
        ts_code: str,
        price: float,
        volume: int,
        strategy_tag: str = None
    ) -> Dict[str, Any]:
        """
        执行买入订单
        
        Args:
            ts_code: 股票代码
            price: 买入价格
            volume: 买入数量
            strategy_tag: 策略标签（可选）
            
        Returns:
            订单字典
            
        Raises:
            AccountNotInitializedError: 账户未初始化
            InsufficientFundsError: 资金不足
        """
        # 检查账户是否存在
        account = self.repository.get_account()
        if not account:
            raise AccountNotInitializedError()
        
        # 计算所需现金（包含手续费 0.2%）
        fee_rate = 0.002
        fee = price * volume * fee_rate
        required_cash = price * volume + fee
        
        # 检查资金是否充足
        if account.cash < required_cash:
            raise InsufficientFundsError(
                required=required_cash,
                available=account.cash
            )
        
        # 获取交易日期
        from src.strategy import get_trade_date
        trade_date = get_trade_date()
        
        # 获取股票名称（如果持仓不存在需要）
        stock_name = ts_code
        try:
            # 尝试从 DataProvider 获取股票名称
            basic = self.data_provider._tushare_client.get_stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name"
            )
            if not basic.empty:
                stock_info = basic[basic['ts_code'] == ts_code]
                if not stock_info.empty:
                    stock_name = stock_info.iloc[0]['name']
        except Exception as e:
            logger.warning(f"获取股票名称失败 {ts_code}: {e}")
        
        # 创建订单
        order_data = {
            'trade_date': trade_date,
            'ts_code': ts_code,
            'action': 'BUY',
            'price': price,
            'volume': volume,
            'fee': fee,
            'strategy_tag': strategy_tag,
            'name': stock_name
        }
        
        order = self.repository.create_order(order_data)
        
        logger.info(f"执行买入: {ts_code} {volume}股 @ {price:.2f}, 手续费 {fee:.2f}")
        
        return {
            'order_id': order.order_id,
            'trade_date': order.trade_date,
            'ts_code': order.ts_code,
            'action': order.action,
            'price': order.price,
            'volume': order.volume,
            'fee': order.fee,
            'status': order.status,
            'strategy_tag': order.strategy_tag,
            'created_at': order.created_at.isoformat() if order.created_at else None,
        }
    
    def execute_sell(
        self,
        ts_code: str,
        price: float,
        volume: int,
        reason: str = None
    ) -> Dict[str, Any]:
        """
        执行卖出订单
        
        Args:
            ts_code: 股票代码
            price: 卖出价格
            volume: 卖出数量
            reason: 卖出原因（可选）
            
        Returns:
            订单字典
            
        Raises:
            PositionNotFoundError: 持仓不存在
            InsufficientVolumeError: 可用数量不足
        """
        # 检查持仓是否存在
        position = self.repository.get_position(ts_code)
        if not position:
            raise PositionNotFoundError(ts_code=ts_code)
        
        # 检查可用数量（T+1 规则）
        if position.avail_vol < volume:
            raise InsufficientVolumeError(
                ts_code=ts_code,
                required=volume,
                available=position.avail_vol
            )
        
        # 计算手续费（0.2%）
        fee_rate = 0.002
        fee = price * volume * fee_rate
        
        # 获取交易日期
        from src.strategy import get_trade_date
        trade_date = get_trade_date()
        
        # 创建订单
        order_data = {
            'trade_date': trade_date,
            'ts_code': ts_code,
            'action': 'SELL',
            'price': price,
            'volume': volume,
            'fee': fee,
            'reason': reason
        }
        
        order = self.repository.create_order(order_data)
        
        logger.info(f"执行卖出: {ts_code} {volume}股 @ {price:.2f}, 手续费 {fee:.2f}")
        
        return {
            'order_id': order.order_id,
            'trade_date': order.trade_date,
            'ts_code': order.ts_code,
            'action': order.action,
            'price': order.price,
            'volume': order.volume,
            'fee': order.fee,
            'status': order.status,
            'reason': order.reason,
            'created_at': order.created_at.isoformat() if order.created_at else None,
        }
    
    def sync_latest_prices(self) -> Dict[str, Any]:
        """
        同步最新价格
        
        从 DataProvider 获取所有持仓的最新价格，并更新到数据库
        
        Returns:
            同步结果字典，包含 updated_count, total_positions, timestamp
        """
        # 获取所有持仓
        positions = self.repository.get_positions()
        
        if not positions:
            return {
                'updated_count': 0,
                'total_positions': 0,
                'timestamp': datetime.now().isoformat()
            }
        
        # 提取股票代码列表
        ts_codes = [pos.ts_code for pos in positions]
        
        # 获取最新价格
        prices_dict = {}
        for ts_code in ts_codes:
            current_price = self._get_current_price(ts_code)
            if current_price:
                prices_dict[ts_code] = current_price
        
        # 批量更新价格
        if prices_dict:
            self.repository.update_positions_market_value(prices_dict)
        
        logger.info(f"同步价格: 更新 {len(prices_dict)}/{len(ts_codes)} 只股票")
        
        return {
            'updated_count': len(prices_dict),
            'total_positions': len(positions),
            'timestamp': datetime.now().isoformat()
        }
    
    def delete_position(self, position_id: int) -> bool:
        """
        删除持仓
        
        Args:
            position_id: 持仓ID
            
        Returns:
            如果删除成功返回 True，如果持仓不存在返回 False
            
        Raises:
            PositionNotFoundError: 持仓不存在
        """
        # 检查持仓是否存在
        position = self.repository.get_position_by_id(position_id)
        if not position:
            raise PositionNotFoundError(ts_code=f"ID:{position_id}")
        
        # 删除持仓
        success = self.repository.delete_position(position_id)
        
        if success:
            logger.info(f"删除持仓成功: ID={position_id}, ts_code={position.ts_code}")
        else:
            logger.warning(f"删除持仓失败: ID={position_id} 不存在")
        
        return success
    
    def _get_current_price(self, ts_code: str) -> Optional[float]:
        """
        获取股票当前价格
        
        Args:
            ts_code: 股票代码
            
        Returns:
            当前价格，如果获取失败则返回 None
        """
        try:
            from src.strategy import get_trade_date
            trade_date = get_trade_date()
            
            # 获取最新价格（使用 TushareClient）
            daily = self.data_provider._tushare_client.get_daily(
                ts_code=ts_code,
                trade_date=trade_date,
                fields="close"
            )
            
            if not daily.empty:
                return float(daily.iloc[0]['close'])
            
            # 如果当天没有数据，获取最近的数据
            daily = self.data_provider._tushare_client.get_daily(
                ts_code=ts_code,
                end_date=trade_date,
                limit=1,
                fields="close"
            )
            
            if not daily.empty:
                return float(daily.iloc[0]['close'])
            
            return None
            
        except Exception as e:
            logger.warning(f"获取股票价格失败 {ts_code}: {e}")
            return None
    
    def get_metrics(self) -> Dict[str, float]:
        """
        计算组合指标
        
        Returns:
            组合指标字典
        """
        positions = self.get_positions()
        account = self.get_account()
        
        if not positions:
            return {
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0
            }
        
        # 计算总收益（基于持仓盈亏）
        total_cost = sum(pos['avg_price'] * pos['total_vol'] for pos in positions)
        total_value = sum(
            (pos['current_price'] or pos['avg_price']) * pos['total_vol'] 
            for pos in positions
        )
        total_return = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
        
        # 计算最大回撤（简化：基于当前持仓的盈亏）
        max_drawdown = self._calculate_max_drawdown(positions)
        
        # 计算夏普比率（简化：基于总收益）
        sharpe_ratio = self._calculate_sharpe_ratio(total_return)
        
        return {
            "total_return": round(total_return, 2),
            "max_drawdown": round(max_drawdown, 2),
            "sharpe_ratio": round(sharpe_ratio, 2)
        }
    
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
            if pos['avg_price'] > 0 and pos['current_price']:
                pnl_pct = (pos['current_price'] - pos['avg_price']) / pos['avg_price'] * 100
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
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        获取统一组合状态（实时净值）
        
        先同步最新价格，然后返回账户信息和持仓列表
        
        Returns:
            {
                'account': Account info (total_asset, cash, market_value),
                'positions': List of Position with calculated P&L
            }
        """
        # 1. 先同步最新价格，确保实时净值
        self.sync_latest_prices()
        
        # 2. 获取账户信息
        account = self.get_account()
        
        # 3. 获取持仓列表（包含盈亏）
        positions = self.get_positions()
        
        return {
            'account': account,
            'positions': positions
        }
    
    def execute_order(
        self,
        action: str,
        ts_code: str,
        price: float,
        volume: int,
        strategy_tag: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        统一订单执行方法
        
        Args:
            action: 订单动作，'BUY' 或 'SELL'
            ts_code: 股票代码
            price: 成交价格
            volume: 成交数量
            strategy_tag: 策略标签（买入时可选）
            reason: 卖出原因（卖出时可选）
            
        Returns:
            订单字典
            
        Raises:
            ValueError: 无效的订单动作
        """
        if action == 'BUY':
            return self.execute_buy(ts_code, price, volume, strategy_tag)
        elif action == 'SELL':
            return self.execute_sell(ts_code, price, volume, reason)
        else:
            raise ValueError(f"无效的订单动作: {action}，必须是 'BUY' 或 'SELL'")
    
    def get_order_history(self, limit: Optional[int] = 50) -> List[Dict[str, Any]]:
        """
        获取订单历史
        
        Args:
            limit: 返回的最大订单数量，默认50
            
        Returns:
            订单字典列表，按创建时间倒序排列
        """
        orders = self.repository.get_orders(limit=limit)
        return [self._order_to_dict(order) for order in orders]
    
    def _order_to_dict(self, order) -> Dict[str, Any]:
        """
        将 Order 模型转换为字典
        
        Args:
            order: Order 模型实例
            
        Returns:
            订单字典
        """
        return {
            'order_id': order.order_id,
            'trade_date': order.trade_date,
            'ts_code': order.ts_code,
            'action': order.action,
            'price': order.price,
            'volume': order.volume,
            'fee': order.fee,
            'status': order.status,
            'strategy_tag': order.strategy_tag,
            'reason': order.reason,
            'created_at': order.created_at.isoformat() if order.created_at else None,
        }
    
    def _position_to_dict(self, position) -> Dict[str, Any]:
        """
        将 Position 模型转换为字典
        
        Args:
            position: Position 模型实例
            
        Returns:
            持仓字典（包含后端字段和前端兼容字段）
        """
        # 转换ID为字符串以匹配前端期望
        position_id = str(position.id) if position.id else None
        
        return {
            # 后端原始字段
            'id': position_id,
            'ts_code': position.ts_code,
            'name': position.name,
            'total_vol': position.total_vol,
            'avail_vol': position.avail_vol,
            'avg_price': position.avg_price,
            'current_price': position.current_price,
            'profit': position.profit,
            'profit_pct': position.profit_pct,
            'created_at': position.created_at.isoformat() if position.created_at else None,
            'updated_at': position.updated_at.isoformat() if position.updated_at else None,
            # 前端兼容字段（别名）
            'code': position.ts_code,
            'cost': position.avg_price,
            'shares': position.total_vol,
            'stop_loss_price': None,  # 前端期望但后端暂无此字段
        }
