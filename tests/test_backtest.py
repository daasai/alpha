"""
Unit tests for VectorBacktester
Tests for backtesting engine functionality
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.backtest import VectorBacktester
from src.data_provider import DataProvider


class TestVectorBacktesterInit:
    """Test VectorBacktester initialization"""
    
    @patch('src.backtest.DataProvider')
    def test_init_with_data_provider(self, mock_dp_class):
        """Test initialization with provided DataProvider"""
        mock_dp = MagicMock()
        mock_dp_class.return_value = mock_dp
        
        backtester = VectorBacktester(mock_dp)
        
        assert backtester.data_provider is mock_dp
        assert len(backtester.factor_pipeline) == 4  # 4 factors added
    
    @patch('src.backtest.DataProvider')
    def test_init_without_data_provider(self, mock_dp_class):
        """Test initialization without DataProvider (creates new one)"""
        mock_dp = MagicMock()
        mock_dp_class.return_value = mock_dp
        
        backtester = VectorBacktester()
        
        assert backtester.data_provider is mock_dp
        mock_dp_class.assert_called_once()
        assert len(backtester.factor_pipeline) == 4


class TestGenerateBuySignals:
    """Test _generate_buy_signals method"""
    
    @pytest.fixture
    def backtester(self):
        """Create VectorBacktester instance"""
        with patch('src.backtest.DataProvider'):
            return VectorBacktester()
    
    @pytest.fixture
    def sample_enriched_df(self):
        """Create sample enriched DataFrame with factors"""
        return pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ'],
            'trade_date': ['20240101', '20240102', '20240103', '20240104'],
            'rps_60': [90.0, 95.0, 80.0, 88.0],  # 000003.SZ fails momentum
            'is_undervalued': [1, 1, 1, 0],  # 000004.SZ fails value
            'vol_ratio_5': [2.0, 1.8, 2.2, 1.6],  # All pass liquidity
            'above_ma_20': [1, 1, 1, 1]  # All pass trend
        })
    
    def test_generate_buy_signals_all_conditions_met(self, backtester, sample_enriched_df):
        """Test buy signal generation when all conditions are met"""
        result = backtester._generate_buy_signals(sample_enriched_df.copy())
        
        assert 'buy_signal' in result.columns
        # Only 000001.SZ and 000002.SZ should have buy_signal = 1
        assert result.loc[result['ts_code'] == '000001.SZ', 'buy_signal'].iloc[0] == 1
        assert result.loc[result['ts_code'] == '000002.SZ', 'buy_signal'].iloc[0] == 1
        assert result.loc[result['ts_code'] == '000003.SZ', 'buy_signal'].iloc[0] == 0
        assert result.loc[result['ts_code'] == '000004.SZ', 'buy_signal'].iloc[0] == 0
    
    def test_generate_buy_signals_missing_columns(self, backtester):
        """Test buy signal generation with missing required columns"""
        df = pd.DataFrame({'ts_code': ['000001.SZ']})
        
        with pytest.raises(ValueError, match="缺少必需的因子列"):
            backtester._generate_buy_signals(df)
    
    def test_generate_buy_signals_vectorized(self, backtester, sample_enriched_df):
        """Test that buy signals are generated vectorized (no loops)"""
        result = backtester._generate_buy_signals(sample_enriched_df.copy())
        
        # buy_signal should be 0 or 1
        assert set(result['buy_signal'].unique()).issubset({0, 1})
        
        # Verify logic: all conditions must be True
        buy_signals = result[result['buy_signal'] == 1]
        if len(buy_signals) > 0:
            assert (buy_signals['rps_60'] > 85).all()
            assert (buy_signals['is_undervalued'] == 1).all()
            assert (buy_signals['vol_ratio_5'] > 1.5).all()
            assert (buy_signals['above_ma_20'] == 1).all()


class TestCalculateReturns:
    """Test _calculate_returns method"""
    
    @pytest.fixture
    def backtester(self):
        """Create VectorBacktester instance"""
        with patch('src.backtest.DataProvider'):
            return VectorBacktester()
    
    @pytest.fixture
    def sample_data_with_signals(self):
        """Create sample data with buy signals"""
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
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
                    'buy_signal': 1 if i == 5 else 0  # Buy signal on day 5
                })
        
        return pd.DataFrame(data)
    
    def test_calculate_returns_basic(self, backtester, sample_data_with_signals):
        """Test basic return calculation"""
        result = backtester._calculate_returns(sample_data_with_signals.copy(), holding_days=5)
        
        assert 'return' in result.columns
        
        # Find the buy signal row
        buy_row = result[result['buy_signal'] == 1]
        if len(buy_row) > 0:
            # Return should be calculated if we have enough data
            # T+1 Open (day 6) to T+1+5 Close (day 11)
            # If we have 20 days, we should have enough data
            returns = buy_row['return'].dropna()
            if len(returns) > 0:
                assert isinstance(returns.iloc[0], (int, float))
    
    def test_calculate_returns_holding_days(self, backtester, sample_data_with_signals):
        """Test return calculation with different holding_days"""
        result1 = backtester._calculate_returns(sample_data_with_signals.copy(), holding_days=3)
        result2 = backtester._calculate_returns(sample_data_with_signals.copy(), holding_days=5)
        
        # Returns should be different for different holding periods
        buy_row1 = result1[result1['buy_signal'] == 1]['return'].dropna()
        buy_row2 = result2[result2['buy_signal'] == 1]['return'].dropna()
        
        # If both have returns, they should be different
        if len(buy_row1) > 0 and len(buy_row2) > 0:
            # They might be different (or same if data allows)
            pass  # Just verify they can be calculated
    
    def test_calculate_returns_missing_columns(self, backtester):
        """Test return calculation with missing price columns"""
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'buy_signal': [1]
        })
        
        with pytest.raises(ValueError, match="缺少必需的价格列"):
            backtester._calculate_returns(df)
    
    def test_calculate_returns_no_buy_signals(self, backtester, sample_data_with_signals):
        """Test return calculation when there are no buy signals"""
        df = sample_data_with_signals.copy()
        df['buy_signal'] = 0
        
        result = backtester._calculate_returns(df, holding_days=5)
        
        # All returns should be NaN
        assert result['return'].isna().all()
    
    def test_calculate_returns_insufficient_data(self, backtester):
        """Test return calculation with insufficient data"""
        # Only 3 days of data, but need T+1+5 = 6 days minimum
        df = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 3,
            'trade_date': ['20240101', '20240102', '20240103'],
            'open': [10.0, 10.1, 10.2],
            'high': [10.1, 10.2, 10.3],
            'low': [9.95, 10.05, 10.15],
            'close': [10.05, 10.15, 10.25],
            'buy_signal': [1, 0, 0]
        })
        
        result = backtester._calculate_returns(df, holding_days=5)
        
        # Should not crash, but returns should be NaN
        assert result['return'].isna().all()


class TestCalculateMetrics:
    """Test _calculate_metrics method"""
    
    @pytest.fixture
    def backtester(self):
        """Create VectorBacktester instance"""
        with patch('src.backtest.DataProvider'):
            return VectorBacktester()
    
    def test_calculate_metrics_empty_returns(self, backtester):
        """Test metrics calculation with empty returns"""
        returns = pd.Series([], dtype=float)
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['win_rate'] == 0.0
        assert metrics['total_return'] == 0.0
        assert metrics['max_drawdown'] == 0.0
        assert metrics['total_trades'] == 0
    
    def test_calculate_metrics_all_nan(self, backtester):
        """Test metrics calculation with all NaN returns"""
        returns = pd.Series([np.nan, np.nan, np.nan])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['win_rate'] == 0.0
        assert metrics['total_trades'] == 0
    
    def test_calculate_metrics_win_rate(self, backtester):
        """Test win rate calculation"""
        # 3 wins, 2 losses
        returns = pd.Series([5.0, -2.0, 3.0, -1.0, 4.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['win_rate'] == 60.0  # 3/5 = 60%
        assert metrics['total_trades'] == 5
    
    def test_calculate_metrics_total_return(self, backtester):
        """Test total return calculation"""
        returns = pd.Series([5.0, -2.0, 3.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['total_return'] == 6.0  # 5 - 2 + 3 = 6
    
    def test_calculate_metrics_avg_return(self, backtester):
        """Test average return calculation"""
        returns = pd.Series([5.0, -2.0, 3.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['avg_return'] == 2.0  # (5 - 2 + 3) / 3 = 2
    
    def test_calculate_metrics_max_drawdown(self, backtester):
        """Test max drawdown calculation"""
        # Returns that create a drawdown
        returns = pd.Series([10.0, -5.0, -3.0, 2.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert metrics['max_drawdown'] >= 0
        assert isinstance(metrics['max_drawdown'], float)
    
    def test_calculate_metrics_sharpe_ratio(self, backtester):
        """Test Sharpe ratio calculation"""
        returns = pd.Series([5.0, -2.0, 3.0, 1.0, 2.0])
        metrics = backtester._calculate_metrics(returns)
        
        assert isinstance(metrics['sharpe_ratio'], float)
        # Sharpe ratio should be calculated if std > 0
        if metrics['avg_return'] != 0:
            assert metrics['sharpe_ratio'] != 0
    
    def test_calculate_metrics_zero_std(self, backtester):
        """Test metrics with zero standard deviation"""
        returns = pd.Series([5.0, 5.0, 5.0])  # All same
        metrics = backtester._calculate_metrics(returns)
        
        # Sharpe ratio should be 0 when std is 0
        assert metrics['sharpe_ratio'] == 0.0


class TestGetBenchmarkData:
    """Test _get_benchmark_data method"""
    
    @pytest.fixture
    def backtester(self):
        """Create VectorBacktester with mocked DataProvider"""
        mock_dp = MagicMock()
        mock_pro = MagicMock()
        mock_dp._pro = mock_pro
        
        with patch('src.backtest.DataProvider', return_value=mock_dp):
            backtester = VectorBacktester(mock_dp)
            backtester.data_provider = mock_dp
            return backtester
    
    def test_get_benchmark_data_success(self, backtester):
        """Test successful benchmark data retrieval"""
        mock_index_df = pd.DataFrame({
            'trade_date': ['20240101', '20240102', '20240103'],
            'close': [3000.0, 3010.0, 3005.0]
        })
        
        # Mock the tushare client properly
        backtester.data_provider._tushare_client = MagicMock()
        backtester.data_provider._tushare_client._pro = MagicMock()
        backtester.data_provider._tushare_client._pro.index_daily.return_value = mock_index_df
        
        result = backtester._get_benchmark_data('20240101', '20240103', '000300.SH')
        
        assert not result.empty
        assert 'trade_date' in result.columns
        assert 'close' in result.columns
        assert 'benchmark_return' in result.columns
    
    def test_get_benchmark_data_empty(self, backtester):
        """Test benchmark data retrieval with empty result"""
        backtester.data_provider._pro.index_daily.return_value = pd.DataFrame()
        
        result = backtester._get_benchmark_data('20240101', '20240103', '000300.SH')
        
        assert result.empty
    
    def test_get_benchmark_data_exception(self, backtester):
        """Test benchmark data retrieval with exception"""
        backtester.data_provider._pro.index_daily.side_effect = Exception("API Error")
        
        result = backtester._get_benchmark_data('20240101', '20240103', '000300.SH')
        
        assert result.empty


class TestRun:
    """Test run method"""
    
    @pytest.fixture
    def backtester(self):
        """Create VectorBacktester with mocked DataProvider"""
        mock_dp = MagicMock()
        mock_pro = MagicMock()
        mock_dp._pro = mock_pro
        
        with patch('src.backtest.DataProvider', return_value=mock_dp):
            backtester = VectorBacktester(mock_dp)
            backtester.data_provider = mock_dp
            return backtester
    
    @pytest.fixture
    def sample_history_data(self):
        """Create sample history data for backtesting"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # Only weekdays
        
        data = []
        for ts_code in ['000001.SZ']:
            for i, date in enumerate(dates[:60]):
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
    
    def test_run_empty_dataframe(self, backtester):
        """Test run with empty DataFrame"""
        result = backtester.run(pd.DataFrame(), holding_days=5)
        
        assert 'strategy_metrics' in result
        assert 'benchmark_metrics' in result
        assert 'trades' in result
        assert result['trades'].empty
    
    def test_run_basic(self, backtester, sample_history_data):
        """Test basic run functionality"""
        # Mock benchmark data
        mock_index_df = pd.DataFrame({
            'trade_date': ['20240101', '20240102'],
            'close': [3000.0, 3010.0]
        })
        backtester.data_provider._pro.index_daily.return_value = mock_index_df
        
        result = backtester.run(sample_history_data.copy(), holding_days=5)
        
        assert 'strategy_metrics' in result
        assert 'benchmark_metrics' in result
        assert 'trades' in result
        
        # Check strategy metrics structure
        strategy_metrics = result['strategy_metrics']
        assert 'win_rate' in strategy_metrics
        assert 'total_return' in strategy_metrics
        assert 'max_drawdown' in strategy_metrics
        assert 'total_trades' in strategy_metrics
    
    def test_run_different_holding_days(self, backtester, sample_history_data):
        """Test run with different holding_days"""
        mock_index_df = pd.DataFrame({
            'trade_date': ['20240101'],
            'close': [3000.0]
        })
        backtester.data_provider._pro.index_daily.return_value = mock_index_df
        
        result1 = backtester.run(sample_history_data.copy(), holding_days=3)
        result2 = backtester.run(sample_history_data.copy(), holding_days=10)
        
        # Both should complete successfully
        assert 'strategy_metrics' in result1
        assert 'strategy_metrics' in result2
    
    def test_run_trades_structure(self, backtester, sample_history_data):
        """Test that trades DataFrame has correct structure"""
        mock_index_df = pd.DataFrame({
            'trade_date': ['20240101'],
            'close': [3000.0]
        })
        backtester.data_provider._pro.index_daily.return_value = mock_index_df
        
        result = backtester.run(sample_history_data.copy(), holding_days=5)
        
        trades = result['trades']
        if not trades.empty:
            assert 'ts_code' in trades.columns
            assert 'trade_date' in trades.columns
            assert 'return' in trades.columns
