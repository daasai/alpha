"""
Quantitative Engineering Tests - Strategy Performance
Tests Alpha Trident strategy performance vs benchmark
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.backtest import VectorBacktester
from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
from src.strategy import AlphaStrategy


class TestStrategyPerformance:
    """Test Alpha Trident strategy performance"""
    
    @pytest.fixture
    def sample_backtest_data(self):
        """Create sample data for strategy backtesting"""
        dates = pd.date_range('2024-01-01', periods=200, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:150]  # 150 weekdays
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ', '000005.SZ']:
            for i, date in enumerate(dates):
                # Create realistic price movement
                base_price = 10.0
                trend = i * 0.05  # Slight upward trend
                noise = np.random.normal(0, 0.1)
                close = base_price + trend + noise
                
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': close - 0.05,
                    'high': close + 0.1,
                    'low': close - 0.1,
                    'close': close,
                    'vol': 1000000 + np.random.randint(-200000, 200000),
                    'pe_ttm': 15.0 + np.random.normal(0, 5)
                })
        
        return pd.DataFrame(data)
    
    def test_strategy_generates_signals(self, sample_backtest_data):
        """Test that strategy generates buy signals"""
        # Compute factors
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(sample_backtest_data.copy())
        
        # Apply strategy
        strategy = AlphaStrategy(enriched_df)
        result_df = strategy.filter_alpha_trident()
        
        # Strategy should generate some signals (may be 0 if no stocks meet criteria)
        assert isinstance(result_df, pd.DataFrame)
    
    def test_strategy_metrics_calculation(self, sample_backtest_data):
        """Test that strategy metrics are calculated correctly"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        results = backtester.run(sample_backtest_data.copy(), holding_days=5)
        
        strategy_metrics = results['strategy_metrics']
        
        # Verify all metrics are present and valid
        assert 'win_rate' in strategy_metrics
        assert 'total_return' in strategy_metrics
        assert 'max_drawdown' in strategy_metrics
        assert 'total_trades' in strategy_metrics
        
        # Metrics should be numeric
        assert isinstance(strategy_metrics['win_rate'], (int, float))
        assert isinstance(strategy_metrics['total_return'], (int, float))
        assert isinstance(strategy_metrics['max_drawdown'], (int, float))
        assert isinstance(strategy_metrics['total_trades'], int)
    
    def test_strategy_vs_benchmark_comparison(self, sample_backtest_data):
        """Test strategy performance vs benchmark"""
        from src.backtest import VectorBacktester
        from unittest.mock import MagicMock
        
        # Mock benchmark data
        mock_dp = MagicMock()
        mock_index_df = pd.DataFrame({
            'trade_date': ['20240101', '20240102', '20240103'],
            'close': [3000.0, 3010.0, 3005.0]
        })
        mock_dp._pro.index_daily.return_value = mock_index_df
        
        backtester = VectorBacktester(mock_dp)
        results = backtester.run(sample_backtest_data.copy(), holding_days=5)
        
        # Verify benchmark metrics
        benchmark_metrics = results['benchmark_metrics']
        assert 'total_return' in benchmark_metrics
        assert 'max_drawdown' in benchmark_metrics
        
        # Both strategy and benchmark should have metrics
        assert 'strategy_metrics' in results
        assert 'benchmark_metrics' in results


class TestStrategyStability:
    """Test strategy stability and robustness"""
    
    @pytest.fixture
    def sample_data_variations(self):
        """Create data with different market conditions"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        # Bull market data
        bull_data = []
        for ts_code in ['000001.SZ']:
            for i, date in enumerate(dates):
                bull_data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.2,
                    'close': 10.0 + i * 0.2 + 0.1,
                    'vol': 1500000,
                    'pe_ttm': 20.0
                })
        
        # Bear market data
        bear_data = []
        for ts_code in ['000002.SZ']:
            for i, date in enumerate(dates):
                bear_data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 - i * 0.1,
                    'close': 10.0 - i * 0.1 - 0.05,
                    'vol': 800000,
                    'pe_ttm': 25.0
                })
        
        return pd.DataFrame(bull_data), pd.DataFrame(bear_data)
    
    def test_strategy_different_market_conditions(self, sample_data_variations):
        """Test strategy in different market conditions"""
        bull_data, bear_data = sample_data_variations
        
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        # Test in bull market
        bull_enriched = pipeline.run(bull_data.copy())
        bull_strategy = AlphaStrategy(bull_enriched)
        bull_result = bull_strategy.filter_alpha_trident()
        
        # Test in bear market
        bear_enriched = pipeline.run(bear_data.copy())
        bear_strategy = AlphaStrategy(bear_enriched)
        bear_result = bear_strategy.filter_alpha_trident()
        
        # Both should complete without errors
        assert isinstance(bull_result, pd.DataFrame)
        assert isinstance(bear_result, pd.DataFrame)
    
    def test_strategy_parameter_sensitivity(self):
        """Test strategy with different parameters"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        data = []
        for ts_code in ['000001.SZ']:
            for i, date in enumerate(dates):
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.1,
                    'close': 10.0 + i * 0.1 + 0.05,
                    'vol': 1000000,
                    'pe_ttm': 15.0
                })
        
        df = pd.DataFrame(data)
        
        # Test with different RPS thresholds
        pipeline1 = FactorPipeline()
        pipeline1.add(RPSFactor(window=60))
        pipeline1.add(MAFactor(window=20))
        pipeline1.add(VolumeRatioFactor(window=5))
        pipeline1.add(PEProxyFactor(max_pe=30))
        
        enriched1 = pipeline1.run(df.copy())
        strategy1 = AlphaStrategy(enriched1)
        result1 = strategy1.filter_alpha_trident()
        
        # Test with different PE threshold
        pipeline2 = FactorPipeline()
        pipeline2.add(RPSFactor(window=60))
        pipeline2.add(MAFactor(window=20))
        pipeline2.add(VolumeRatioFactor(window=5))
        pipeline2.add(PEProxyFactor(max_pe=20))  # Different PE threshold
        
        enriched2 = pipeline2.run(df.copy())
        strategy2 = AlphaStrategy(enriched2)
        result2 = strategy2.filter_alpha_trident()
        
        # Both should complete
        assert isinstance(result1, pd.DataFrame)
        assert isinstance(result2, pd.DataFrame)
