"""
Pytest configuration and shared fixtures
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
import os
from pathlib import Path


@pytest.fixture
def mock_tushare_pro():
    """Mock Tushare Pro API"""
    mock_pro = MagicMock()
    return mock_pro


@pytest.fixture
def sample_stock_basics():
    """Sample stock basics DataFrame"""
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH', '600001.SH', 'ST0001.SZ'],
        'symbol': ['000001', '000002', '600000', '600001', '000001'],
        'name': ['平安银行', '万科A', '浦发银行', '邯郸钢铁', 'ST测试'],
        'area': ['深圳', '深圳', '上海', '河北', '深圳'],
        'industry': ['银行', '房地产', '银行', '钢铁', '其他'],
        'list_date': ['19910403', '19910129', '19991110', '19980101', '20200101'],
        'is_hs': ['N', 'Y', 'Y', 'N', 'N'],
        'is_st': [False, False, False, False, True]
    })


@pytest.fixture
def sample_daily_indicators():
    """Sample daily indicators DataFrame"""
    trade_date = datetime.now().strftime('%Y%m%d')
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH', '600001.SH'],
        'trade_date': [trade_date] * 4,
        'pe_ttm': [8.5, 12.3, 6.2, 25.5],
        'pb': [0.8, 1.2, 0.6, 4.5],
        'dividend_yield': [2.5, 3.2, 1.8, 0.5],
        'total_market_cap': [1500000, 2000000, 1200000, 800000]  # 万元
    })


@pytest.fixture
def sample_financial_indicators():
    """Sample financial indicators DataFrame"""
    end_date = datetime.now().strftime('%Y%m%d')
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH', '600001.SH'],
        'end_date': [end_date] * 4,
        'roe': [12.5, 15.8, 10.2, 5.5],
        'net_profit_growth_rate': [8.5, 12.3, 6.2, -2.1]
    })


@pytest.fixture
def sample_notices():
    """Sample notices DataFrame"""
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime('%Y%m%d') for i in range(5)]
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '000001.SZ', '600000.SH', '600001.SH'],
        'ann_date': dates,
        'title': [
            '关于公司增持股份的公告',
            '关于公司回购股份的公告',
            '关于公司预增业绩的公告',
            '关于公司减持股份的公告',
            '关于公司收到立案调查通知的公告'
        ]
    })


@pytest.fixture
def sample_anchor_pool():
    """Sample anchor pool DataFrame after filtering"""
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH'],
        'name': ['平安银行', '万科A', '浦发银行'],
        'industry': ['银行', '房地产', '银行'],
        'pe_ttm': [8.5, 12.3, 6.2],
        'pb': [0.8, 1.2, 0.6],
        'roe': [12.5, 15.8, 10.2],
        'dividend_yield': [2.5, 3.2, 1.8],
        'total_market_cap': [1500000, 2000000, 1200000],
        'listing_days': [12000, 12500, 9000]
    })


@pytest.fixture
def sample_notice_results():
    """Sample notice analysis results"""
    today = datetime.now()
    return [
        {
            'ts_code': '000001.SZ',
            'notice_date': today.strftime('%Y-%m-%d'),
            'title': '关于公司增持股份的公告',
            'matched_keyword': '增持',
            'sentiment': 'Positive'
        },
        {
            'ts_code': '000002.SZ',
            'notice_date': (today - timedelta(days=1)).strftime('%Y-%m-%d'),
            'title': '关于公司回购股份的公告',
            'matched_keyword': '回购',
            'sentiment': 'Positive'
        },
        {
            'ts_code': '600001.SH',
            'notice_date': (today - timedelta(days=2)).strftime('%Y-%m-%d'),
            'title': '关于公司收到立案调查通知的公告',
            'matched_keyword': '立案',
            'sentiment': 'Negative'
        }
    ]


@pytest.fixture
def temp_config_dir(tmp_path):
    """Temporary directory for test config files"""
    config_dir = tmp_path / 'config'
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test output files"""
    output_dir = tmp_path / 'output'
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_settings_yaml(temp_config_dir):
    """Create sample settings.yaml file"""
    settings_file = temp_config_dir / 'settings.yaml'
    settings_file.write_text("""# Stock Screening Strategy Parameters

# Valuation Filters (Value)
pe_ttm_max: 30  # Maximum PE_TTM ratio
pb_max: 5       # Maximum PB ratio

# Quality Filters
roe_min: 8      # Minimum ROE (percentage)

# Yield Filters
dividend_yield_min: 1.5  # Minimum dividend yield (percentage)

# Exclusion Rules
listing_days_min: 365  # Minimum days since listing (exclude new stocks)
""", encoding='utf-8')
    return str(settings_file)


@pytest.fixture
def sample_keywords_yaml(temp_config_dir):
    """Create sample keywords.yaml file"""
    keywords_file = temp_config_dir / 'keywords.yaml'
    keywords_file.write_text("""# Announcement Monitoring Keywords

# Positive keywords (利好)
positive:
  - "增持"
  - "回购"
  - "预增"
  - "中标"
  - "分红"
  - "股权激励"

# Negative keywords (利空/警示)
negative:
  - "减持"
  - "立案"
  - "调查"
  - "亏损"
  - "违规"
  - "警示函"
""", encoding='utf-8')
    return str(keywords_file)


@pytest.fixture
def mock_env_file(tmp_path, monkeypatch):
    """Create mock .env file and set environment variable"""
    env_file = tmp_path / '.env'
    env_file.write_text('TUSHARE_TOKEN=test_token_12345\n', encoding='utf-8')
    
    # Set environment variable
    monkeypatch.setenv('TUSHARE_TOKEN', 'test_token_12345')
    
    # Change to temp directory so load_dotenv finds the .env file
    original_cwd = os.getcwd()
    monkeypatch.chdir(tmp_path)
    
    yield env_file
    
    # Restore original directory
    monkeypatch.chdir(original_cwd)


@pytest.fixture
def trade_date():
    """Sample trade date"""
    # Use a weekday date
    date = datetime.now()
    while date.weekday() >= 5:  # Skip weekends
        date -= timedelta(days=1)
    return date.strftime('%Y%m%d')
