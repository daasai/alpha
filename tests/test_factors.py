"""
Unit tests for Factor Engine module
Tests for BaseFactor, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor, FactorPipeline
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from abc import ABC

from src.factors.base import BaseFactor
from src.factors.momentum import RPSFactor
from src.factors.technical import MAFactor, VolumeRatioFactor
from src.factors.fundamental import PEProxyFactor
from src.factors.engine import FactorPipeline


class TestBaseFactor:
    """Test BaseFactor abstract class"""
    
    def test_base_factor_is_abstract(self):
        """Test that BaseFactor is abstract and cannot be instantiated"""
        with pytest.raises(TypeError):
            BaseFactor()
    
    def test_base_factor_requires_compute(self):
        """Test that subclasses must implement compute() method"""
        class IncompleteFactor(BaseFactor):
            def name(self):
                return "test"
        
        with pytest.raises(TypeError):
            IncompleteFactor()
    
    def test_base_factor_requires_name(self):
        """Test that subclasses must implement name() method"""
        class IncompleteFactor(BaseFactor):
            def compute(self, df):
                return df
        
        with pytest.raises(TypeError):
            IncompleteFactor()


class TestRPSFactor:
    """Test RPSFactor"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for RPS calculation"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ']:
            for i, date in enumerate(dates[:60]):
                # Create price trend
                close = 10.0 + i * 0.1 + np.random.normal(0, 0.05)
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'close': close,
                    'vol': 1000000 + np.random.randint(-100000, 100000)
                })
        
        return pd.DataFrame(data)
    
    def test_rps_factor_initialization(self):
        """Test RPSFactor initialization"""
        factor = RPSFactor(window=60)
        assert factor.window == 60
        assert factor.name() == "rps_60"
    
    def test_rps_factor_name(self):
        """Test RPSFactor name method"""
        factor = RPSFactor(window=30)
        assert factor.name() == "rps_30"
    
    def test_rps_factor_compute_with_close(self, sample_data):
        """Test RPS calculation with close prices"""
        factor = RPSFactor(window=60)
        result = factor.compute(sample_data.copy())
        
        assert 'rps_60' in result.columns
        assert len(result) == len(sample_data)
        # RPS should be between 0 and 100 (excluding NaN values)
        valid_rps = result['rps_60'].dropna()
        if len(valid_rps) > 0:
            assert valid_rps.min() >= 0
            assert valid_rps.max() <= 100
    
    def test_rps_factor_compute_with_pct_chg(self):
        """Test RPS calculation with existing pct_chg"""
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 5,
            'trade_date': [d.strftime('%Y%m%d') for d in dates],
            'pct_chg': [5.0, 3.0, 1.0, -1.0, -3.0]
        })
        
        factor = RPSFactor(window=60)
        result = factor.compute(df.copy())
        
        assert 'rps_60' in result.columns
        # Highest pct_chg should have highest RPS
        assert result.loc[result['pct_chg'].idxmax(), 'rps_60'] >= result.loc[result['pct_chg'].idxmin(), 'rps_60']
    
    def test_rps_factor_empty_dataframe(self):
        """Test RPSFactor with empty DataFrame"""
        factor = RPSFactor(window=60)
        result = factor.compute(pd.DataFrame())
        assert result.empty
    
    def test_rps_factor_missing_columns(self):
        """Test RPSFactor with missing required columns"""
        factor = RPSFactor(window=60)
        df = pd.DataFrame({'ts_code': ['000001.SZ'], 'trade_date': ['20240101']})
        
        with pytest.raises(ValueError, match="requires either 'pct_chg' or 'close' column"):
            factor.compute(df)
    
    def test_rps_factor_single_stock(self):
        """Test RPSFactor with single stock"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 10,
            'trade_date': [d.strftime('%Y%m%d') for d in dates],
            'close': np.random.uniform(10, 12, 10)
        })
        
        factor = RPSFactor(window=5)
        result = factor.compute(df.copy())
        
        assert 'rps_5' in result.columns
        assert len(result) == 10


class TestMAFactor:
    """Test MAFactor"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for MA calculation"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ']:
            for i, date in enumerate(dates):
                close = 10.0 + i * 0.1
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'close': close
                })
        
        return pd.DataFrame(data)
    
    def test_ma_factor_initialization(self):
        """Test MAFactor initialization"""
        factor = MAFactor(window=20)
        assert factor.window == 20
        assert factor.name() == "ma_20"
    
    def test_ma_factor_compute(self, sample_data):
        """Test MA calculation"""
        factor = MAFactor(window=20)
        result = factor.compute(sample_data.copy())
        
        assert f'ma_{factor.window}' in result.columns
        assert 'above_ma_20' in result.columns
        assert len(result) == len(sample_data)
        
        # above_ma_20 should be 0 or 1
        assert set(result['above_ma_20'].unique()).issubset({0, 1})
    
    def test_ma_factor_above_ma_logic(self, sample_data):
        """Test above_ma logic"""
        factor = MAFactor(window=20)
        result = factor.compute(sample_data.copy())
        
        # For rows where close > ma, above_ma should be 1
        mask = result['close'] > result[f'ma_{factor.window}']
        assert (result.loc[mask, 'above_ma_20'] == 1).all()
    
    def test_ma_factor_empty_dataframe(self):
        """Test MAFactor with empty DataFrame"""
        factor = MAFactor(window=20)
        result = factor.compute(pd.DataFrame())
        assert result.empty
    
    def test_ma_factor_missing_close(self):
        """Test MAFactor with missing close column"""
        factor = MAFactor(window=20)
        df = pd.DataFrame({'ts_code': ['000001.SZ'], 'trade_date': ['20240101']})
        
        with pytest.raises(ValueError, match="requires 'close' column"):
            factor.compute(df)
    
    def test_ma_factor_different_windows(self, sample_data):
        """Test MAFactor with different window parameters"""
        for window in [5, 10, 20, 30]:
            factor = MAFactor(window=window)
            result = factor.compute(sample_data.copy())
            
            assert f'ma_{window}' in result.columns
            assert f'above_ma_{window}' in result.columns


class TestVolumeRatioFactor:
    """Test VolumeRatioFactor"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for volume ratio calculation"""
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ']:
            for i, date in enumerate(dates):
                vol = 1000000 + np.random.randint(-200000, 200000)
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'vol': vol
                })
        
        return pd.DataFrame(data)
    
    def test_volume_ratio_factor_initialization(self):
        """Test VolumeRatioFactor initialization"""
        factor = VolumeRatioFactor(window=5)
        assert factor.window == 5
        assert factor.name() == "volume_ratio_5"
    
    def test_volume_ratio_factor_compute(self, sample_data):
        """Test volume ratio calculation"""
        factor = VolumeRatioFactor(window=5)
        result = factor.compute(sample_data.copy())
        
        assert 'vol_ratio_5' in result.columns
        assert len(result) == len(sample_data)
        # Volume ratio should be positive
        assert (result['vol_ratio_5'] > 0).all()
    
    def test_volume_ratio_factor_with_volume_column(self):
        """Test VolumeRatioFactor with 'volume' column name"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 10,
            'trade_date': [d.strftime('%Y%m%d') for d in dates],
            'volume': np.random.uniform(1000000, 2000000, 10)
        })
        
        factor = VolumeRatioFactor(window=5)
        result = factor.compute(df.copy())
        
        assert 'vol_ratio_5' in result.columns
    
    def test_volume_ratio_factor_empty_dataframe(self):
        """Test VolumeRatioFactor with empty DataFrame"""
        factor = VolumeRatioFactor(window=5)
        result = factor.compute(pd.DataFrame())
        assert result.empty
    
    def test_volume_ratio_factor_missing_columns(self):
        """Test VolumeRatioFactor with missing volume column"""
        factor = VolumeRatioFactor(window=5)
        df = pd.DataFrame({'ts_code': ['000001.SZ'], 'trade_date': ['20240101']})
        
        with pytest.raises(ValueError, match="requires 'vol' or 'volume' column"):
            factor.compute(df)
    
    def test_volume_ratio_factor_zero_volume(self):
        """Test VolumeRatioFactor with zero volume"""
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 10,
            'trade_date': [d.strftime('%Y%m%d') for d in dates],
            'vol': [0] * 10
        })
        
        factor = VolumeRatioFactor(window=5)
        result = factor.compute(df.copy())
        
        # Should handle zero volume gracefully (fill with 1.0)
        assert 'vol_ratio_5' in result.columns
        assert (result['vol_ratio_5'] == 1.0).all()


class TestPEProxyFactor:
    """Test PEProxyFactor"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for PE proxy calculation"""
        return pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ'],
            'pe_ttm': [10.5, 25.0, 35.0, -5.0, 0.0]  # Mix of valid, high, negative, zero
        })
    
    def test_pe_proxy_factor_initialization(self):
        """Test PEProxyFactor initialization"""
        factor = PEProxyFactor(max_pe=30.0)
        assert factor.max_pe == 30.0
        assert factor.name() == "pe_proxy_30.0"
    
    def test_pe_proxy_factor_compute(self, sample_data):
        """Test PE proxy calculation"""
        factor = PEProxyFactor(max_pe=30.0)
        result = factor.compute(sample_data.copy())
        
        assert 'is_undervalued' in result.columns
        assert len(result) == len(sample_data)
        # is_undervalued should be 0 or 1
        assert set(result['is_undervalued'].unique()).issubset({0, 1})
    
    def test_pe_proxy_factor_logic(self, sample_data):
        """Test PE proxy logic: 0 < pe_ttm < max_pe"""
        factor = PEProxyFactor(max_pe=30.0)
        result = factor.compute(sample_data.copy())
        
        # pe_ttm = 10.5 (0 < 10.5 < 30) -> should be 1
        assert result.loc[result['pe_ttm'] == 10.5, 'is_undervalued'].iloc[0] == 1
        
        # pe_ttm = 25.0 (0 < 25.0 < 30) -> should be 1
        assert result.loc[result['pe_ttm'] == 25.0, 'is_undervalued'].iloc[0] == 1
        
        # pe_ttm = 35.0 (35.0 >= 30) -> should be 0
        assert result.loc[result['pe_ttm'] == 35.0, 'is_undervalued'].iloc[0] == 0
        
        # pe_ttm = -5.0 (negative) -> should be 0
        assert result.loc[result['pe_ttm'] == -5.0, 'is_undervalued'].iloc[0] == 0
        
        # pe_ttm = 0.0 (zero) -> should be 0
        assert result.loc[result['pe_ttm'] == 0.0, 'is_undervalued'].iloc[0] == 0
    
    def test_pe_proxy_factor_different_max_pe(self):
        """Test PEProxyFactor with different max_pe parameters"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'pe_ttm': [25.0]
        })
        
        # max_pe = 30, pe_ttm = 25 -> should be 1
        factor1 = PEProxyFactor(max_pe=30.0)
        result1 = factor1.compute(df.copy())
        assert result1['is_undervalued'].iloc[0] == 1
        
        # max_pe = 20, pe_ttm = 25 -> should be 0
        factor2 = PEProxyFactor(max_pe=20.0)
        result2 = factor2.compute(df.copy())
        assert result2['is_undervalued'].iloc[0] == 0
    
    def test_pe_proxy_factor_empty_dataframe(self):
        """Test PEProxyFactor with empty DataFrame"""
        factor = PEProxyFactor(max_pe=30.0)
        result = factor.compute(pd.DataFrame())
        assert result.empty
    
    def test_pe_proxy_factor_missing_pe_ttm(self):
        """Test PEProxyFactor with missing pe_ttm column"""
        factor = PEProxyFactor(max_pe=30.0)
        df = pd.DataFrame({'ts_code': ['000001.SZ']})
        
        with pytest.raises(ValueError, match="requires 'pe_ttm' column"):
            factor.compute(df)


class TestFactorPipeline:
    """Test FactorPipeline"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for pipeline testing"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ']:
            for i, date in enumerate(dates[:60]):
                close = 10.0 + i * 0.1
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'close': close,
                    'vol': 1000000 + np.random.randint(-100000, 100000),
                    'pe_ttm': 15.0 + np.random.normal(0, 5)
                })
        
        return pd.DataFrame(data)
    
    def test_factor_pipeline_initialization(self):
        """Test FactorPipeline initialization"""
        pipeline = FactorPipeline()
        assert len(pipeline) == 0
        assert pipeline.factors == []
    
    def test_factor_pipeline_add(self):
        """Test adding factors to pipeline"""
        pipeline = FactorPipeline()
        rps = RPSFactor(window=60)
        ma = MAFactor(window=20)
        
        pipeline.add(rps)
        assert len(pipeline) == 1
        
        pipeline.add(ma)
        assert len(pipeline) == 2
    
    def test_factor_pipeline_add_type_check(self):
        """Test that add() only accepts BaseFactor instances"""
        pipeline = FactorPipeline()
        
        with pytest.raises(TypeError, match="must be an instance of BaseFactor"):
            pipeline.add("not a factor")
    
    def test_factor_pipeline_chaining(self):
        """Test method chaining"""
        pipeline = FactorPipeline()
        result = pipeline.add(RPSFactor()).add(MAFactor()).add(PEProxyFactor())
        
        assert result is pipeline
        assert len(pipeline) == 3
    
    def test_factor_pipeline_run(self, sample_data):
        """Test running pipeline"""
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        result = pipeline.run(sample_data.copy())
        
        assert 'rps_60' in result.columns
        assert 'above_ma_20' in result.columns
        assert 'vol_ratio_5' in result.columns
        assert 'is_undervalued' in result.columns
        assert len(result) == len(sample_data)
    
    def test_factor_pipeline_run_empty_dataframe(self):
        """Test running pipeline with empty DataFrame"""
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor())
        
        result = pipeline.run(pd.DataFrame())
        assert result.empty
    
    def test_factor_pipeline_run_order(self, sample_data):
        """Test that factors are executed in order"""
        pipeline = FactorPipeline()
        
        # Add factors in specific order
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        
        result = pipeline.run(sample_data.copy())
        
        # Both factors should be computed
        assert 'rps_60' in result.columns
        assert 'above_ma_20' in result.columns
    
    def test_factor_pipeline_run_error_handling(self):
        """Test error handling in pipeline"""
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        
        # Missing required columns should raise error
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101']
            # Missing 'close' or 'pct_chg'
        })
        
        with pytest.raises(ValueError):
            pipeline.run(df)
    
    def test_factor_pipeline_clear(self):
        """Test clearing pipeline"""
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor()).add(MAFactor())
        
        assert len(pipeline) == 2
        
        pipeline.clear()
        assert len(pipeline) == 0
    
    def test_factor_pipeline_repr(self):
        """Test pipeline string representation"""
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        
        repr_str = repr(pipeline)
        assert 'FactorPipeline' in repr_str
        assert 'rps_60' in repr_str
        assert 'ma_20' in repr_str
