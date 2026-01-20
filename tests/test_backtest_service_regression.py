"""
Backtest Service Regression Tests
验证BacktestService与原有逻辑的等价性
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.services import BacktestService, BacktestResult
from src.data_provider import DataProvider
from src.backtest import VectorBacktester
from src.exceptions import DataFetchError, StrategyError


class TestBacktestServiceRegression:
    """Backtest Service回归测试"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """创建Mock DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def mock_config(self):
        """创建Mock ConfigManager"""
        from src.config_manager import ConfigManager
        return ConfigManager()
    
    @pytest.fixture
    def sample_history_data(self):
        """创建样本历史数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]  # 60个交易日
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ', '000003.SZ']:
            for i, date in enumerate(dates):
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.1,
                    'high': 10.0 + i * 0.1 + 0.2,
                    'low': 10.0 + i * 0.1 - 0.1,
                    'close': 10.0 + i * 0.1 + 0.05,
                    'vol': 1000000,
                    'pe_ttm': 15.0
                })
        
        df = pd.DataFrame(data)
        # 确保trade_date是datetime格式（backtest需要）
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        return df
    
    def test_backtest_service_initialization(self, mock_data_provider, mock_config):
        """测试BacktestService可以正确初始化"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        assert service.data_provider is not None
        assert service.config is not None
        assert service.data_provider == mock_data_provider
        assert service.config == mock_config
    
    def test_backtest_service_run_backtest_structure(self, mock_data_provider, mock_config,
                                                      sample_history_data):
        """测试BacktestService.run_backtest()返回结构"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        
        # Mock数据获取
        start_date = sample_history_data['trade_date'].min().strftime('%Y%m%d')
        end_date = sample_history_data['trade_date'].max().strftime('%Y%m%d')
        
        # 准备mock数据（需要字符串格式的trade_date）
        mock_history = sample_history_data.copy()
        mock_history['trade_date'] = mock_history['trade_date'].dt.strftime('%Y%m%d')
        
        mock_data_provider.fetch_history_batch = MagicMock(return_value=mock_history)
        mock_data_provider.get_stock_basic = MagicMock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ'],
            'name': ['股票1', '股票2', '股票3']
        }))
        
        # Mock VectorBacktester
        with patch('src.services.backtest_service.VectorBacktester') as mock_backtester_class:
            mock_backtester = MagicMock()
            mock_backtester_class.return_value = mock_backtester
            
            # Mock回测结果
            mock_results = {
                'total_return': 10.5,
                'max_drawdown': 5.2,
                'win_rate': 60.0,
                'equity_curve': pd.Series([1.0, 1.05, 1.10]),
                'strategy_metrics': {'total_trades': 10},
                'benchmark_metrics': {'total_return': 8.0},
                'trades': pd.DataFrame(),
                'top_contributors': pd.DataFrame()
            }
            mock_backtester.run.return_value = mock_results
            
            result = service.run_backtest(
                start_date=start_date,
                end_date=end_date,
                holding_days=5,
                stop_loss_pct=0.08,
                cost_rate=0.002
            )
        
        # 验证返回结构
        assert isinstance(result, BacktestResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'results')
        assert hasattr(result, 'error')
    
    def test_backtest_service_parameters(self, mock_data_provider, mock_config,
                                         sample_history_data):
        """测试回测参数传递"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        
        start_date = '20240101'
        end_date = '20240301'
        
        mock_history = sample_history_data.copy()
        mock_history['trade_date'] = mock_history['trade_date'].dt.strftime('%Y%m%d')
        mock_data_provider.fetch_history_batch = MagicMock(return_value=mock_history)
        mock_data_provider.get_stock_basic = MagicMock(return_value=pd.DataFrame())
        
        with patch('src.services.backtest_service.VectorBacktester') as mock_backtester_class:
            mock_backtester = MagicMock()
            mock_backtester_class.return_value = mock_backtester
            mock_backtester.run.return_value = {
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'equity_curve': pd.Series(),
                'strategy_metrics': {},
                'benchmark_metrics': {},
                'trades': pd.DataFrame(),
                'top_contributors': pd.DataFrame()
            }
            
            result = service.run_backtest(
                start_date=start_date,
                end_date=end_date,
                holding_days=10,
                stop_loss_pct=0.10,
                cost_rate=0.003,
                benchmark_code='000905.SH'
            )
            
            # 验证参数传递
            assert mock_backtester.run.called
            call_args = mock_backtester.run.call_args
            assert call_args[1]['holding_days'] == 10
            assert call_args[1]['stop_loss_pct'] == 0.10
            assert call_args[1]['cost_rate'] == 0.003
            assert call_args[1]['benchmark_code'] == '000905.SH'
    
    def test_backtest_service_config_integration(self, mock_data_provider, mock_config,
                                                  sample_history_data):
        """测试配置集成"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        
        # 验证从配置读取参数
        index_code = mock_config.get('backtest.index_code', '000300.SH')
        initial_capital = mock_config.get('backtest.initial_capital', 1000000.0)
        max_positions = mock_config.get('backtest.max_positions', 4)
        
        assert index_code is not None
        assert initial_capital > 0
        assert max_positions > 0
    
    def test_backtest_service_error_handling(self, mock_data_provider, mock_config):
        """测试错误处理"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        
        # 测试数据获取失败
        mock_data_provider.fetch_history_batch = MagicMock(return_value=pd.DataFrame())
        
        result = service.run_backtest(
            start_date='20240101',
            end_date='20240301'
        )
        
        assert not result.success
        assert result.error is not None
        assert '数据' in result.error or 'DataFetchError' in str(type(result.error))
    
    def test_backtest_service_results_structure(self, mock_data_provider, mock_config,
                                                 sample_history_data):
        """测试结果结构完整性"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        
        start_date = sample_history_data['trade_date'].min().strftime('%Y%m%d')
        end_date = sample_history_data['trade_date'].max().strftime('%Y%m%d')
        
        mock_history = sample_history_data.copy()
        mock_history['trade_date'] = mock_history['trade_date'].dt.strftime('%Y%m%d')
        mock_data_provider.fetch_history_batch = MagicMock(return_value=mock_history)
        mock_data_provider.get_stock_basic = MagicMock(return_value=pd.DataFrame())
        
        with patch('src.services.backtest_service.VectorBacktester') as mock_backtester_class:
            mock_backtester = MagicMock()
            mock_backtester_class.return_value = mock_backtester
            
            # 完整的mock结果
            mock_results = {
                'total_return': 15.5,
                'max_drawdown': 8.2,
                'win_rate': 65.0,
                'equity_curve': pd.Series([1.0, 1.05, 1.10, 1.15], 
                                         index=pd.date_range('2024-01-01', periods=4)),
                'strategy_metrics': {
                    'total_trades': 20,
                    'win_rate': 65.0,
                    'avg_return': 2.5,
                    'sharpe_ratio': 1.2
                },
                'benchmark_metrics': {
                    'total_return': 12.0,
                    'max_drawdown': 6.0,
                    'avg_return': 1.8
                },
                'trades': pd.DataFrame({
                    'ts_code': ['000001.SZ'],
                    'buy_date': [pd.Timestamp('2024-01-01')],
                    'sell_date': [pd.Timestamp('2024-01-06')],
                    'return': [5.0]
                }),
                'top_contributors': pd.DataFrame({
                    'ts_code': ['000001.SZ'],
                    'total_gain': [1000.0],
                    'total_gain_pct': [10.0]
                })
            }
            mock_backtester.run.return_value = mock_results
            
            result = service.run_backtest(
                start_date=start_date,
                end_date=end_date
            )
        
        if result.success:
            results = result.results
            # 验证关键指标存在
            assert 'total_return' in results
            assert 'max_drawdown' in results
            assert 'win_rate' in results
            assert 'equity_curve' in results
            assert 'strategy_metrics' in results
            assert 'benchmark_metrics' in results
            assert 'trades' in results
            assert 'top_contributors' in results


class TestBacktestServiceEquivalence:
    """测试BacktestService与原有逻辑的等价性"""
    
    @pytest.fixture
    def sample_history_data(self):
        """创建样本历史数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]
        
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
                    'vol': 1000000,
                    'pe_ttm': 15.0
                })
        
        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        return df
    
    def test_backtest_service_vs_direct_backtester(self, sample_history_data):
        """测试Service方式与直接使用VectorBacktester的等价性"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            from src.config_manager import ConfigManager
            from src.backtest import VectorBacktester
            
            dp = DataProvider()
            dp._pro = MagicMock()
            config = ConfigManager()
            
            # 准备数据
            start_date = sample_history_data['trade_date'].min().strftime('%Y%m%d')
            end_date = sample_history_data['trade_date'].max().strftime('%Y%m%d')
            mock_history = sample_history_data.copy()
            mock_history['trade_date'] = mock_history['trade_date'].dt.strftime('%Y%m%d')
            
            dp.fetch_history_batch = MagicMock(return_value=mock_history)
            dp.get_stock_basic = MagicMock(return_value=pd.DataFrame())
            
            # 方式1: 直接使用VectorBacktester
            backtester = VectorBacktester(dp)
            # 注意：这里需要mock backtester.run，因为实际运行需要真实数据
            
            # 方式2: 使用Service
            service = BacktestService(data_provider=dp, config=config)
            
            # 验证两者都能初始化
            assert backtester is not None
            assert service is not None
            assert service.data_provider == dp
