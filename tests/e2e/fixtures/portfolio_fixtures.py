"""
Portfolio E2E Test Fixtures
提供Portfolio测试所需的数据和Mock
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from typing import Dict, Any, List
import uuid

from src.database import Account, Position, Order, _SessionLocal, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def sample_portfolio_positions():
    """示例持仓数据（新模型格式）"""
    return [
        {
            'ts_code': '000001.SZ',
            'name': '平安银行',
            'total_vol': 1000,
            'avail_vol': 1000,
            'avg_price': 10.0,
            'current_price': 10.5,
            'profit': 500.0,
            'profit_pct': 5.0,
        },
        {
            'ts_code': '000002.SZ',
            'name': '万科A',
            'total_vol': 500,
            'avail_vol': 500,
            'avg_price': 15.0,
            'current_price': 15.8,
            'profit': 400.0,
            'profit_pct': 5.33,
        },
        {
            'ts_code': '600000.SH',
            'name': '浦发银行',
            'total_vol': 2000,
            'avail_vol': 2000,
            'avg_price': 8.5,
            'current_price': 8.7,
            'profit': 400.0,
            'profit_pct': 2.35,
        },
    ]


@pytest.fixture
def sample_account():
    """示例账户数据"""
    return {
        'id': 1,
        'cash': 100000.0,
        'market_value': 50000.0,
        'total_asset': 150000.0,
        'frozen_cash': 0.0,
    }


@pytest.fixture
def sample_stock_daily_data():
    """Mock股票日线数据（用于价格查询）"""
    trade_date = datetime.now()
    # 跳过周末
    while trade_date.weekday() >= 5:
        trade_date -= timedelta(days=1)
    
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH'],
        'trade_date': [trade_date.strftime('%Y%m%d')] * 3,
        'close': [10.5, 15.8, 8.7]
    })


@pytest.fixture
def test_db_session(tmp_path, monkeypatch):
    """创建测试数据库会话"""
    import src.database
    
    # 创建临时数据库
    test_db_path = tmp_path / f"test_daas_{uuid.uuid4().hex[:8]}.db"
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存原始路径和engine
    original_db_path = src.database._DB_PATH
    original_engine = getattr(src.database, '_engine', None)
    original_SessionLocal = getattr(src.database, '_SessionLocal', None)
    
    # 设置测试数据库路径
    src.database._DB_PATH = test_db_path
    
    # 创建新的engine和session
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    
    # 创建表
    Base.metadata.create_all(engine)
    
    # 更新database模块的全局变量
    src.database._engine = engine
    src.database._SessionLocal = SessionLocal
    
    # 清空所有表，确保测试数据库是干净的
    with SessionLocal() as session:
        session.query(Position).delete()
        session.query(Account).delete()
        session.query(Order).delete()
        session.commit()
    
    # 创建session供测试使用
    session = SessionLocal()
    
    yield session
    
    # 清理
    session.close()
    engine.dispose()
    
    # 恢复原始值
    src.database._DB_PATH = original_db_path
    if original_engine:
        src.database._engine = original_engine
    if original_SessionLocal:
        src.database._SessionLocal = original_SessionLocal
    
    # 删除测试数据库
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
def populated_test_db(test_db_session, sample_portfolio_positions, sample_account):
    """填充测试数据的数据库"""
    from src.repositories.portfolio_repository import PortfolioRepository
    
    # 初始化账户
    repo = PortfolioRepository()
    repo.initialize_account(initial_cash=sample_account['cash'])
    
    # 插入持仓数据
    for pos_data in sample_portfolio_positions:
        position = Position(
            ts_code=pos_data['ts_code'],
            name=pos_data['name'],
            total_vol=pos_data['total_vol'],
            avail_vol=pos_data['avail_vol'],
            avg_price=pos_data['avg_price'],
            current_price=pos_data['current_price'],
            profit=pos_data['profit'],
            profit_pct=pos_data['profit_pct'],
        )
        test_db_session.add(position)
    
    test_db_session.commit()
    
    # 确保数据库设置完成后再返回
    # 这样后续的Repository会使用正确的_SessionLocal
    import src.database
    # 验证数据库路径已更新
    assert 'test_daas_' in str(src.database._DB_PATH) or 'tmp' in str(src.database._DB_PATH).lower()
    
    return test_db_session


@pytest.fixture
def mock_data_provider(sample_stock_daily_data):
    """Mock DataProvider"""
    from src.data_provider import DataProvider
    from src.config_manager import ConfigManager
    
    mock_provider = MagicMock(spec=DataProvider)
    mock_provider._tushare_client = MagicMock()
    
    # Mock get_daily方法
    def mock_get_daily(ts_code, trade_date=None, end_date=None, limit=None, fields=None):
        # 返回对应股票的数据
        filtered = sample_stock_daily_data[sample_stock_daily_data['ts_code'] == ts_code]
        if not filtered.empty:
            return filtered[['trade_date', 'close']]
        return pd.DataFrame()
    
    mock_provider._tushare_client.get_daily = MagicMock(side_effect=mock_get_daily)
    
    return mock_provider


@pytest.fixture
def mock_config():
    """Mock ConfigManager"""
    from src.config_manager import ConfigManager
    from unittest.mock import Mock
    
    config = MagicMock(spec=ConfigManager)
    config.get = Mock(side_effect=lambda key, default=None: {
        'portfolio.default_shares': 100,
        'portfolio.default_stop_loss_ratio': 0.9,
    }.get(key, default))
    
    return config


@pytest.fixture
def expected_position_schema():
    """预期的Position响应schema（新模型）"""
    return {
        'id': int,
        'ts_code': str,
        'name': str,
        'total_vol': int,
        'avail_vol': int,
        'avg_price': (int, float),
        'current_price': (int, float, type(None)),
        'profit': (int, float),
        'profit_pct': (int, float),
    }


@pytest.fixture
def expected_metrics_schema():
    """预期的Metrics响应schema"""
    return {
        'total_return': (int, float),
        'max_drawdown': (int, float),
        'sharpe_ratio': (int, float),
    }


@pytest.fixture
def expected_add_position_request():
    """添加持仓请求示例"""
    return {
        'code': '000001.SZ',
        'name': '平安银行',
        'cost': 10.0,
        'shares': 1000,
        'stop_loss_price': 9.0,
    }


@pytest.fixture
def expected_update_position_request():
    """更新持仓请求示例"""
    return {
        'cost': 10.5,
        'shares': 1200,
        'stop_loss_price': 9.5,
    }
