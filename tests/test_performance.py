"""
性能测试
"""

import pytest
import time
import pandas as pd
from datetime import datetime, timedelta
from src.strategy import StockStrategy


def test_large_stock_pool_performance():
    """测试大规模股票池的性能"""
    # 创建大量测试数据
    today = datetime.now()
    old_date = (today - timedelta(days=400)).strftime('%Y%m%d')
    
    large_pool = pd.DataFrame({
        'ts_code': [f'{i:06d}.SZ' for i in range(1000)],
        'name': [f'股票{i}' for i in range(1000)],
        'industry': ['测试'] * 1000,
        'list_date': [old_date] * 1000,
        'is_st': [False] * 1000,
        'is_hs': ['N'] * 1000
    })
    
    # 创建对应的指标数据
    daily_indicators = pd.DataFrame({
        'ts_code': large_pool['ts_code'],
        'pe_ttm': [10.0 + (i % 20) for i in range(1000)],
        'pb': [1.0 + (i % 3) for i in range(1000)],
        'dividend_yield': [2.0 + (i % 2) for i in range(1000)],
        'total_market_cap': [1000000] * 1000
    })
    
    financial_indicators = pd.DataFrame({
        'ts_code': large_pool['ts_code'],
        'roe': [10.0 + (i % 10) for i in range(1000)]
    })
    
    # 测试策略筛选性能
    strategy = StockStrategy()
    
    start_time = time.time()
    result = strategy.filter_stocks(large_pool, daily_indicators, financial_indicators)
    end_time = time.time()
    
    # 性能指标
    duration = end_time - start_time
    assert duration < 5.0, f"筛选1000只股票耗时过长: {duration}秒"
    
    print(f"性能测试通过，耗时: {duration:.2f}秒")


def test_merge_performance():
    """测试数据合并性能"""
    # 创建测试数据
    n_stocks = 5000
    
    stock_basics = pd.DataFrame({
        'ts_code': [f'{i:06d}.SZ' for i in range(n_stocks)],
        'name': [f'股票{i}' for i in range(n_stocks)],
        'industry': ['测试'] * n_stocks,
        'list_date': ['20200101'] * n_stocks,
        'is_st': [False] * n_stocks
    })
    
    daily_indicators = pd.DataFrame({
        'ts_code': stock_basics['ts_code'],
        'pe_ttm': [10.0] * n_stocks,
        'pb': [1.0] * n_stocks,
        'dividend_yield': [2.0] * n_stocks,
        'total_market_cap': [1000000] * n_stocks
    })
    
    financial_indicators = pd.DataFrame({
        'ts_code': stock_basics['ts_code'],
        'roe': [10.0] * n_stocks
    })
    
    start_time = time.time()
    merged = stock_basics.merge(daily_indicators, on='ts_code', how='inner')
    merged = merged.merge(financial_indicators, on='ts_code', how='left')
    end_time = time.time()
    
    duration = end_time - start_time
    assert duration < 1.0, f"合并5000条数据耗时过长: {duration}秒"
    
    print(f"数据合并性能测试通过，耗时: {duration:.3f}秒")
