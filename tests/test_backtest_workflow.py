"""
Integration tests for Backtest workflow
Tests complete flow: fetch_history_batch → FactorPipeline → VectorBacktester.run()
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.data_provider import DataProvider
from src.backtest import VectorBacktester


class TestBacktestWorkflow:
    """Test complete Backtest workflow"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """Create mocked DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def sample_history_data(self):
        """Create sample history data for backtesting"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:80]  # 80 weekdays
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ']:
            for i, date in enumerate(dates):
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.1,
                    'high': 10.0 + i * 0.1 + 0.2,
                    'low': 10.0 + i * 0.1 - 0.1,
                    'close': 10.0 + i * 0.1 + 0.05,
                    'vol': 1000000 + np.random.randint(-100000, 100000),
                    'pe_ttm': 15.0 + np.random.normal(0, 5)
                })
        
        return pd.DataFrame(data)
    
    def test_backtest_workflow_complete(self, mock_data_provider, sample_history_data):
        """Test complete backtest workflow"""
        # Step 1: fetch_history_batch (simulated - using sample data)
        history_df = sample_history_data.copy()
        
        # Step 2: VectorBacktester.run()
        backtester = VectorBacktester(mock_data_provider)
        results = backtester.run(history_df, holding_days=5)
        
        # Verify result structure
        assert 'strategy_metrics' in results
        assert 'benchmark_metrics' in results
        assert 'trades' in results
        
        # Verify strategy metrics
        strategy_metrics = results['strategy_metrics']
        assert 'win_rate' in strategy_metrics
        assert 'total_return' in strategy_metrics
        assert 'max_drawdown' in strategy_metrics
        assert 'total_trades' in strategy_metrics
        
        # Verify trades
        trades = results['trades']
        assert isinstance(trades, pd.DataFrame)
    
    def test_backtest_workflow_data_integrity(self, sample_history_data):
        """Test that data integrity is maintained through workflow"""
        initial_count = len(sample_history_data)
        
        backtester = VectorBacktester()
        results = backtester.run(sample_history_data.copy(), holding_days=5)
        
        # Trades should be subset of original data
        trades = results['trades']
        if not trades.empty:
            assert len(trades) <= initial_count
    
    def test_backtest_workflow_factor_computation(self, sample_history_data):
        """Test that factors are computed correctly in backtest"""
        backtester = VectorBacktester()
        
        # Run backtest
        results = backtester.run(sample_history_data.copy(), holding_days=5)
        
        # Verify that factor pipeline was used
        assert len(backtester.factor_pipeline) == 4
        
        # Verify metrics are calculated
        strategy_metrics = results['strategy_metrics']
        assert isinstance(strategy_metrics['win_rate'], (int, float))
        assert isinstance(strategy_metrics['total_return'], (int, float))
    
    def test_backtest_workflow_different_holding_days(self, sample_history_data):
        """Test backtest with different holding_days"""
        backtester = VectorBacktester()
        
        results_3 = backtester.run(sample_history_data.copy(), holding_days=3)
        results_5 = backtester.run(sample_history_data.copy(), holding_days=5)
        results_10 = backtester.run(sample_history_data.copy(), holding_days=10)
        
        # All should complete successfully
        assert 'strategy_metrics' in results_3
        assert 'strategy_metrics' in results_5
        assert 'strategy_metrics' in results_10
        
        # Trades count may differ based on holding_days
        # (shorter holding_days may have more valid trades)
    
    def test_backtest_workflow_empty_data(self):
        """Test backtest with empty data"""
        backtester = VectorBacktester()
        results = backtester.run(pd.DataFrame(), holding_days=5)
        
        # Should handle gracefully
        assert 'strategy_metrics' in results
        assert 'trades' in results
        assert results['trades'].empty
    
    def test_backtest_workflow_benchmark_integration(self, mock_data_provider, sample_history_data):
        """Test benchmark data integration"""
        # Mock benchmark data
        mock_index_df = pd.DataFrame({
            'trade_date': ['20240101', '20240102', '20240103'],
            'close': [3000.0, 3010.0, 3005.0]
        })
        mock_data_provider._pro.index_daily.return_value = mock_index_df
        
        backtester = VectorBacktester(mock_data_provider)
        results = backtester.run(sample_history_data.copy(), holding_days=5)
        
        # Verify benchmark metrics
        benchmark_metrics = results['benchmark_metrics']
        assert 'total_return' in benchmark_metrics
        assert 'max_drawdown' in benchmark_metrics
        assert 'avg_return' in benchmark_metrics
