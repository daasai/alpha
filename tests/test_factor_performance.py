"""
Performance tests for Factor Engine
Tests factor computation speed and memory usage
"""

import pytest
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor


class TestFactorPerformance:
    """Test factor computation performance"""
    
    @pytest.fixture
    def large_dataset(self):
        """Create large dataset for performance testing"""
        dates = pd.date_range('2023-01-01', periods=500, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
        data = []
        # Create data for 100 stocks
        for stock_num in range(1, 101):
            ts_code = f"000{stock_num:03d}.SZ"
            for i, date in enumerate(dates):
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.1 + np.random.normal(0, 0.1),
                    'high': 10.0 + i * 0.1 + 0.2,
                    'low': 10.0 + i * 0.1 - 0.1,
                    'close': 10.0 + i * 0.1 + 0.05,
                    'vol': 1000000 + np.random.randint(-100000, 100000),
                    'pe_ttm': 15.0 + np.random.normal(0, 5)
                })
        
        return pd.DataFrame(data)
    
    def test_factor_pipeline_performance(self, large_dataset):
        """Test factor pipeline performance on large dataset"""
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        # Measure execution time
        start_time = time.time()
        result = pipeline.run(large_dataset.copy())
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete in reasonable time (< 10 seconds for 100 stocks * 500 days)
        assert execution_time < 10.0, f"Factor computation took {execution_time:.2f}s, expected < 10s"
        
        # Verify result is correct
        assert len(result) == len(large_dataset)
        assert 'rps_60' in result.columns
        assert 'above_ma_20' in result.columns
        assert 'vol_ratio_5' in result.columns
        assert 'is_undervalued' in result.columns
    
    def test_factor_vectorization(self, large_dataset):
        """Test that factors use vectorized operations (no row loops)"""
        import inspect
        import ast
        
        # Check RPSFactor compute method
        rps_source = inspect.getsource(RPSFactor.compute)
        
        # Should not contain explicit row iteration patterns
        # (This is a basic check - full verification would require AST analysis)
        # For now, we verify performance indicates vectorization
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        
        start_time = time.time()
        result = pipeline.run(large_dataset.copy())
        end_time = time.time()
        
        # Vectorized operations should be fast
        execution_time = end_time - start_time
        rows_per_second = len(large_dataset) / execution_time
        
        # Should process at least 1000 rows per second (vectorized)
        assert rows_per_second > 1000, f"Processing speed: {rows_per_second:.0f} rows/s, expected > 1000"
    
    def test_memory_usage(self, large_dataset):
        """Test memory usage during factor computation"""
        import sys
        
        # Get initial memory (approximate)
        initial_size = sys.getsizeof(large_dataset)
        
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        result = pipeline.run(large_dataset.copy())
        
        # Memory should not grow excessively (result should be similar size)
        result_size = sys.getsizeof(result)
        
        # Result should be reasonable (may be larger due to new columns)
        assert result_size < initial_size * 2, "Memory usage seems excessive"
    
    def test_individual_factor_performance(self, large_dataset):
        """Test performance of individual factors"""
        # Test RPSFactor
        rps_factor = RPSFactor(window=60)
        start_time = time.time()
        rps_result = rps_factor.compute(large_dataset.copy())
        rps_time = time.time() - start_time
        
        assert rps_time < 5.0, f"RPSFactor took {rps_time:.2f}s"
        
        # Test MAFactor
        ma_factor = MAFactor(window=20)
        start_time = time.time()
        ma_result = ma_factor.compute(large_dataset.copy())
        ma_time = time.time() - start_time
        
        assert ma_time < 2.0, f"MAFactor took {ma_time:.2f}s"
        
        # Test VolumeRatioFactor
        vol_factor = VolumeRatioFactor(window=5)
        start_time = time.time()
        vol_result = vol_factor.compute(large_dataset.copy())
        vol_time = time.time() - start_time
        
        assert vol_time < 2.0, f"VolumeRatioFactor took {vol_time:.2f}s"
        
        # Test PEProxyFactor
        pe_factor = PEProxyFactor(max_pe=30)
        start_time = time.time()
        pe_result = pe_factor.compute(large_dataset.copy())
        pe_time = time.time() - start_time
        
        assert pe_time < 1.0, f"PEProxyFactor took {pe_time:.2f}s"
