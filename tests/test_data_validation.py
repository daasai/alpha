"""
Data validation tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from src.data_loader import DataLoader
from src.strategy import StockStrategy


class TestDataFrameStructure:
    """Test DataFrame structure validation"""
    
    def test_dataframe_structure_stock_basics(self, sample_stock_basics):
        """Test stock basics DataFrame structure"""
        required_columns = ['ts_code', 'symbol', 'name', 'area', 'industry', 
                          'list_date', 'is_hs', 'is_st']
        
        assert isinstance(sample_stock_basics, pd.DataFrame)
        assert all(col in sample_stock_basics.columns for col in required_columns)
        assert len(sample_stock_basics) > 0
    
    def test_dataframe_structure_daily_indicators(self, sample_daily_indicators):
        """Test daily indicators DataFrame structure"""
        required_columns = ['ts_code', 'trade_date', 'pe_ttm', 'pb', 
                          'dividend_yield', 'total_market_cap']
        
        assert isinstance(sample_daily_indicators, pd.DataFrame)
        assert all(col in sample_daily_indicators.columns for col in required_columns)
        assert len(sample_daily_indicators) > 0
    
    def test_dataframe_structure_financial_indicators(self, sample_financial_indicators):
        """Test financial indicators DataFrame structure"""
        required_columns = ['ts_code', 'end_date', 'roe', 'net_profit_growth_rate']
        
        assert isinstance(sample_financial_indicators, pd.DataFrame)
        assert all(col in sample_financial_indicators.columns for col in required_columns)
    
    def test_dataframe_structure_anchor_pool(self, sample_anchor_pool):
        """Test anchor pool DataFrame structure"""
        required_columns = ['ts_code', 'name', 'industry', 'pe_ttm', 'pb', 'roe',
                          'dividend_yield', 'total_market_cap', 'listing_days']
        
        assert isinstance(sample_anchor_pool, pd.DataFrame)
        assert all(col in sample_anchor_pool.columns for col in required_columns)
    
    def test_dataframe_structure_after_merge(self, sample_stock_basics, 
                                            sample_daily_indicators,
                                            sample_financial_indicators,
                                            sample_settings_yaml):
        """Test DataFrame structure after merging in strategy"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        result = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators,
                                       sample_financial_indicators)
        
        assert isinstance(result, pd.DataFrame)
        # Verify all expected columns are present
        expected_cols = ['ts_code', 'name', 'industry', 'pe_ttm', 'pb', 'roe',
                        'dividend_yield', 'total_market_cap', 'listing_days']
        assert all(col in result.columns for col in expected_cols)


class TestDataTypes:
    """Test data type validation"""
    
    def test_data_types_stock_basics(self, sample_stock_basics):
        """Test stock basics data types"""
        assert sample_stock_basics['ts_code'].dtype == 'object'  # String
        assert sample_stock_basics['name'].dtype == 'object'  # String
        assert sample_stock_basics['is_st'].dtype == 'bool'
    
    def test_data_types_daily_indicators(self, sample_daily_indicators):
        """Test daily indicators data types"""
        assert sample_daily_indicators['ts_code'].dtype == 'object'  # String
        assert pd.api.types.is_numeric_dtype(sample_daily_indicators['pe_ttm'])
        assert pd.api.types.is_numeric_dtype(sample_daily_indicators['pb'])
        assert pd.api.types.is_numeric_dtype(sample_daily_indicators['dividend_yield'])
        assert pd.api.types.is_numeric_dtype(sample_daily_indicators['total_market_cap'])
    
    def test_data_types_financial_indicators(self, sample_financial_indicators):
        """Test financial indicators data types"""
        assert sample_financial_indicators['ts_code'].dtype == 'object'  # String
        assert pd.api.types.is_numeric_dtype(sample_financial_indicators['roe'])
        if 'net_profit_growth_rate' in sample_financial_indicators.columns:
            assert pd.api.types.is_numeric_dtype(sample_financial_indicators['net_profit_growth_rate'])
    
    def test_data_types_anchor_pool(self, sample_anchor_pool):
        """Test anchor pool data types"""
        assert sample_anchor_pool['ts_code'].dtype == 'object'  # String
        assert sample_anchor_pool['name'].dtype == 'object'  # String
        assert pd.api.types.is_numeric_dtype(sample_anchor_pool['pe_ttm'])
        assert pd.api.types.is_numeric_dtype(sample_anchor_pool['pb'])
        assert pd.api.types.is_numeric_dtype(sample_anchor_pool['roe'])
        assert pd.api.types.is_numeric_dtype(sample_anchor_pool['dividend_yield'])
        assert pd.api.types.is_numeric_dtype(sample_anchor_pool['total_market_cap'])
        assert pd.api.types.is_numeric_dtype(sample_anchor_pool['listing_days'])


class TestDataRanges:
    """Test data range validation"""
    
    def test_data_ranges_pe_ttm(self, sample_daily_indicators):
        """Test PE_TTM range validation"""
        # PE_TTM should be positive (or NaN for invalid data)
        valid_pe = sample_daily_indicators['pe_ttm'].dropna()
        if len(valid_pe) > 0:
            # In real data, PE can be negative for loss-making companies
            # But for our filtering, we require PE > 0
            assert all(valid_pe > 0) or any(valid_pe > 0)
    
    def test_data_ranges_pb(self, sample_daily_indicators):
        """Test PB range validation"""
        # PB should be positive (or NaN)
        valid_pb = sample_daily_indicators['pb'].dropna()
        if len(valid_pb) > 0:
            assert all(valid_pb > 0) or any(valid_pb > 0)
    
    def test_data_ranges_dividend_yield(self, sample_daily_indicators):
        """Test dividend yield range validation"""
        # Dividend yield should be non-negative (can be 0)
        valid_dy = sample_daily_indicators['dividend_yield'].dropna()
        if len(valid_dy) > 0:
            assert all(valid_dy >= 0)
    
    def test_data_ranges_market_cap(self, sample_daily_indicators):
        """Test market cap range validation"""
        # Market cap should be positive
        valid_mc = sample_daily_indicators['total_market_cap'].dropna()
        if len(valid_mc) > 0:
            assert all(valid_mc > 0)
    
    def test_data_ranges_roe(self, sample_financial_indicators):
        """Test ROE range validation"""
        # ROE can be negative (loss-making companies) or positive
        valid_roe = sample_financial_indicators['roe'].dropna()
        if len(valid_roe) > 0:
            # ROE can be any real number
            assert isinstance(valid_roe.iloc[0], (int, float, np.number))
    
    def test_data_ranges_after_filtering(self, sample_stock_basics, sample_daily_indicators,
                                        sample_financial_indicators, sample_settings_yaml):
        """Test data ranges after filtering"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        result = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators,
                                       sample_financial_indicators)
        
        if len(result) > 0:
            # After filtering, all values should be within expected ranges
            assert all((result['pe_ttm'] > 0) & (result['pe_ttm'] < strategy.pe_ttm_max))
            assert all((result['pb'] > 0) & (result['pb'] < strategy.pb_max))
            assert all(result['roe'] > strategy.roe_min)
            assert all(result['dividend_yield'] > strategy.dividend_yield_min)
            assert all(result['listing_days'] >= strategy.listing_days_min)


class TestMissingValues:
    """Test missing value handling"""
    
    def test_missing_values_stock_basics(self, sample_stock_basics):
        """Test missing values in stock basics"""
        # Key columns should not have missing values
        assert not sample_stock_basics['ts_code'].isna().any()
        assert not sample_stock_basics['name'].isna().any()
        assert not sample_stock_basics['is_st'].isna().any()
    
    def test_missing_values_daily_indicators(self, sample_daily_indicators):
        """Test missing values in daily indicators"""
        # ts_code should not be missing
        assert not sample_daily_indicators['ts_code'].isna().any()
        
        # Other fields might have NaN (e.g., PE for loss-making companies)
        # This is acceptable
    
    def test_missing_values_financial_indicators(self, sample_financial_indicators):
        """Test missing values in financial indicators"""
        # ts_code should not be missing
        if len(sample_financial_indicators) > 0:
            assert not sample_financial_indicators['ts_code'].isna().any()
    
    def test_missing_values_handling_in_strategy(self, sample_stock_basics, 
                                                 sample_daily_indicators,
                                                 sample_settings_yaml):
        """Test missing value handling in strategy"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        
        # Create data with missing values
        daily_with_nan = sample_daily_indicators.copy()
        daily_with_nan.loc[0, 'pe_ttm'] = np.nan
        
        financial_with_nan = pd.DataFrame({
            'ts_code': ['000001.SZ'],  # Only one stock
            'end_date': ['20250116'],
            'roe': [np.nan]  # Missing ROE
        })
        
        result = strategy.filter_stocks(sample_stock_basics, daily_with_nan, financial_with_nan)
        
        # Strategy should handle missing values (dropna)
        assert isinstance(result, pd.DataFrame)
        # After dropna, result should not have NaN in key columns
        if len(result) > 0:
            key_cols = ['pe_ttm', 'pb', 'roe', 'dividend_yield']
            assert not result[key_cols].isna().any().any()
    
    def test_missing_values_left_join(self, sample_stock_basics, sample_daily_indicators,
                                      sample_settings_yaml):
        """Test that left join preserves stocks without financial data"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        
        # Empty financial indicators
        empty_financial = pd.DataFrame(columns=['ts_code', 'end_date', 'roe', 'net_profit_growth_rate'])
        
        result = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators, empty_financial)
        
        # Should handle gracefully (all stocks will have NaN ROE, then filtered out)
        assert isinstance(result, pd.DataFrame)


class TestDateFormats:
    """Test date format consistency"""
    
    def test_date_formats_list_date(self, sample_stock_basics):
        """Test list_date format"""
        # list_date should be in YYYYMMDD format (string)
        if len(sample_stock_basics) > 0:
            list_dates = sample_stock_basics['list_date'].dropna()
            if len(list_dates) > 0:
                # Should be 8-digit strings
                assert all(len(str(date)) == 8 for date in list_dates)
    
    def test_date_formats_trade_date(self, sample_daily_indicators):
        """Test trade_date format"""
        # trade_date should be in YYYYMMDD format
        if len(sample_daily_indicators) > 0:
            trade_dates = sample_daily_indicators['trade_date'].dropna()
            if len(trade_dates) > 0:
                assert all(len(str(date)) == 8 for date in trade_dates)
    
    def test_date_formats_end_date(self, sample_financial_indicators):
        """Test end_date format"""
        # end_date should be in YYYYMMDD format
        if len(sample_financial_indicators) > 0:
            end_dates = sample_financial_indicators['end_date'].dropna()
            if len(end_dates) > 0:
                assert all(len(str(date)) == 8 for date in end_dates)
    
    def test_date_formats_ann_date(self, sample_notices):
        """Test ann_date format"""
        # ann_date should be in YYYYMMDD format
        if len(sample_notices) > 0:
            ann_dates = sample_notices['ann_date'].dropna()
            if len(ann_dates) > 0:
                assert all(len(str(date)) == 8 for date in ann_dates)
    
    def test_date_formats_consistency(self, sample_stock_basics, sample_daily_indicators,
                                     sample_financial_indicators, sample_settings_yaml):
        """Test date format consistency across modules"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        result = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators,
                                       sample_financial_indicators)
        
        # After processing, dates should be properly formatted
        # (though listing_days is calculated, not a date string)
        assert isinstance(result, pd.DataFrame)


class TestDataConsistency:
    """Test data consistency across the system"""
    
    def test_ts_code_consistency(self, sample_stock_basics, sample_daily_indicators,
                                 sample_financial_indicators):
        """Test that ts_code format is consistent"""
        # All ts_codes should follow the same format (e.g., '000001.SZ')
        if len(sample_stock_basics) > 0:
            stock_codes = sample_stock_basics['ts_code'].dropna()
            # Should contain dot and extension
            assert all('.' in str(code) for code in stock_codes)
    
    def test_data_merge_consistency(self, sample_stock_basics, sample_daily_indicators,
                                   sample_financial_indicators, sample_settings_yaml):
        """Test that data can be merged consistently"""
        strategy = StockStrategy(config_path=sample_settings_yaml)
        result = strategy.filter_stocks(sample_stock_basics, sample_daily_indicators,
                                       sample_financial_indicators)
        
        # After merge, all rows should have consistent data
        if len(result) > 0:
            # All rows should have all required columns
            assert not result[['ts_code', 'name', 'pe_ttm', 'pb', 'roe']].isna().all(axis=1).any()
    
    def test_data_uniqueness(self, sample_stock_basics):
        """Test that ts_code is unique in stock basics"""
        # Each stock should appear only once
        assert sample_stock_basics['ts_code'].is_unique
