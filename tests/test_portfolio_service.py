"""
Portfolio Service Unit Tests
组合管理服务层单元测试
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd

from api.services.portfolio_service import PortfolioService
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.repositories.portfolio_repository import PortfolioRepository
from api.utils.exceptions import (
    AccountNotInitializedError,
    InsufficientFundsError,
    PositionNotFoundError,
    InsufficientVolumeError,
)


@pytest.fixture
def mock_data_provider():
    """创建模拟 DataProvider"""
    provider = Mock(spec=DataProvider)
    provider._tushare_client = Mock()
    return provider


@pytest.fixture
def mock_config():
    """创建模拟 ConfigManager"""
    config = Mock(spec=ConfigManager)
    return config


@pytest.fixture
def mock_repository():
    """创建模拟 Repository"""
    return Mock(spec=PortfolioRepository)


@pytest.fixture
def service(mock_data_provider, mock_config, mock_repository):
    """创建 PortfolioService 实例"""
    return PortfolioService(
        data_provider=mock_data_provider,
        config=mock_config,
        repository=mock_repository
    )


class TestPortfolioService:
    """测试 PortfolioService"""
    
    def test_get_account(self, service, mock_repository):
        """测试获取账户"""
        from src.database import Account
        from datetime import datetime
        
        account = Account(
            id=1,
            cash=100000.0,
            total_asset=100000.0,
            market_value=0.0,
            frozen_cash=0.0
        )
        mock_repository.get_account.return_value = account
        
        result = service.get_account()
        
        assert result is not None
        assert result['id'] == 1
        assert result['cash'] == 100000.0
        mock_repository.get_account.assert_called_once()
    
    def test_get_account_not_exists(self, service, mock_repository):
        """测试获取不存在的账户"""
        mock_repository.get_account.return_value = None
        
        result = service.get_account()
        
        assert result is None
    
    def test_get_positions(self, service, mock_repository):
        """测试获取持仓列表"""
        from src.database import Position
        
        positions = [
            Position(
                id=1,
                ts_code='000001.SZ',
                name='平安银行',
                total_vol=1000,
                avail_vol=1000,
                avg_price=10.0,
                current_price=12.0,
                profit=2000.0,
                profit_pct=20.0
            )
        ]
        mock_repository.get_positions.return_value = positions
        
        result = service.get_positions()
        
        assert len(result) == 1
        assert result[0]['ts_code'] == '000001.SZ'
        mock_repository.get_positions.assert_called_once()
    
    def test_get_position(self, service, mock_repository):
        """测试获取单个持仓"""
        from src.database import Position
        
        position = Position(
            id=1,
            ts_code='000001.SZ',
            name='平安银行',
            total_vol=1000,
            avail_vol=1000,
            avg_price=10.0
        )
        mock_repository.get_position.return_value = position
        
        result = service.get_position('000001.SZ')
        
        assert result is not None
        assert result['ts_code'] == '000001.SZ'
        mock_repository.get_position.assert_called_once_with('000001.SZ')
    
    def test_execute_buy_success(self, service, mock_repository, mock_data_provider):
        """测试成功执行买入"""
        from src.database import Account, Order
        from datetime import datetime
        import uuid
        
        # 设置账户
        account = Account(id=1, cash=100000.0, total_asset=100000.0)
        mock_repository.get_account.return_value = account
        
        # 设置股票基本信息
        basic_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['平安银行']
        })
        mock_data_provider._tushare_client.get_stock_basic.return_value = basic_df
        
        # 设置订单
        order = Order(
            order_id=str(uuid.uuid4()),
            trade_date='20240101',
            ts_code='000001.SZ',
            action='BUY',
            price=10.0,
            volume=1000,
            fee=2.0,
            status='FILLED'
        )
        mock_repository.create_order.return_value = order
        
        # Mock get_trade_date
        with patch('src.strategy.get_trade_date', return_value='20240101'):
            result = service.execute_buy(
                ts_code='000001.SZ',
                price=10.0,
                volume=1000,
                strategy_tag='test'
            )
        
        assert result is not None
        assert result['action'] == 'BUY'
        assert result['status'] == 'FILLED'
        mock_repository.create_order.assert_called_once()
    
    def test_execute_buy_account_not_initialized(self, service, mock_repository):
        """测试买入时账户未初始化"""
        mock_repository.get_account.return_value = None
        
        with patch('src.strategy.get_trade_date', return_value='20240101'):
            with pytest.raises(AccountNotInitializedError):
                service.execute_buy(
                    ts_code='000001.SZ',
                    price=10.0,
                    volume=1000
                )
    
    def test_execute_buy_insufficient_funds(self, service, mock_repository):
        """测试买入时资金不足"""
        from src.database import Account
        
        account = Account(id=1, cash=100.0, total_asset=100.0)
        mock_repository.get_account.return_value = account
        
        with patch('src.strategy.get_trade_date', return_value='20240101'):
            with pytest.raises(InsufficientFundsError):
                service.execute_buy(
                    ts_code='000001.SZ',
                    price=10.0,
                    volume=1000  # 需要 10000 + 20 = 10020，但只有 100
                )
    
    def test_execute_sell_success(self, service, mock_repository):
        """测试成功执行卖出"""
        from src.database import Position, Order
        import uuid
        
        # 设置持仓
        position = Position(
            id=1,
            ts_code='000001.SZ',
            name='平安银行',
            total_vol=1000,
            avail_vol=1000,  # 可用数量充足
            avg_price=10.0
        )
        mock_repository.get_position.return_value = position
        
        # 设置订单
        order = Order(
            order_id=str(uuid.uuid4()),
            trade_date='20240101',
            ts_code='000001.SZ',
            action='SELL',
            price=12.0,
            volume=500,
            fee=1.2,
            status='FILLED'
        )
        mock_repository.create_order.return_value = order
        
        with patch('src.strategy.get_trade_date', return_value='20240101'):
            result = service.execute_sell(
                ts_code='000001.SZ',
                price=12.0,
                volume=500,
                reason='test'
            )
        
        assert result is not None
        assert result['action'] == 'SELL'
        assert result['status'] == 'FILLED'
        mock_repository.create_order.assert_called_once()
    
    def test_execute_sell_position_not_found(self, service, mock_repository):
        """测试卖出时持仓不存在"""
        mock_repository.get_position.return_value = None
        
        with patch('src.strategy.get_trade_date', return_value='20240101'):
            with pytest.raises(PositionNotFoundError):
                service.execute_sell(
                    ts_code='000001.SZ',
                    price=12.0,
                    volume=500
                )
    
    def test_execute_sell_insufficient_volume(self, service, mock_repository):
        """测试卖出时可用数量不足"""
        from src.database import Position
        
        position = Position(
            id=1,
            ts_code='000001.SZ',
            name='平安银行',
            total_vol=1000,
            avail_vol=100,  # 可用数量不足
            avg_price=10.0
        )
        mock_repository.get_position.return_value = position
        
        with patch('src.strategy.get_trade_date', return_value='20240101'):
            with pytest.raises(InsufficientVolumeError):
                service.execute_sell(
                    ts_code='000001.SZ',
                    price=12.0,
                    volume=500  # 需要 500，但只有 100
                )
    
    def test_sync_latest_prices(self, service, mock_repository, mock_data_provider):
        """测试同步最新价格"""
        from src.database import Position
        
        positions = [
            Position(
                id=1,
                ts_code='000001.SZ',
                name='平安银行',
                total_vol=1000,
                avail_vol=1000,
                avg_price=10.0
            ),
            Position(
                id=2,
                ts_code='000002.SZ',
                name='万科A',
                total_vol=500,
                avail_vol=500,
                avg_price=20.0
            )
        ]
        mock_repository.get_positions.return_value = positions
        
        # Mock get_daily 返回价格
        daily_df1 = pd.DataFrame({'close': [12.0]})
        daily_df2 = pd.DataFrame({'close': [22.0]})
        mock_data_provider._tushare_client.get_daily.side_effect = [daily_df1, daily_df2]
        
        with patch('src.strategy.get_trade_date', return_value='20240101'):
            result = service.sync_latest_prices()
        
        assert result['updated_count'] == 2
        assert result['total_positions'] == 2
        assert 'timestamp' in result
        
        # 验证调用了 update_positions_market_value
        mock_repository.update_positions_market_value.assert_called_once()
        call_args = mock_repository.update_positions_market_value.call_args[0][0]
        assert call_args['000001.SZ'] == 12.0
        assert call_args['000002.SZ'] == 22.0
    
    def test_sync_latest_prices_empty(self, service, mock_repository):
        """测试同步空持仓列表"""
        mock_repository.get_positions.return_value = []
        
        result = service.sync_latest_prices()
        
        assert result['updated_count'] == 0
        assert result['total_positions'] == 0
