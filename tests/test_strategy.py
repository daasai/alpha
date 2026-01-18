"""
Tests for Strategy module
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from src.strategy import StockStrategy


class TestStockStrategyInit:
    """Test StockStrategy initialization"""
    
    def test_init_load_config(self, sample_settings_yaml):
        """Test configuration loading"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        
        assert strategy.pe_ttm_max == 30
        assert strategy.pb_max == 5
        assert strategy.roe_min == 8
        assert strategy.dividend_yield_min == 1.5
        assert strategy.listing_days_min == 365
    
    def test_init_missing_config(self, tmp_path):
        """Test initialization with missing config file"""
        missing_config = tmp_path / 'missing.yaml'
        
        with pytest.raises(FileNotFoundError):
            StockStrategy(config_path=str(missing_config))


class TestFilterStocks:
    """Test filter_stocks method"""
    
    @pytest.fixture
    def strategy(self, sample_settings_yaml):
        """Create StockStrategy instance"""
        return StockStrategy(config_path=sample_settings_yaml)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for filtering"""
        today = datetime.now()
        old_date = (today - timedelta(days=400)).strftime('%Y%m%d')
        new_date = (today - timedelta(days=100)).strftime('%Y%m%d')
        
        stock_basics = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', 'ST0001.SZ', '600000.SH', '600001.SH'],
            'name': ['平安银行', '万科A', 'ST测试', '浦发银行', '新股票'],
            'industry': ['银行', '房地产', '其他', '银行', '科技'],
            'list_date': [old_date, old_date, old_date, old_date, new_date],
            'is_st': [False, False, True, False, False]
        })
        
        daily_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', 'ST0001.SZ', '600000.SH', '600001.SH'],
            'pe_ttm': [8.5, 12.3, 5.0, 6.2, 35.0],  # 600001.SH PE too high
            'pb': [0.8, 1.2, 0.5, 0.6, 6.0],  # 600001.SH PB too high
            'dividend_yield': [2.5, 3.2, 1.0, 1.8, 0.5],  # 600001.SH dividend too low
            'total_market_cap': [1500000, 2000000, 500000, 1200000, 800000]
        })
        
        financial_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', 'ST0001.SZ', '600000.SH', '600001.SH'],
            'roe': [12.5, 15.8, 5.0, 10.2, 6.0]  # 600001.SH ROE too low
        })
        
        return stock_basics, daily_indicators, financial_indicators
    
    def test_filter_stocks_basic(self, strategy, sample_data):
        """Test basic filtering functionality"""
        stock_basics, daily_indicators, financial_indicators = sample_data
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'ts_code' in result.columns
        assert 'name' in result.columns
        assert 'pe_ttm' in result.columns
        assert 'pb' in result.columns
        assert 'roe' in result.columns
        assert 'dividend_yield' in result.columns
    
    def test_filter_stocks_exclude_st(self, strategy, sample_data):
        """Test exclusion of ST stocks"""
        stock_basics, daily_indicators, financial_indicators = sample_data
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # ST股票应该被排除
        assert 'ST0001.SZ' not in result['ts_code'].values
    
    def test_filter_stocks_exclude_new_stocks(self, strategy, sample_data):
        """Test exclusion of new stocks (listing days < 365)"""
        stock_basics, daily_indicators, financial_indicators = sample_data
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # 新股应该被排除
        assert '600001.SH' not in result['ts_code'].values
    
    def test_filter_stocks_pe_pb_filter(self, strategy, sample_data):
        """Test PE and PB filtering"""
        stock_basics, daily_indicators, financial_indicators = sample_data
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # 所有股票的PE应该在范围内
        if len(result) > 0:
            assert all((result['pe_ttm'] > 0) & (result['pe_ttm'] < 30))
            assert all((result['pb'] > 0) & (result['pb'] < 5))
    
    def test_filter_stocks_roe_filter(self, strategy, sample_data):
        """Test ROE filtering"""
        stock_basics, daily_indicators, financial_indicators = sample_data
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # 所有股票的ROE应该大于阈值
        if len(result) > 0:
            assert all(result['roe'] > 8)
    
    def test_filter_stocks_dividend_filter(self, strategy, sample_data):
        """Test dividend yield filtering"""
        stock_basics, daily_indicators, financial_indicators = sample_data
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # 所有股票的股息率应该大于阈值
        if len(result) > 0:
            assert all(result['dividend_yield'] > 1.5)
    
    def test_filter_stocks_empty_result(self, strategy):
        """Test filtering with no matching stocks"""
        # Create data that won't match any criteria
        today = datetime.now()
        old_date = (today - timedelta(days=400)).strftime('%Y%m%d')
        
        stock_basics = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['测试股票'],
            'industry': ['其他'],
            'list_date': [old_date],
            'is_st': [False]
        })
        
        daily_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'pe_ttm': [50.0],  # Too high
            'pb': [10.0],  # Too high
            'dividend_yield': [0.1],  # Too low
            'total_market_cap': [1000000]
        })
        
        financial_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'roe': [2.0]  # Too low
        })
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_filter_stocks_missing_data(self, strategy):
        """Test handling of missing data"""
        today = datetime.now()
        old_date = (today - timedelta(days=400)).strftime('%Y%m%d')
        
        stock_basics = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'name': ['股票1', '股票2'],
            'industry': ['其他', '其他'],
            'list_date': [old_date, old_date],
            'is_st': [False, False]
        })
        
        daily_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'pe_ttm': [10.0, np.nan],  # Missing data
            'pb': [1.0, 1.0],
            'dividend_yield': [2.0, 2.0],
            'total_market_cap': [1000000, 1000000]
        })
        
        financial_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'roe': [10.0]
            # 000002.SZ missing financial data
        })
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # Should handle missing data gracefully
        assert isinstance(result, pd.DataFrame)
        # NaN values should be dropped
        if len(result) > 0:
            assert not result[['pe_ttm', 'pb', 'roe', 'dividend_yield']].isna().any().any()
    
    def test_filter_stocks_sorting(self, strategy, sample_data):
        """Test result sorting by ROE"""
        stock_basics, daily_indicators, financial_indicators = sample_data
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # Results should be sorted by ROE descending
        if len(result) > 1:
            roe_values = result['roe'].values
            assert all(roe_values[i] >= roe_values[i+1] for i in range(len(roe_values)-1))
    
    def test_filter_stocks_left_join_financial(self, strategy):
        """Test that financial indicators use left join (not all stocks have financial data)"""
        today = datetime.now()
        old_date = (today - timedelta(days=400)).strftime('%Y%m%d')
        
        stock_basics = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'name': ['股票1', '股票2'],
            'industry': ['其他', '其他'],
            'list_date': [old_date, old_date],
            'is_st': [False, False]
        })
        
        daily_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'pe_ttm': [10.0, 10.0],
            'pb': [1.0, 1.0],
            'dividend_yield': [2.0, 2.0],
            'total_market_cap': [1000000, 1000000]
        })
        
        # Only one stock has financial data
        financial_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'roe': [10.0]
        })
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # Should include both stocks initially, but filter out 000002.SZ due to missing ROE
        # After filtering by ROE > 8, only 000001.SZ should remain
        assert len(result) == 1
        assert result.iloc[0]['ts_code'] == '000001.SZ'
    
    def test_filter_stocks_boundary_values(self, strategy):
        """Test filtering with boundary values"""
        today = datetime.now()
        old_date = (today - timedelta(days=400)).strftime('%Y%m%d')
        
        stock_basics = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ'],
            'name': ['股票1', '股票2', '股票3'],
            'industry': ['其他', '其他', '其他'],
            'list_date': [old_date, old_date, old_date],
            'is_st': [False, False, False]
        })
        
        daily_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ'],
            'pe_ttm': [29.9, 30.1, 10.0],  # Boundary: 29.9 should pass, 30.1 should fail
            'pb': [4.9, 5.1, 2.0],  # Boundary: 4.9 should pass, 5.1 should fail
            'dividend_yield': [1.51, 1.49, 2.0],  # Boundary: 1.51 should pass, 1.49 should fail
            'total_market_cap': [1000000, 1000000, 1000000]
        })
        
        financial_indicators = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ'],
            'roe': [8.1, 7.9, 10.0]  # Boundary: 8.1 should pass, 7.9 should fail
        })
        
        result = strategy.filter_stocks(stock_basics, daily_indicators, financial_indicators)
        
        # Only 000001.SZ and 000003.SZ should pass all filters
        assert len(result) == 2
        assert '000001.SZ' in result['ts_code'].values
        assert '000003.SZ' in result['ts_code'].values
        assert '000002.SZ' not in result['ts_code'].values
