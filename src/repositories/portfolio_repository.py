"""
Portfolio Repository - 组合管理数据访问层
"""
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import uuid

from ..database import Account, Position, Order
from .. import database as db_module
from ..logging_config import get_logger
from api.utils.exceptions import (
    InsufficientFundsError,
    PositionNotFoundError,
    InsufficientVolumeError,
)

logger = get_logger(__name__)


@contextmanager
def _session_scope():
    """数据库会话上下文管理器"""
    # 使用模块级别的 _SessionLocal，确保使用正确的数据库连接
    s = db_module._SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


class PortfolioRepository:
    """组合管理Repository"""
    
    def get_account(self) -> Optional[Account]:
        """
        获取账户（单例，id=1）
        
        Returns:
            Account 模型实例，如果不存在则返回 None
        """
        with _session_scope() as s:
            account = s.query(Account).filter(Account.id == 1).first()
            if account:
                # 在会话内访问属性，然后expunge
                _ = account.cash
                _ = account.total_asset
                _ = account.market_value
                _ = account.frozen_cash
                s.expunge(account)
            return account
    
    def initialize_account(self, initial_cash: float) -> Account:
        """
        初始化账户
        
        Args:
            initial_cash: 初始现金
            
        Returns:
            Account 模型实例
        """
        with _session_scope() as s:
            account = s.query(Account).filter(Account.id == 1).first()
            if account:
                # 如果已存在，更新现金
                account.cash = initial_cash
                account.total_asset = initial_cash
                account.market_value = 0.0
                account.frozen_cash = 0.0
            else:
                # 创建新账户
                account = Account(
                    id=1,
                    cash=initial_cash,
                    total_asset=initial_cash,
                    market_value=0.0,
                    frozen_cash=0.0
                )
                s.add(account)
            
            s.flush()
            # 在会话内访问属性，然后expunge以避免detached实例问题
            _ = account.cash
            _ = account.total_asset
            _ = account.market_value
            _ = account.frozen_cash
            s.expunge(account)  # 从会话中分离，但保留属性值
            logger.info(f"初始化账户: 初始现金 {initial_cash:.2f}")
            return account
    
    def update_account_balance(self, cash: float, total_asset: float) -> Account:
        """
        更新账户余额（充值/调整）
        
        Args:
            cash: 新的现金余额
            total_asset: 新的总资产
            
        Returns:
            Account 模型实例
            
        Raises:
            ValueError: 账户不存在
        """
        with _session_scope() as s:
            account = s.query(Account).filter(Account.id == 1).first()
            if not account:
                raise ValueError("账户未初始化，请先调用 initialize_account")
            
            # 更新现金和总资产
            account.cash = cash
            account.total_asset = total_asset
            # 市值 = 总资产 - 现金（保持一致性）
            account.market_value = total_asset - cash
            
            s.flush()
            # 在会话内访问属性，然后expunge
            _ = account.cash
            _ = account.total_asset
            _ = account.market_value
            s.expunge(account)
            logger.info(f"更新账户余额: 现金={cash:.2f}, 总资产={total_asset:.2f}, 市值={account.market_value:.2f}")
            return account
    
    def get_positions(self) -> List[Position]:
        """
        获取所有持仓
        
        Returns:
            Position 模型实例列表，按 ts_code 排序
        """
        with _session_scope() as s:
            positions = s.query(Position).order_by(Position.ts_code).all()
            # 在会话内访问属性，然后expunge
            for pos in positions:
                _ = pos.ts_code
                _ = pos.total_vol
                _ = pos.avail_vol
                _ = pos.avg_price
                s.expunge(pos)
            return positions
    
    def get_position(self, ts_code: str) -> Optional[Position]:
        """
        按股票代码获取持仓
        
        Args:
            ts_code: 股票代码
            
        Returns:
            Position 模型实例，如果不存在则返回 None
        """
        with _session_scope() as s:
            position = s.query(Position).filter(Position.ts_code == ts_code).first()
            if position:
                # 在会话内访问属性，然后expunge
                _ = position.ts_code
                _ = position.total_vol
                _ = position.avail_vol
                _ = position.avg_price
                s.expunge(position)
            return position
    
    def get_position_by_id(self, position_id: int) -> Optional[Position]:
        """
        按ID获取持仓
        
        Args:
            position_id: 持仓ID
            
        Returns:
            Position 模型实例，如果不存在则返回 None
        """
        with _session_scope() as s:
            position = s.query(Position).filter(Position.id == position_id).first()
            if position:
                # 在会话内访问属性，然后expunge
                _ = position.ts_code
                _ = position.total_vol
                _ = position.avail_vol
                _ = position.avg_price
                s.expunge(position)
            return position
    
    def delete_position(self, position_id: int) -> bool:
        """
        删除持仓
        
        Args:
            position_id: 持仓ID
            
        Returns:
            如果删除成功返回 True，如果持仓不存在返回 False
        """
        with _session_scope() as s:
            position = s.query(Position).filter(Position.id == position_id).first()
            if not position:
                return False
            
            # 删除持仓
            s.delete(position)
            
            # 重新计算账户资产
            self._recalculate_account_assets(s)
            
            logger.info(f"删除持仓: ID={position_id}, ts_code={position.ts_code}")
            return True
    
    def create_order(self, order_data: Dict[str, Any]) -> Order:
        """
        创建订单（原子事务）
        
        买入时：
        - 检查资金是否充足
        - 扣除现金
        - 创建或更新持仓（更新 total_vol，avail_vol 保持不变，重新计算 avg_price）
        - 更新账户市值
        
        卖出时：
        - 检查持仓是否存在
        - 检查可用数量是否充足
        - 增加现金
        - 更新持仓（减少 total_vol 和 avail_vol）
        - 如果 total_vol == 0，删除持仓
        - 更新账户市值
        
        Args:
            order_data: 订单数据，必须包含：
                - trade_date: 交易日期（YYYYMMDD）
                - ts_code: 股票代码
                - action: BUY/SELL
                - price: 成交价格
                - volume: 成交数量
                - fee: 手续费
                - strategy_tag: 策略标签（买入时可选）
                - reason: 卖出原因（卖出时可选）
                - name: 股票名称（买入时，如果持仓不存在需要）
        
        Returns:
            Order 模型实例
            
        Raises:
            InsufficientFundsError: 资金不足
            PositionNotFoundError: 持仓不存在
            InsufficientVolumeError: 可用数量不足
        """
        with _session_scope() as s:
            # 获取账户
            account = s.query(Account).filter(Account.id == 1).first()
            if not account:
                raise ValueError("账户未初始化")
            
            trade_date = order_data['trade_date']
            ts_code = order_data['ts_code']
            action = order_data['action']
            price = float(order_data['price'])
            volume = int(order_data['volume'])
            fee = float(order_data.get('fee', 0.0))
            
            if action == 'BUY':
                # 买入逻辑
                order_cost = price * volume + fee
                
                # 检查资金是否充足
                if account.cash < order_cost:
                    raise InsufficientFundsError(
                        required=order_cost,
                        available=account.cash
                    )
                
                # 扣除现金
                account.cash -= order_cost
                
                # 获取或创建持仓
                position = s.query(Position).filter(Position.ts_code == ts_code).first()
                if position:
                    # 更新现有持仓
                    # 重新计算平均成本价
                    old_total_vol = position.total_vol
                    old_avg_price = position.avg_price
                    new_total_vol = old_total_vol + volume
                    new_avg_price = (old_avg_price * old_total_vol + price * volume) / new_total_vol
                    
                    position.total_vol = new_total_vol
                    # avail_vol 保持不变（T+1 规则）
                    position.avg_price = new_avg_price
                else:
                    # 创建新持仓
                    position = Position(
                        ts_code=ts_code,
                        name=order_data.get('name', ts_code),
                        total_vol=volume,
                        avail_vol=0,  # T+1 规则，买入当日不可卖出
                        avg_price=price,
                        current_price=price,
                        profit=0.0,
                        profit_pct=0.0
                    )
                    s.add(position)
                
                # 创建订单记录
                order = Order(
                    order_id=str(uuid.uuid4()),
                    trade_date=trade_date,
                    ts_code=ts_code,
                    action='BUY',
                    price=price,
                    volume=volume,
                    fee=fee,
                    status='FILLED',
                    strategy_tag=order_data.get('strategy_tag')
                )
                s.add(order)
                
            elif action == 'SELL':
                # 卖出逻辑
                # 获取持仓
                position = s.query(Position).filter(Position.ts_code == ts_code).first()
                if not position:
                    raise PositionNotFoundError(ts_code=ts_code)
                
                # 检查可用数量
                if position.avail_vol < volume:
                    raise InsufficientVolumeError(
                        ts_code=ts_code,
                        required=volume,
                        available=position.avail_vol
                    )
                
                # 增加现金
                account.cash += (price * volume - fee)
                
                # 更新持仓
                position.total_vol -= volume
                position.avail_vol -= volume
                
                # 如果持仓数量为0，删除持仓
                if position.total_vol == 0:
                    s.delete(position)
                
                # 创建订单记录
                order = Order(
                    order_id=str(uuid.uuid4()),
                    trade_date=trade_date,
                    ts_code=ts_code,
                    action='SELL',
                    price=price,
                    volume=volume,
                    fee=fee,
                    status='FILLED',
                    reason=order_data.get('reason')
                )
                s.add(order)
            else:
                raise ValueError(f"无效的订单动作: {action}")
            
            # 重新计算账户资产
            self._recalculate_account_assets(s)
            
            s.flush()
            # 在会话内访问属性，然后expunge以避免detached实例问题
            _ = order.order_id
            _ = order.action
            _ = order.status
            s.expunge(order)  # 从会话中分离，但保留属性值
            logger.info(f"创建订单: {action} {ts_code} {volume}股 @ {price:.2f}")
            return order
    
    def update_positions_market_value(self, prices_dict: Dict[str, float]) -> None:
        """
        批量更新持仓市值
        
        Args:
            prices_dict: 价格字典，key为ts_code，value为current_price
        """
        if not prices_dict:
            return
        
        with _session_scope() as s:
            # 批量更新持仓价格
            for ts_code, current_price in prices_dict.items():
                position = s.query(Position).filter(Position.ts_code == ts_code).first()
                if position:
                    position.current_price = current_price
                    
                    # 重新计算盈亏
                    if position.avg_price > 0:
                        position.profit = (current_price - position.avg_price) * position.total_vol
                        position.profit_pct = (current_price - position.avg_price) / position.avg_price * 100
                    else:
                        position.profit = 0.0
                        position.profit_pct = 0.0
            
            # 重新计算账户资产
            self._recalculate_account_assets(s)
            
            logger.debug(f"批量更新持仓价格: {len(prices_dict)} 只股票")
    
    def get_orders(self, limit: Optional[int] = None) -> List[Order]:
        """
        获取订单历史
        
        Args:
            limit: 返回的最大订单数量，如果为None则返回所有订单
        
        Returns:
            Order 模型实例列表，按创建时间倒序排列
        """
        with _session_scope() as s:
            query = s.query(Order).order_by(Order.created_at.desc())
            if limit is not None:
                query = query.limit(limit)
            orders = query.all()
            # 在会话内访问属性，然后expunge
            for order in orders:
                _ = order.order_id
                _ = order.action
                _ = order.status
                s.expunge(order)
            return orders
    
    def _recalculate_account_assets(self, session) -> None:
        """
        重新计算账户市值和总资产（内部方法）
        
        Args:
            session: 数据库会话
        """
        account = session.query(Account).filter(Account.id == 1).first()
        if not account:
            return
        
        # 计算所有持仓的市值
        positions = session.query(Position).all()
        market_value = sum(
            pos.current_price * pos.total_vol 
            for pos in positions 
            if pos.current_price is not None
        )
        
        account.market_value = market_value
        account.total_asset = account.cash + account.market_value
        
        logger.debug(f"重新计算账户资产: 现金={account.cash:.2f}, 市值={market_value:.2f}, 总资产={account.total_asset:.2f}")
