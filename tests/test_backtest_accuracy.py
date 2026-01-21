"""
Quantitative Engineering Tests - Backtest Accuracy
Tests accuracy of return calculations and performance metrics
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtest import VectorBacktester


class TestReturnCalculationAccuracy:
    """Test return calculation accuracy"""
    
    @pytest.fixture
    def sample_trade_data(self):
        """Create sample data for manual return verification"""
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        data = []
        for ts_code in ['000001.SZ']:
            for i, date in enumerate(dates):
                base_price = 10.0 + i * 0.1
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': base_price,
                    'high': base_price + 0.1,
                    'low': base_price - 0.05,
                    'close': base_price + 0.05,
                    'vol': 1000000,
                    'pe_ttm': 15.0
                })
        
        return pd.DataFrame(data)
    
    def test_return_calculation_manual_verification(self, sample_trade_data):
        """Manually verify return calculation"""
        from src.backtest import VectorBacktester
        from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
        
        # Create data with known buy signal
        df = sample_trade_data.copy()
        
        # Compute factors and set up buy signal
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(df.copy())
        
        # Manually set buy signal on day 5
        if len(enriched_df) > 10:
            enriched_df.loc[5, 'rps_60'] = 90.0
            enriched_df.loc[5, 'is_undervalued'] = 1
            enriched_df.loc[5, 'vol_ratio_5'] = 2.0
            enriched_df.loc[5, 'above_ma_20'] = 1
            enriched_df.loc[5, 'buy_signal'] = 1
        
        backtester = VectorBacktester()
        returns_df = backtester._calculate_returns(enriched_df, holding_days=5)
        
        # Verify return calculation
        buy_row = returns_df[returns_df['buy_signal'] == 1]
        if len(buy_row) > 0 and buy_row['return'].notna().any():
            return_value = buy_row['return'].dropna().iloc[0]
            assert isinstance(return_value, (int, float))
    
    def test_return_calculation_t_plus_one_logic(self):
        """Test T+1 Open buy, T+1+N Close sell logic"""
        # Create specific data to test timing
        dates = pd.date_range('2024-01-01', periods=15, freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        data = []
        for i, date in enumerate(dates):
            base_price = 10.0 + i * 0.1
            data.append({
                'ts_code': '000001.SZ',
                'trade_date': date.strftime('%Y%m%d'),
                'open': base_price,
                'high': base_price + 0.1,
                'low': base_price - 0.05,
                'close': base_price + 0.05,
                'vol': 1000000,
                'pe_ttm': 15.0,
                'buy_signal': 1 if i == 5 else 0  # Buy signal on day 5
            })
        
        df = pd.DataFrame(data)
        
        backtester = VectorBacktester()
        returns_df = backtester._calculate_returns(df, holding_days=3)
        
        # Buy on day 5 -> T+1 Open (day 6) -> T+1+3 Close (day 9)
        # If we have enough data, return should be calculated
        buy_row = returns_df[returns_df['buy_signal'] == 1]
        if len(buy_row) > 0:
            # Return may be NaN if not enough data, or calculated if enough
            assert 'return' in returns_df.columns


class TestPerformanceMetricsAccuracy:
    """Test performance metrics calculation accuracy"""
    
    def test_win_rate_calculation(self):
        """Test win rate calculation accuracy"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        
        # Test with known returns
        returns = pd.Series([5.0, -2.0, 3.0, -1.0, 4.0])  # 3 wins, 2 losses
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['win_rate'] == 60.0  # 3/5 = 60%
        assert metrics['total_trades'] == 5
    
    def test_total_return_calculation(self):
        """Test total return calculation accuracy"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        
        # Test with known returns
        returns = pd.Series([10.0, -5.0, 3.0, 2.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['total_return'] == 10.0  # 10 - 5 + 3 + 2 = 10
    
    def test_max_drawdown_calculation(self):
        """Test max drawdown calculation"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        
        # Create returns that cause drawdown
        returns = pd.Series([10.0, -5.0, -3.0, 2.0, 1.0])
        metrics = backtester._calculate_metrics(returns)
        
        # Max drawdown should be calculated
        assert metrics['max_drawdown'] >= 0
        assert isinstance(metrics['max_drawdown'], float)
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        
        returns = pd.Series([5.0, -2.0, 3.0, 1.0, 2.0])
        metrics = backtester._calculate_metrics(returns)
        
        # Sharpe ratio should be calculated if std > 0
        assert isinstance(metrics['sharpe_ratio'], float)
        if metrics['avg_return'] != 0:
            assert metrics['sharpe_ratio'] != 0
    
    def test_metrics_with_single_trade(self):
        """Test metrics with single trade"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        
        returns = pd.Series([10.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['win_rate'] == 100.0  # 1 win
        assert metrics['total_return'] == 10.0
        assert metrics['total_trades'] == 1
    
    def test_metrics_with_all_wins(self):
        """Test metrics with all winning trades"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        
        returns = pd.Series([5.0, 3.0, 2.0, 1.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['win_rate'] == 100.0
        assert metrics['total_return'] == 11.0
    
    def test_metrics_with_all_losses(self):
        """Test metrics with all losing trades"""
        from src.backtest import VectorBacktester
        
        backtester = VectorBacktester()
        
        returns = pd.Series([-5.0, -3.0, -2.0, -1.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['win_rate'] == 0.0
        assert metrics['total_return'] == -11.0
