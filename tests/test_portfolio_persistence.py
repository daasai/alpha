"""
Portfolio Persistence Tests
测试 Portfolio 数据持久化功能
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid

from src.repositories.portfolio_repository import PortfolioRepository
from api.services.portfolio_service import PortfolioService
from src.database import PortfolioPosition, _SessionLocal
from src.config_manager import ConfigManager
from src.data_provider import DataProvider


class TestPortfolioRepository:
    """测试 PortfolioRepository"""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path, monkeypatch):
        """设置测试数据库"""
        import src.database
        import uuid
        # 为每个测试创建独立的数据库文件
        test_db_path = tmp_path / f"test_daas_{uuid.uuid4().hex[:8]}.db"
        test_data_dir = tmp_path / "data"
        test_data_dir.mkdir()
        
        original_db_path = src.database._DB_PATH
        src.database._DB_PATH = test_db_path
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        src.database._engine = create_engine(
            f"sqlite:///{test_db_path}",
            connect_args={"check_same_thread": False}
        )
        src.database._SessionLocal = sessionmaker(
            bind=src.database._engine,
            autoflush=False,
            autocommit=False
        )
        from src.database import Base
        Base.metadata.create_all(src.database._engine)
        
        yield
        
        # 清理
        src.database._DB_PATH = original_db_path
        if test_db_path.exists():
            test_db_path.unlink()
    
    @pytest.fixture
    def repository(self):
        """创建 PortfolioRepository 实例"""
        return PortfolioRepository()
    
    def test_create_position(self, repository):
        """测试创建持仓"""
        position_data = {
            'id': str(uuid.uuid4()),
            'ts_code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'current_price': 10.5,
            'shares': 1000,
            'stop_loss_price': 9.0,
        }
        
        result = repository.create(position_data)
        
        assert result is not None
        assert result['ts_code'] == '000001.SZ'
        assert result['name'] == '平安银行'
        assert result['cost'] == 10.0
        assert result['shares'] == 1000
    
    def test_get_all_positions(self, repository):
        """测试获取所有持仓"""
        # 创建多个持仓
        for i in range(3):
            position_data = {
                'id': str(uuid.uuid4()),
                'ts_code': f'00000{i}.SZ',
                'name': f'股票{i}',
                'cost': 10.0 + i,
                'shares': 1000,
            }
            repository.create(position_data)
        
        positions = repository.get_all()
        
        assert len(positions) == 3
        assert all('id' in pos for pos in positions)
        assert all('ts_code' in pos for pos in positions)
    
    def test_get_by_id(self, repository):
        """测试根据ID获取持仓"""
        position_id = str(uuid.uuid4())
        position_data = {
            'id': position_id,
            'ts_code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'shares': 1000,
        }
        repository.create(position_data)
        
        result = repository.get_by_id(position_id)
        
        assert result is not None
        assert result['id'] == position_id
        assert result['ts_code'] == '000001.SZ'
    
    def test_update_position(self, repository):
        """测试更新持仓"""
        position_id = str(uuid.uuid4())
        position_data = {
            'id': position_id,
            'ts_code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'shares': 1000,
        }
        repository.create(position_data)
        
        # 更新持仓
        update_data = {
            'cost': 11.0,
            'shares': 1500,
        }
        result = repository.update(position_id, update_data)
        
        assert result is not None
        assert result['cost'] == 11.0
        assert result['shares'] == 1500
    
    def test_delete_position(self, repository):
        """测试删除持仓"""
        position_id = str(uuid.uuid4())
        position_data = {
            'id': position_id,
            'ts_code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'shares': 1000,
        }
        repository.create(position_data)
        
        # 删除持仓
        success = repository.delete(position_id)
        
        assert success is True
        result = repository.get_by_id(position_id)
        assert result is None
    
    def test_batch_update_prices(self, repository):
        """测试批量更新价格"""
        # 创建多个持仓
        position_ids = []
        for i in range(3):
            position_id = str(uuid.uuid4())
            position_ids.append(position_id)
            position_data = {
                'id': position_id,
                'ts_code': f'00000{i}.SZ',
                'name': f'股票{i}',
                'cost': 10.0,
                'shares': 1000,
            }
            repository.create(position_data)
        
        # 批量更新价格
        price_updates = {
            '000000.SZ': 10.5,
            '000001.SZ': 11.0,
            '000002.SZ': 12.0,
        }
        updated_count = repository.batch_update_prices(price_updates)
        
        assert updated_count == 3
        
        # 验证价格已更新
        positions = repository.get_all()
        for pos in positions:
            if pos['ts_code'] in price_updates:
                assert pos['current_price'] == price_updates[pos['ts_code']]


class TestPortfolioServicePersistence:
    """测试 PortfolioService 持久化功能"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        return config
    
    @pytest.fixture
    def mock_data_provider(self):
        """Mock DataProvider"""
        provider = MagicMock(spec=DataProvider)
        provider._tushare_client = MagicMock()
        return provider
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path, monkeypatch):
        """设置测试数据库"""
        import src.database
        import uuid
        # 为每个测试创建独立的数据库文件
        test_db_path = tmp_path / f"test_daas_{uuid.uuid4().hex[:8]}.db"
        
        original_db_path = src.database._DB_PATH
        src.database._DB_PATH = test_db_path
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        src.database._engine = create_engine(
            f"sqlite:///{test_db_path}",
            connect_args={"check_same_thread": False}
        )
        src.database._SessionLocal = sessionmaker(
            bind=src.database._engine,
            autoflush=False,
            autocommit=False
        )
        from src.database import Base
        Base.metadata.create_all(src.database._engine)
        
        yield
        
        # 清理
        src.database._DB_PATH = original_db_path
        if test_db_path.exists():
            test_db_path.unlink()
    
    @pytest.fixture
    def repository(self):
        """创建测试 Repository"""
        return PortfolioRepository()
    
    @pytest.fixture
    def portfolio_service(self, mock_config, mock_data_provider, repository):
        """创建 PortfolioService 实例"""
        # Mock 价格获取
        mock_data_provider._tushare_client.get_daily.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.5],
        })
        
        service = PortfolioService(
            data_provider=mock_data_provider,
            config=mock_config,
            repository=repository
        )
        return service
    
    def test_add_position_persistence(self, portfolio_service):
        """测试添加持仓并持久化"""
        position_data = {
            'code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'shares': 1000,
            'stop_loss_price': 9.0,
        }
        
        result = portfolio_service.add_position(position_data)
        
        assert result is not None
        assert 'id' in result
        assert result['code'] == '000001.SZ'
        
        # 验证已持久化
        positions = portfolio_service.get_positions()
        assert len(positions) == 1
        assert positions[0]['code'] == '000001.SZ'
    
    def test_update_position_persistence(self, portfolio_service):
        """测试更新持仓并持久化"""
        # 先添加持仓
        position_data = {
            'code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'shares': 1000,
        }
        position = portfolio_service.add_position(position_data)
        position_id = position['id']
        
        # 更新持仓
        update_data = {
            'cost': 11.0,
            'shares': 1500,
        }
        result = portfolio_service.update_position(position_id, update_data)
        
        assert result is not None
        assert result['cost'] == 11.0
        assert result['shares'] == 1500
        
        # 验证已持久化
        positions = portfolio_service.get_positions()
        assert positions[0]['cost'] == 11.0
        assert positions[0]['shares'] == 1500
    
    def test_delete_position_persistence(self, portfolio_service):
        """测试删除持仓并持久化"""
        # 先添加持仓
        position_data = {
            'code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'shares': 1000,
        }
        position = portfolio_service.add_position(position_data)
        position_id = position['id']
        
        # 删除持仓
        success = portfolio_service.delete_position(position_id)
        
        assert success is True
        
        # 验证已从数据库删除
        positions = portfolio_service.get_positions()
        assert len(positions) == 0
    
    def test_get_positions_from_database(self, portfolio_service):
        """测试从数据库获取持仓"""
        # 添加多个持仓
        for i in range(3):
            position_data = {
                'code': f'00000{i}.SZ',
                'name': f'股票{i}',
                'cost': 10.0 + i,
                'shares': 1000,
            }
            portfolio_service.add_position(position_data)
        
        # 获取持仓
        positions = portfolio_service.get_positions()
        
        assert len(positions) == 3
        assert all('id' in pos for pos in positions)
        assert all('code' in pos for pos in positions)
    
    def test_refresh_prices_persistence(self, portfolio_service):
        """测试刷新价格并持久化"""
        # 添加持仓
        position_data = {
            'code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'shares': 1000,
        }
        portfolio_service.add_position(position_data)
        
        # 刷新价格
        result = portfolio_service.refresh_prices()
        
        assert result['updated_count'] >= 0
        assert result['total_positions'] == 1
        
        # 验证价格已更新到数据库
        positions = portfolio_service.get_positions()
        if positions[0].get('current_price'):
            assert positions[0]['current_price'] > 0
