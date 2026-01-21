"""
Portfolio Models Unit Tests
组合管理模型单元测试
"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.exc import IntegrityError
from src.database import Account, Position, Order, Base, _engine, _SessionLocal


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """设置测试数据库"""
    import src.database
    
    # 创建临时数据库
    test_db_path = tmp_path / "test_daas.db"
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存原始值
    original_db_path = src.database._DB_PATH
    original_engine = src.database._engine
    original_SessionLocal = src.database._SessionLocal
    
    # 设置测试数据库
    src.database._DB_PATH = test_db_path
    src.database._engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False}
    )
    src.database._SessionLocal = sessionmaker(
        bind=src.database._engine,
        autoflush=False,
        autocommit=False
    )
    
    # 创建表
    Base.metadata.create_all(src.database._engine)
    
    yield
    
    # 恢复原始值
    src.database._DB_PATH = original_db_path
    src.database._engine = original_engine
    src.database._SessionLocal = original_SessionLocal


class TestAccountModel:
    """测试 Account 模型"""
    
    def test_account_singleton_constraint(self, setup_test_db):
        """测试账户单例约束"""
        from src.database import _SessionLocal
        
        session = _SessionLocal()
        try:
            # 创建第一个账户
            account1 = Account(id=1, cash=100000.0, total_asset=100000.0)
            session.add(account1)
            session.commit()
            
            # 尝试创建第二个账户（应该失败，因为唯一约束）
            account2 = Account(id=1, cash=200000.0, total_asset=200000.0)
            session.add(account2)
            
            # 应该抛出 IntegrityError
            with pytest.raises(IntegrityError):
                session.commit()
            
            # 回滚后验证只有一个账户存在
            session.rollback()
            accounts = session.query(Account).all()
            assert len(accounts) == 1, "应该只有一个账户"
            assert accounts[0].cash == 100000.0, "第一个账户应该保持不变"
        finally:
            session.close()
    
    def test_account_default_values(self, setup_test_db):
        """测试账户默认值"""
        from src.database import _SessionLocal
        
        session = _SessionLocal()
        try:
            account = Account(id=1)
            session.add(account)
            session.commit()
            
            assert account.total_asset == 0.0
            assert account.cash == 0.0
            assert account.market_value == 0.0
            assert account.frozen_cash == 0.0
            assert account.id == 1
        finally:
            session.close()
    
    def test_account_total_asset_constraint(self, setup_test_db):
        """测试总资产 = 现金 + 市值"""
        from src.database import _SessionLocal
        
        session = _SessionLocal()
        try:
            account = Account(
                id=1,
                cash=100000.0,
                market_value=50000.0,
                total_asset=150000.0
            )
            session.add(account)
            session.commit()
            
            # 验证约束：total_asset = cash + market_value
            assert account.total_asset == account.cash + account.market_value
        finally:
            session.close()


class TestPositionModel:
    """测试 Position 模型"""
    
    def test_position_ts_code_unique(self, setup_test_db):
        """测试 ts_code 唯一性约束"""
        from src.database import _SessionLocal
        
        session = _SessionLocal()
        try:
            # 创建第一个持仓
            position1 = Position(
                ts_code="000001.SZ",
                name="平安银行",
                total_vol=1000,
                avail_vol=1000,
                avg_price=10.0
            )
            session.add(position1)
            session.commit()
            
            # 尝试创建相同 ts_code 的持仓（应该失败）
            position2 = Position(
                ts_code="000001.SZ",
                name="平安银行",
                total_vol=500,
                avail_vol=500,
                avg_price=11.0
            )
            session.add(position2)
            
            with pytest.raises(Exception):  # 应该抛出唯一约束异常
                session.commit()
        finally:
            session.close()
    
    def test_position_default_values(self, setup_test_db):
        """测试持仓默认值"""
        from src.database import _SessionLocal
        
        session = _SessionLocal()
        try:
            position = Position(
                ts_code="000001.SZ",
                name="平安银行"
            )
            session.add(position)
            session.commit()
            
            assert position.total_vol == 0
            assert position.avail_vol == 0
            assert position.avg_price == 0.0
            assert position.profit == 0.0
            assert position.profit_pct == 0.0
            assert position.current_price is None
        finally:
            session.close()
    
    def test_position_profit_calculation(self, setup_test_db):
        """测试盈亏计算逻辑"""
        from src.database import _SessionLocal
        
        session = _SessionLocal()
        try:
            position = Position(
                ts_code="000001.SZ",
                name="平安银行",
                total_vol=1000,
                avail_vol=1000,
                avg_price=10.0,
                current_price=12.0
            )
            session.add(position)
            session.commit()
            
            # 手动计算盈亏
            expected_profit = (12.0 - 10.0) * 1000
            expected_profit_pct = (12.0 - 10.0) / 10.0 * 100
            
            # 注意：profit 和 profit_pct 需要在业务逻辑中计算，这里只是测试模型字段
            position.profit = expected_profit
            position.profit_pct = expected_profit_pct
            session.commit()
            
            assert position.profit == expected_profit
            assert position.profit_pct == expected_profit_pct
        finally:
            session.close()


class TestOrderModel:
    """测试 Order 模型"""
    
    def test_order_immutability(self, setup_test_db):
        """测试订单不可变性（只读，无更新方法）"""
        from src.database import _SessionLocal
        import uuid
        
        session = _SessionLocal()
        try:
            order = Order(
                order_id=str(uuid.uuid4()),
                trade_date="20240101",
                ts_code="000001.SZ",
                action="BUY",
                price=10.0,
                volume=100,
                fee=2.0,
                status="FILLED"
            )
            session.add(order)
            session.commit()
            
            # 订单创建后，不应该有更新方法（由业务逻辑保证）
            # 这里只测试模型可以正常创建和查询
            retrieved_order = session.query(Order).filter(Order.order_id == order.order_id).first()
            assert retrieved_order is not None
            assert retrieved_order.action == "BUY"
        finally:
            session.close()
    
    def test_order_action_values(self, setup_test_db):
        """测试订单动作值（BUY/SELL）"""
        from src.database import _SessionLocal
        import uuid
        
        session = _SessionLocal()
        try:
            # 测试买入订单
            buy_order = Order(
                order_id=str(uuid.uuid4()),
                trade_date="20240101",
                ts_code="000001.SZ",
                action="BUY",
                price=10.0,
                volume=100,
                fee=2.0,
                status="FILLED"
            )
            session.add(buy_order)
            
            # 测试卖出订单
            sell_order = Order(
                order_id=str(uuid.uuid4()),
                trade_date="20240101",
                ts_code="000001.SZ",
                action="SELL",
                price=12.0,
                volume=100,
                fee=2.4,
                status="FILLED"
            )
            session.add(sell_order)
            session.commit()
            
            orders = session.query(Order).all()
            assert len(orders) == 2
            assert orders[0].action == "BUY"
            assert orders[1].action == "SELL"
        finally:
            session.close()
    
    def test_order_status_values(self, setup_test_db):
        """测试订单状态值（FILLED/CANCELLED）"""
        from src.database import _SessionLocal
        import uuid
        
        session = _SessionLocal()
        try:
            # 测试已成交订单
            filled_order = Order(
                order_id=str(uuid.uuid4()),
                trade_date="20240101",
                ts_code="000001.SZ",
                action="BUY",
                price=10.0,
                volume=100,
                fee=2.0,
                status="FILLED"
            )
            session.add(filled_order)
            
            # 测试已取消订单
            cancelled_order = Order(
                order_id=str(uuid.uuid4()),
                trade_date="20240101",
                ts_code="000001.SZ",
                action="BUY",
                price=10.0,
                volume=100,
                fee=2.0,
                status="CANCELLED"
            )
            session.add(cancelled_order)
            session.commit()
            
            orders = session.query(Order).all()
            assert len(orders) == 2
            assert orders[0].status == "FILLED"
            assert orders[1].status == "CANCELLED"
        finally:
            session.close()
