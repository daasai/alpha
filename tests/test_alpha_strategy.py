"""
Unit tests for AlphaStrategy
Tests for Alpha Trident strategy filtering logic
"""

import pytest
import pandas as pd
import numpy as np
from src.strategy import AlphaStrategy


class TestAlphaStrategyInit:
    """Test AlphaStrategy initialization"""
    
    def test_init_with_enriched_df(self):
        """Test initialization with enriched DataFrame"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['测试股票'],
            'rps_60': [90.0],
            'is_undervalued': [1],
            'vol_ratio_5': [2.0],
            'above_ma_20': [1]
        })
        
        strategy = AlphaStrategy(df)
        assert len(strategy.enriched_df) == 1
        assert 'ts_code' in strategy.enriched_df.columns
    
    def test_init_with_empty_df(self):
        """Test initialization with empty DataFrame"""
        strategy = AlphaStrategy(pd.DataFrame())
        assert strategy.enriched_df.empty
    
    def test_init_copies_dataframe(self):
        """Test that initialization creates a copy"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'rps_60': [90.0],
            'is_undervalued': [1],
            'vol_ratio_5': [2.0],
            'above_ma_20': [1]
        })
        
        strategy = AlphaStrategy(df)
        # Modify original DataFrame
        df.loc[0, 'rps_60'] = 50.0
        
        # Strategy's DataFrame should not be affected
        assert strategy.enriched_df.loc[0, 'rps_60'] == 90.0


class TestFilterAlphaTrident:
    """Test filter_alpha_trident method"""
    
    @pytest.fixture
    def sample_enriched_df(self):
        """Create sample enriched DataFrame with all factors"""
        return pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ'],
            'name': ['股票1', '股票2', '股票3', '股票4', '股票5'],
            'close': [10.0, 20.0, 30.0, 40.0, 50.0],
            'pe_ttm': [15.0, 25.0, 35.0, 10.0, 20.0],
            'rps_60': [90.0, 95.0, 80.0, 88.0, 92.0],  # 000003.SZ fails momentum
            'is_undervalued': [1, 1, 0, 1, 1],  # 000003.SZ fails value
            'vol_ratio_5': [2.0, 1.8, 2.2, 1.4, 1.6],  # 000004.SZ fails liquidity
            'above_ma_20': [1, 1, 1, 1, 0]  # 000005.SZ fails trend
        })
    
    def test_filter_all_conditions_met(self, sample_enriched_df):
        """Test filtering when all conditions are met"""
        strategy = AlphaStrategy(sample_enriched_df)
        result = strategy.filter_alpha_trident()
        
        # Only 000001.SZ and 000002.SZ should pass all filters
        assert len(result) == 2
        assert set(result['ts_code'].values) == {'000001.SZ', '000002.SZ'}
    
    def test_filter_momentum_condition(self, sample_enriched_df):
        """Test momentum filter (rps_60 > 85)"""
        # Modify to have only one stock with rps_60 > 85
        df = sample_enriched_df.copy()
        df.loc[df['ts_code'] == '000001.SZ', 'rps_60'] = 90.0
        df.loc[df['ts_code'] == '000002.SZ', 'rps_60'] = 80.0  # Fails momentum
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        # Should filter out 000002.SZ due to momentum
        assert len(result) == 1
        assert result['ts_code'].iloc[0] == '000001.SZ'
    
    def test_filter_value_condition(self, sample_enriched_df):
        """Test value filter (is_undervalued == 1)"""
        df = sample_enriched_df.copy()
        # Set all to pass momentum, but one fails value
        df['rps_60'] = 90.0
        df.loc[df['ts_code'] == '000002.SZ', 'is_undervalued'] = 0
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        # Should filter out 000002.SZ due to value
        assert len(result) == 1
        assert result['ts_code'].iloc[0] == '000001.SZ'
    
    def test_filter_liquidity_condition(self, sample_enriched_df):
        """Test liquidity filter (vol_ratio_5 > 1.5)"""
        df = sample_enriched_df.copy()
        # Set all to pass momentum, value, and trend, but one fails liquidity
        # Only keep 2 stocks for this test
        df = df[df['ts_code'].isin(['000001.SZ', '000002.SZ'])].copy()
        df['rps_60'] = 90.0
        df['is_undervalued'] = 1
        df['above_ma_20'] = 1
        df.loc[df['ts_code'] == '000002.SZ', 'vol_ratio_5'] = 1.4  # Fails liquidity
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        # Should filter out 000002.SZ due to liquidity
        assert len(result) == 1
        assert result['ts_code'].iloc[0] == '000001.SZ'
    
    def test_filter_trend_condition(self, sample_enriched_df):
        """Test trend filter (above_ma_20 == 1)"""
        df = sample_enriched_df.copy()
        # Set all to pass momentum, value, liquidity, but one fails trend
        # Only keep 2 stocks for this test
        df = df[df['ts_code'].isin(['000001.SZ', '000002.SZ'])].copy()
        df['rps_60'] = 90.0
        df['is_undervalued'] = 1
        df['vol_ratio_5'] = 2.0
        df.loc[df['ts_code'] == '000002.SZ', 'above_ma_20'] = 0  # Fails trend
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        # Should filter out 000002.SZ due to trend
        # Only stocks with above_ma_20 == 1 should pass
        assert len(result) == 1
        assert result['ts_code'].iloc[0] == '000001.SZ'
    
    def test_filter_sorting(self, sample_enriched_df):
        """Test that results are sorted by rps_60 descending"""
        df = sample_enriched_df.copy()
        # Ensure all pass filters
        df['rps_60'] = [92.0, 90.0, 95.0, 88.0, 91.0]  # Different RPS values
        df['is_undervalued'] = 1
        df['vol_ratio_5'] = 2.0
        df['above_ma_20'] = 1
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        # Should be sorted by rps_60 descending
        assert len(result) == 5
        rps_values = result['rps_60'].values
        assert all(rps_values[i] >= rps_values[i+1] for i in range(len(rps_values)-1))
        assert result['rps_60'].iloc[0] == 95.0  # Highest RPS first
    
    def test_filter_output_columns(self, sample_enriched_df):
        """Test that output contains required columns"""
        df = sample_enriched_df.copy()
        df['rps_60'] = 90.0
        df['is_undervalued'] = 1
        df['vol_ratio_5'] = 2.0
        df['above_ma_20'] = 1
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        required_columns = ['ts_code', 'name', 'close', 'pe_ttm', 'rps_60', 'vol_ratio_5', 'strategy_tag']
        assert all(col in result.columns for col in required_columns)
    
    def test_filter_strategy_tag(self, sample_enriched_df):
        """Test that strategy_tag is set correctly"""
        df = sample_enriched_df.copy()
        df['rps_60'] = 90.0
        df['is_undervalued'] = 1
        df['vol_ratio_5'] = 2.0
        df['above_ma_20'] = 1
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        assert (result['strategy_tag'] == '🚀 强推荐').all()
    
    def test_filter_empty_result(self):
        """Test filtering when no stocks meet all conditions"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['股票1'],
            'rps_60': [80.0],  # Fails momentum
            'is_undervalued': [1],
            'vol_ratio_5': [2.0],
            'above_ma_20': [1]
        })
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        assert result.empty
    
    def test_filter_empty_input(self):
        """Test filtering with empty enriched DataFrame"""
        strategy = AlphaStrategy(pd.DataFrame())
        result = strategy.filter_alpha_trident()
        
        assert result.empty
    
    def test_filter_missing_required_columns(self):
        """Test filtering with missing required columns"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['股票1']
            # Missing required factor columns
        })
        
        strategy = AlphaStrategy(df)
        
        with pytest.raises(ValueError, match="缺少必需的因子列"):
            strategy.filter_alpha_trident()
    
    def test_filter_partial_missing_columns(self):
        """Test filtering with some missing output columns"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'rps_60': [90.0],
            'is_undervalued': [1],
            'vol_ratio_5': [2.0],
            'above_ma_20': [1],
            'close': [10.0],
            'pe_ttm': [15.0]
            # Missing 'name' column
        })
        
        strategy = AlphaStrategy(df)
        result = strategy.filter_alpha_trident()
        
        # Should still work, but 'name' won't be in output
        assert len(result) == 1
        assert 'ts_code' in result.columns
        # 'name' should be missing from output
        assert 'name' not in result.columns
    
    def test_filter_boundary_values(self):
        """Test filtering with boundary values"""
        # Test rps_60 exactly 85 (should fail)
        df1 = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['股票1'],
            'rps_60': [85.0],  # Exactly 85, should fail (> 85)
            'is_undervalued': [1],
            'vol_ratio_5': [2.0],
            'above_ma_20': [1],
            'close': [10.0],
            'pe_ttm': [15.0]
        })
        
        strategy1 = AlphaStrategy(df1)
        result1 = strategy1.filter_alpha_trident()
        assert result1.empty
        
        # Test rps_60 = 85.01 (should pass)
        df2 = df1.copy()
        df2.loc[0, 'rps_60'] = 85.01
        
        strategy2 = AlphaStrategy(df2)
        result2 = strategy2.filter_alpha_trident()
        assert len(result2) == 1
        
        # Test vol_ratio_5 exactly 1.5 (should fail)
        df3 = df2.copy()
        df3.loc[0, 'vol_ratio_5'] = 1.5  # Exactly 1.5, should fail (> 1.5)
        
        strategy3 = AlphaStrategy(df3)
        result3 = strategy3.filter_alpha_trident()
        assert result3.empty
        
        # Test vol_ratio_5 = 1.51 (should pass)
        df4 = df3.copy()
        df4.loc[0, 'vol_ratio_5'] = 1.51
        
        strategy4 = AlphaStrategy(df4)
        result4 = strategy4.filter_alpha_trident()
        assert len(result4) == 1
