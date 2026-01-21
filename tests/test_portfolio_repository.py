"""
Portfolio Repository Unit Tests
组合管理仓库层单元测试
"""
import pytest
from unittest.mock import patch

from src.repositories.portfolio_repository import PortfolioRepository
from src.database import Account, Position, Order, Base, _engine, _SessionLocal
from api.utils.exceptions import (
    InsufficientFundsError,
    PositionNotFoundError,
    InsufficientVolumeError,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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
    
    # 清理测试数据
    with src.database._SessionLocal() as session:
        session.query(Order).delete()
        session.query(Position).delete()
        session.query(Account).delete()
        session.commit()
    
    # 恢复原始值
    src.database._DB_PATH = original_db_path
    src.database._engine = original_engine
    src.database._SessionLocal = original_SessionLocal


@pytest.fixture
def repository():
    """创建 Repository 实例"""
    # 注意：数据库清理由 setup_test_db fixture 处理
    return PortfolioRepository()


@pytest.fixture
def initialized_account(repository):
    """初始化账户"""
    return repository.initialize_account(initial_cash=100000.0)


class TestPortfolioRepository:
    """测试 PortfolioRepository"""
    
    def test_get_account_not_exists(self, repository):
        """测试获取不存在的账户"""
        account = repository.get_account()
        assert account is None
    
    def test_get_account_exists(self, repository, initialized_account):
        """测试获取存在的账户"""
        account = repository.get_account()
        assert account is not None
        assert account.id == 1
        assert account.cash == 100000.0
    
    def test_initialize_account(self, repository):
        """测试初始化账户"""
        account = repository.initialize_account(initial_cash=50000.0)
        assert account.id == 1
        assert account.cash == 50000.0
        assert account.total_asset == 50000.0
        assert account.market_value == 0.0
    
    def test_get_positions_empty(self, repository):
        """测试获取空持仓列表"""
        positions = repository.get_positions()
        assert positions == []
    
    def test_get_position_not_exists(self, repository):
        """测试获取不存在的持仓"""
        position = repository.get_position("000001.SZ")
        assert position is None
    
    def test_create_order_buy_success(self, repository, initialized_account):
        """测试成功创建买入订单"""
        order_data = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 10.0,
            'volume': 1000,
            'fee': 2.0,
            'strategy_tag': 'test',
            'name': '平安银行'
        }
        
        order = repository.create_order(order_data)
        
        assert order is not None
        assert order.action == 'BUY'
        assert order.status == 'FILLED'
        
        # 验证账户资金已扣除
        account = repository.get_account()
        assert account.cash == 100000.0 - (10.0 * 1000 + 2.0)
        
        # 验证持仓已创建
        position = repository.get_position('000001.SZ')
        assert position is not None
        assert position.total_vol == 1000
        assert position.avail_vol == 0  # T+1 规则
        assert position.avg_price == 10.0
    
    def test_create_order_buy_insufficient_funds(self, repository, initialized_account):
        """测试买入订单资金不足"""
        order_data = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 1000.0,  # 价格很高
            'volume': 1000,
            'fee': 2000.0,
            'name': '平安银行'
        }
        
        with pytest.raises(InsufficientFundsError):
            repository.create_order(order_data)
    
    def test_create_order_buy_update_existing_position(self, repository, initialized_account):
        """测试买入订单更新现有持仓"""
        # 第一次买入
        order_data1 = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 10.0,
            'volume': 1000,
            'fee': 2.0,
            'name': '平安银行'
        }
        repository.create_order(order_data1)
        
        # 第二次买入（更高价格）
        order_data2 = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 12.0,
            'volume': 500,
            'fee': 1.2,
            'name': '平安银行'
        }
        repository.create_order(order_data2)
        
        # 验证持仓已更新
        position = repository.get_position('000001.SZ')
        assert position.total_vol == 1500
        assert position.avail_vol == 0  # T+1 规则，仍然为0
        # 验证平均成本价：((10.0 * 1000) + (12.0 * 500)) / 1500 = 10.67
        expected_avg_price = (10.0 * 1000 + 12.0 * 500) / 1500
        assert abs(position.avg_price - expected_avg_price) < 0.01
    
    def test_create_order_sell_success(self, repository, initialized_account):
        """测试成功创建卖出订单"""
        # 先买入
        buy_order = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 10.0,
            'volume': 1000,
            'fee': 2.0,
            'name': '平安银行'
        }
        repository.create_order(buy_order)
        
        # 验证持仓已创建
        position_after_buy = repository.get_position('000001.SZ')
        assert position_after_buy is not None, "Position should exist after buy order"
        assert position_after_buy.total_vol == 1000, "Position total_vol should be 1000"
        
        # 手动设置 avail_vol（模拟 T+1 后）
        from src.database import _SessionLocal
        session = _SessionLocal()
        try:
            position = session.query(Position).filter(Position.ts_code == '000001.SZ').first()
            assert position is not None, "Position should exist in session"
            position.avail_vol = 1000
            session.commit()
        finally:
            session.close()
        
        # 验证 avail_vol 已更新
        position_after_update = repository.get_position('000001.SZ')
        assert position_after_update.avail_vol == 1000, f"avail_vol should be 1000, got {position_after_update.avail_vol}"
        
        # 卖出
        sell_order = {
            'trade_date': '20240102',
            'ts_code': '000001.SZ',
            'action': 'SELL',
            'price': 12.0,
            'volume': 500,
            'fee': 1.2,
            'reason': 'test'
        }
        order = repository.create_order(sell_order)
        
        assert order is not None
        assert order.action == 'SELL'
        assert order.status == 'FILLED'
        
        # 验证账户资金已增加
        account = repository.get_account()
        expected_cash = 100000.0 - (10.0 * 1000 + 2.0) + (12.0 * 500 - 1.2)
        assert abs(account.cash - expected_cash) < 0.01
        
        # 验证持仓已更新
        position = repository.get_position('000001.SZ')
        assert position.total_vol == 500
        assert position.avail_vol == 500
    
    def test_create_order_sell_position_not_found(self, repository, initialized_account):
        """测试卖出订单持仓不存在"""
        sell_order = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'SELL',
            'price': 12.0,
            'volume': 500,
            'fee': 1.2
        }
        
        with pytest.raises(PositionNotFoundError):
            repository.create_order(sell_order)
    
    def test_create_order_sell_insufficient_volume(self, repository, initialized_account):
        """测试卖出订单可用数量不足"""
        # 先买入
        buy_order = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 10.0,
            'volume': 1000,
            'fee': 2.0,
            'name': '平安银行'
        }
        repository.create_order(buy_order)
        
        # 尝试卖出（avail_vol 为 0，T+1 规则）
        sell_order = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'SELL',
            'price': 12.0,
            'volume': 500,
            'fee': 1.2
        }
        
        with pytest.raises(InsufficientVolumeError):
            repository.create_order(sell_order)
    
    def test_create_order_sell_delete_position_when_zero(self, repository, initialized_account):
        """测试卖出后持仓为0时删除持仓"""
        # 先买入
        buy_order = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 10.0,
            'volume': 1000,
            'fee': 2.0,
            'name': '平安银行'
        }
        repository.create_order(buy_order)
        
        # 验证持仓已创建
        position_after_buy = repository.get_position('000001.SZ')
        assert position_after_buy is not None, "Position should exist after buy order"
        
        # 手动设置 avail_vol（模拟 T+1 后）
        from src.database import _SessionLocal
        session = _SessionLocal()
        try:
            position = session.query(Position).filter(Position.ts_code == '000001.SZ').first()
            assert position is not None, "Position should exist in session"
            position.avail_vol = 1000
            session.commit()
        finally:
            session.close()
        
        # 验证 avail_vol 已更新
        position_after_update = repository.get_position('000001.SZ')
        assert position_after_update.avail_vol == 1000, f"avail_vol should be 1000, got {position_after_update.avail_vol}"
        
        # 全部卖出
        sell_order = {
            'trade_date': '20240102',
            'ts_code': '000001.SZ',
            'action': 'SELL',
            'price': 12.0,
            'volume': 1000,
            'fee': 2.4
        }
        repository.create_order(sell_order)
        
        # 验证持仓已删除
        position = repository.get_position('000001.SZ')
        assert position is None
    
    def test_update_positions_market_value(self, repository, initialized_account):
        """测试批量更新持仓市值"""
        # 先买入
        buy_order = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 10.0,
            'volume': 1000,
            'fee': 2.0,
            'name': '平安银行'
        }
        repository.create_order(buy_order)
        
        # 更新价格
        prices_dict = {'000001.SZ': 12.0}
        repository.update_positions_market_value(prices_dict)
        
        # 验证持仓价格已更新
        position = repository.get_position('000001.SZ')
        assert position.current_price == 12.0
        assert position.profit == (12.0 - 10.0) * 1000
        assert abs(position.profit_pct - ((12.0 - 10.0) / 10.0 * 100)) < 0.01
        
        # 验证账户市值已更新
        account = repository.get_account()
        assert account.market_value == 12.0 * 1000
        assert account.total_asset == account.cash + account.market_value
    
    def test_transaction_rollback_on_error(self, repository, initialized_account):
        """测试错误时事务回滚"""
        # 尝试买入（资金不足，应该回滚）
        order_data = {
            'trade_date': '20240101',
            'ts_code': '000001.SZ',
            'action': 'BUY',
            'price': 1000.0,
            'volume': 1000,
            'fee': 2000.0,
            'name': '平安银行'
        }
        
        initial_cash = repository.get_account().cash
        
        with pytest.raises(InsufficientFundsError):
            repository.create_order(order_data)
        
        # 验证账户资金未改变（事务已回滚）
        account = repository.get_account()
        assert account.cash == initial_cash
        
        # 验证没有创建持仓
        position = repository.get_position('000001.SZ')
        assert position is None
