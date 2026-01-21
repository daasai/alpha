"""
Dashboard E2E Test Fixtures
提供Dashboard测试所需的数据和Mock
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from typing import Dict, Any, List
import uuid

from src.database import Position, _SessionLocal, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def mock_index_daily_data():
    """Mock指数日线数据（60天）"""
    end_date = datetime.now()
    dates = []
    prices = []
    
    # 生成60天的数据
    base_price = 3000.0
    for i in range(60):
        date = end_date - timedelta(days=59-i)
        # 跳过周末
        while date.weekday() >= 5:
            date -= timedelta(days=1)
        
        # 模拟价格波动
        price = base_price + np.random.uniform(-100, 100)
        base_price = price
        
        dates.append(date.strftime('%Y%m%d'))
        prices.append(round(price, 2))
    
    df = pd.DataFrame({
        'trade_date': dates,
        'close': prices
    })
    return df


@pytest.fixture
def mock_index_daily_data_empty():
    """Mock空指数数据"""
    return pd.DataFrame(columns=['trade_date', 'close'])


@pytest.fixture
def sample_portfolio_positions():
    """示例持仓数据"""
    return [
        {
            'id': str(uuid.uuid4()),
            'ts_code': '000001.SZ',
            'name': '平安银行',
            'cost': 10.0,
            'current_price': 10.5,
            'shares': 1000,
            'stop_loss_price': 9.0,
        },
        {
            'id': str(uuid.uuid4()),
            'ts_code': '000002.SZ',
            'name': '万科A',
            'cost': 15.0,
            'current_price': 15.8,
            'shares': 500,
            'stop_loss_price': 13.5,
        },
        {
            'id': str(uuid.uuid4()),
            'ts_code': '600000.SH',
            'name': '浦发银行',
            'cost': 8.5,
            'current_price': 8.7,
            'shares': 2000,
            'stop_loss_price': 7.65,
        },
    ]


@pytest.fixture
def test_db_session(tmp_path, monkeypatch):
    """创建测试数据库会话"""
    import src.database
    
    # 创建临时数据库
    test_db_path = tmp_path / f"test_daas_{uuid.uuid4().hex[:8]}.db"
    test_data_dir = tmp_path / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存原始路径
    original_db_path = src.database._DB_PATH
    
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
    
    # 创建session
    session = SessionLocal()
    
    yield session
    
    # 清理
    session.close()
    engine.dispose()
    src.database._DB_PATH = original_db_path
    
    # 删除测试数据库
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
def populated_test_db(test_db_session, sample_portfolio_positions):
    """填充测试数据的数据库"""
    # 插入持仓数据
    for pos_data in sample_portfolio_positions:
        position = Position(
            ts_code=pos_data['ts_code'],
            name=pos_data['name'],
            avg_price=pos_data['cost'],  # cost -> avg_price
            current_price=pos_data['current_price'],
            total_vol=pos_data['shares'],  # shares -> total_vol
            avail_vol=0,  # T+1规则，初始可用为0
            profit=0.0,
            profit_pct=0.0,
        )
        test_db_session.add(position)
    
    test_db_session.commit()
    
    return test_db_session


@pytest.fixture
def mock_data_provider(mock_index_daily_data):
    """Mock DataProvider"""
    from src.data_provider import DataProvider
    from src.config_manager import ConfigManager
    
    mock_provider = MagicMock(spec=DataProvider)
    mock_provider._pro = MagicMock()
    
    # Mock _tushare_client 和 _pro
    mock_provider._tushare_client = MagicMock()
    mock_provider._tushare_client._pro = MagicMock()
    
    # Mock index_daily方法
    def mock_index_daily(ts_code, start_date, end_date, fields):
        return mock_index_daily_data.copy()
    
    mock_provider._tushare_client._pro.index_daily = MagicMock(side_effect=mock_index_daily)
    mock_provider._pro.index_daily = MagicMock(side_effect=mock_index_daily)
    
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
def expected_overview_schema():
    """预期的Overview响应schema"""
    return {
        'market_regime': {
            'regime': str,
            'is_bull': bool,
        },
        'sentiment': {
            'sentiment': (int, float),
            'change': (int, float, type(None)),
        },
        'target_position': {
            'position': (int, float),
            'label': str,
        },
        'portfolio_nav': {
            'nav': (int, float),
            'change_percent': (int, float, type(None)),
        },
    }


@pytest.fixture
def expected_market_trend_schema():
    """预期的Market Trend响应schema"""
    return {
        'index_code': str,
        'index_name': str,
        'data': list,
    }


@pytest.fixture
def expected_trend_data_point_schema():
    """预期的趋势数据点schema"""
    return {
        'date': str,
        'price': (int, float),
        'bbi': (int, float),
    }
