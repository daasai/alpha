"""
Performance tests for Backtest Engine
Tests backtest execution speed and efficiency
"""

import pytest
import pandas as pd
import numpy as np
import time
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.backtest import VectorBacktester


class TestBacktestPerformance:
    """Test backtest engine performance"""
    
    @pytest.fixture
    def large_backtest_data(self):
        """Create large dataset for backtest performance testing"""
        dates = pd.date_range('2023-01-01', periods=500, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
        data = []
        # Create data for 50 stocks
        for stock_num in range(1, 51):
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
    
    def test_backtest_execution_speed(self, large_backtest_data):
        """Test backtest execution speed"""
        backtester = VectorBacktester()
        
        # Measure execution time
        start_time = time.time()
        results = backtester.run(large_backtest_data.copy(), holding_days=5)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should complete in reasonable time (< 30 seconds for 50 stocks * 500 days)
        assert execution_time < 30.0, f"Backtest took {execution_time:.2f}s, expected < 30s"
        
        # Verify results are correct
        assert 'strategy_metrics' in results
        assert 'trades' in results
    
    def test_backtest_vectorization(self, large_backtest_data):
        """Test that backtest uses vectorized operations"""
        backtester = VectorBacktester()
        
        start_time = time.time()
        results = backtester.run(large_backtest_data.copy(), holding_days=5)
        end_time = time.time()
        
        execution_time = end_time - start_time
        rows_per_second = len(large_backtest_data) / execution_time
        
        # Should process at least 500 rows per second (vectorized)
        assert rows_per_second > 500, f"Processing speed: {rows_per_second:.0f} rows/s, expected > 500"
    
    def test_backtest_different_holding_days_performance(self, large_backtest_data):
        """Test performance with different holding_days"""
        backtester = VectorBacktester()
        
        times = {}
        for holding_days in [3, 5, 10, 20]:
            start_time = time.time()
            results = backtester.run(large_backtest_data.copy(), holding_days=holding_days)
            end_time = time.time()
            times[holding_days] = end_time - start_time
        
        # All should complete in reasonable time
        for holding_days, exec_time in times.items():
            assert exec_time < 30.0, f"Backtest with holding_days={holding_days} took {exec_time:.2f}s"
    
    def test_buy_signal_generation_performance(self, large_backtest_data):
        """Test buy signal generation performance"""
        from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
        
        # Compute factors first
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(large_backtest_data.copy())
        
        # Test buy signal generation
        backtester = VectorBacktester()
        
        start_time = time.time()
        signal_df = backtester._generate_buy_signals(enriched_df.copy())
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should be very fast (vectorized)
        assert execution_time < 1.0, f"Buy signal generation took {execution_time:.2f}s"
        assert 'buy_signal' in signal_df.columns
    
    def test_return_calculation_performance(self, large_backtest_data):
        """Test return calculation performance"""
        from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
        
        # Setup data with buy signals
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(large_backtest_data.copy())
        
        # Add some buy signals
        enriched_df.loc[enriched_df.index[::10], 'rps_60'] = 90.0
        enriched_df.loc[enriched_df.index[::10], 'is_undervalued'] = 1
        enriched_df.loc[enriched_df.index[::10], 'vol_ratio_5'] = 2.0
        enriched_df.loc[enriched_df.index[::10], 'above_ma_20'] = 1
        enriched_df.loc[enriched_df.index[::10], 'buy_signal'] = 1
        
        backtester = VectorBacktester()
        
        start_time = time.time()
        returns_df = backtester._calculate_returns(enriched_df.copy(), holding_days=5)
        end_time = time.time()
        
        execution_time = end_time - start_time
        
        # Should be fast (vectorized)
        assert execution_time < 2.0, f"Return calculation took {execution_time:.2f}s"
        assert 'return' in returns_df.columns
