"""
Hunter E2E Test Fixtures
提供Hunter测试所需的数据和Mock
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
def mock_stock_basic_data():
    """Mock股票基础数据"""
    # 使用当前日期作为trade_date，确保与mock_history_data匹配
    trade_date = datetime.now().strftime('%Y%m%d')
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH', '600001.SH', '000858.SZ'],
        'name': ['平安银行', '万科A', '浦发银行', '邯郸钢铁', '五粮液'],
        'trade_date': [trade_date] * 5,
        'pe_ttm': [8.5, 12.3, 6.2, 25.5, 18.2],
        'pb': [0.8, 1.2, 0.6, 4.5, 3.2],
        'total_mv': [1500000, 2000000, 1200000, 800000, 5000000],  # 万元
        'dv_ttm': [2.5, 3.2, 1.8, 0.5, 1.2],  # 股息率
        'list_date': ['19910403', '19910129', '19991110', '19981224', '19980427'],  # 上市日期
        'mv': [1500000, 2000000, 1200000, 800000, 5000000],  # 市值（与total_mv相同）
        'dividend_yield': [2.5, 3.2, 1.8, 0.5, 1.2],  # 股息率（与dv_ttm相同）
    })


@pytest.fixture
def mock_history_data():
    """Mock历史日线数据（120天）"""
    # 使用当前日期作为最后一天，确保与mock_stock_basic_data的trade_date匹配
    end_date = datetime.now()
    # 确保最后一条数据是今天（不跳过周末，直接使用今天）
    trade_date_str = end_date.strftime('%Y%m%d')
    stocks = ['000001.SZ', '000002.SZ', '600000.SH', '600001.SH', '000858.SZ']
    
    data = []
    # 生成119天的历史数据 + 1天当前数据
    for i in range(120):
        if i == 119:
            # 最后一条使用当前日期
            date_str = trade_date_str
        else:
            date = end_date - timedelta(days=119-i)
            # 跳过周末
            while date.weekday() >= 5:
                date -= timedelta(days=1)
            date_str = date.strftime('%Y%m%d')
        
        for stock in stocks:
            # 模拟价格波动
            base_price = 10.0 if '000001' in stock else 15.0 if '000002' in stock else 8.0
            price = base_price + np.random.uniform(-2, 2)
            volume = np.random.uniform(1000000, 5000000)
            
            data.append({
                'ts_code': stock,
                'trade_date': date_str,
                'open': price * 0.99,
                'high': price * 1.02,
                'low': price * 0.98,
                'close': price,
                'vol': volume,
            })
    
    return pd.DataFrame(data)


@pytest.fixture
def mock_enriched_data():
    """Mock增强后的数据（包含因子计算结果）"""
    trade_date = datetime.now().strftime('%Y%m%d')
    
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH', '000858.SZ'],
        'name': ['平安银行', '万科A', '浦发银行', '五粮液'],
        'trade_date': [trade_date] * 4,
        'close': [10.5, 15.8, 8.7, 120.5],
        'pct_chg': [2.5, 1.8, -0.5, 3.2],
        'rps_60': [92.5, 88.3, 75.2, 95.1],
        'vol_ratio_5': [2.1, 1.8, 1.2, 2.5],
        'pe_ttm': [8.5, 12.3, 6.2, 18.2],
        'is_undervalued': [True, True, True, False],
        'above_ma_20': [True, True, False, True],
        'ai_analysis': [
            '银行股估值合理，技术面强势',
            '地产股基本面改善，RPS较高',
            '银行股估值较低，但技术面偏弱',
            '白酒股估值偏高，但RPS很强'
        ],
    })


@pytest.fixture
def mock_scan_results():
    """Mock扫描结果数据"""
    return [
        {
            'id': '000001.SZ_0',
            'code': '000001.SZ',
            'name': '平安银行',
            'price': 10.5,
            'change_percent': 2.5,
            'rps': 92.5,
            'volume_ratio': 2.1,
            'ai_analysis': '银行股估值合理，技术面强势',
        },
        {
            'id': '000002.SZ_1',
            'code': '000002.SZ',
            'name': '万科A',
            'price': 15.8,
            'change_percent': 1.8,
            'rps': 88.3,
            'volume_ratio': 1.8,
            'ai_analysis': '地产股基本面改善，RPS较高',
        },
        {
            'id': '000858.SZ_3',
            'code': '000858.SZ',
            'name': '五粮液',
            'price': 120.5,
            'change_percent': 3.2,
            'rps': 95.1,
            'volume_ratio': 2.5,
            'ai_analysis': '白酒股估值偏高，但RPS很强',
        },
    ]


@pytest.fixture
def mock_filters_response():
    """Mock筛选条件响应"""
    return {
        'rps_threshold': {
            'default': 85,
            'min': 50,
            'max': 100,
            'step': 1
        },
        'volume_ratio_threshold': {
            'default': 1.5,
            'min': 0.0,
            'max': 10.0,
            'step': 0.1
        },
        'pe_max': {
            'default': 30,
            'min': 5,
            'max': 100,
            'step': 1
        }
    }


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
def mock_data_provider(mock_stock_basic_data, mock_history_data):
    """Mock DataProvider"""
    from src.data_provider import DataProvider
    from src.config_manager import ConfigManager
    
    mock_provider = MagicMock(spec=DataProvider)
    mock_provider._tushare_client = MagicMock()
    mock_provider._eastmoney_client = MagicMock()
    mock_provider._cache_manager = MagicMock()
    
    # Mock get_daily_basic方法 - 根据传入的trade_date更新数据
    def mock_get_daily_basic(trade_date, index_code=None):
        # 复制基础数据并更新trade_date
        result = mock_stock_basic_data.copy()
        result['trade_date'] = trade_date
        return result
    
    mock_provider.get_daily_basic = MagicMock(side_effect=mock_get_daily_basic)
    
    # Mock get_daily_history方法
    def mock_get_daily_history(ts_codes, start_date, end_date):
        # 返回指定股票的历史数据
        if isinstance(ts_codes, str):
            ts_codes = [ts_codes]
        return mock_history_data[mock_history_data['ts_code'].isin(ts_codes)].copy()
    
    mock_provider.get_daily_history = MagicMock(side_effect=mock_get_daily_history)
    
    # Mock fetch_history_for_hunter方法（HunterService使用）
    def mock_fetch_history_for_hunter(trade_date, start_date, index_code=None, use_cache=True):
        # 返回历史数据，过滤日期范围，并确保包含trade_date当天的数据
        filtered = mock_history_data[
            (mock_history_data['trade_date'] >= start_date) &
            (mock_history_data['trade_date'] <= trade_date)
        ].copy()
        
        # 如果过滤后的数据中没有trade_date当天的数据，添加它
        if not filtered.empty and trade_date not in filtered['trade_date'].values:
            # 获取最后一条数据作为模板
            last_row = filtered.iloc[-1].copy()
            last_row['trade_date'] = trade_date
            # 为所有股票添加trade_date当天的数据
            stocks = filtered['ts_code'].unique()
            new_rows = []
            for stock in stocks:
                stock_data = filtered[filtered['ts_code'] == stock].iloc[-1].copy()
                stock_data['trade_date'] = trade_date
                new_rows.append(stock_data)
            if new_rows:
                filtered = pd.concat([filtered, pd.DataFrame(new_rows)], ignore_index=True)
        
        return filtered
    
    mock_provider.fetch_history_for_hunter = MagicMock(side_effect=mock_fetch_history_for_hunter)
    
    return mock_provider


@pytest.fixture
def mock_config():
    """Mock ConfigManager"""
    from src.config_manager import ConfigManager
    from unittest.mock import Mock
    
    config = MagicMock(spec=ConfigManager)
    config.get = Mock(side_effect=lambda key, default=None: {
        'hunter.history_days': 120,
        'strategy.alpha_trident.rps_threshold': 85,
        'strategy.alpha_trident.vol_ratio_threshold': 1.5,
        'strategy.alpha_trident.pe_max': 30,
        'portfolio.default_shares': 100,
        'portfolio.default_stop_loss_ratio': 0.9,
    }.get(key, default))
    
    # 添加config属性用于临时修改
    config.config = {
        'strategy': {
            'alpha_trident': {
                'rps_threshold': 85,
                'vol_ratio_threshold': 1.5,
                'pe_max': 30,
            }
        }
    }
    
    return config


@pytest.fixture
def expected_filters_schema():
    """预期的Filters响应schema"""
    return {
        'rps_threshold': {
            'default': (int, float),
            'min': (int, float),
            'max': (int, float),
            'step': (int, float),
        },
        'volume_ratio_threshold': {
            'default': (int, float),
            'min': (int, float),
            'max': (int, float),
            'step': (int, float),
        },
        'pe_max': {
            'default': (int, float),
            'min': (int, float),
            'max': (int, float),
            'step': (int, float),
        },
    }


@pytest.fixture
def expected_scan_response_schema():
    """预期的Scan响应schema"""
    return {
        'success': bool,
        'trade_date': (str, type(None)),
        'results': list,
        'diagnostics': (dict, type(None)),
        'error': (str, type(None)),
    }


@pytest.fixture
def expected_stock_result_schema():
    """预期的股票结果schema"""
    return {
        'id': str,
        'code': str,
        'name': str,
        'price': (int, float),
        'change_percent': (int, float),
        'rps': (int, float),
        'volume_ratio': (int, float),
        'ai_analysis': (str, type(None)),
    }
