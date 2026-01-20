"""
Service Layer Exception Handling Tests
测试Service层异常处理
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from src.services import HunterService, BacktestService, TruthService
from src.exceptions import DataFetchError, StrategyError, FactorError


class TestHunterServiceExceptions:
    """测试HunterService异常处理"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """创建Mock DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def mock_config(self):
        """创建Mock ConfigManager"""
        from src.config_manager import ConfigManager
        return ConfigManager()
    
    def test_hunter_service_data_fetch_error(self, mock_data_provider, mock_config):
        """测试HunterService处理DataFetchError"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        # Mock数据获取失败
        mock_data_provider.get_daily_basic = MagicMock(return_value=pd.DataFrame())
        
        result = service.run_scan(trade_date='20240101')
        
        # 应该返回失败结果，而不是抛出异常
        assert not result.success
        assert result.error is not None
        assert isinstance(result.error, str)
    
    def test_hunter_service_strategy_error(self, mock_data_provider, mock_config):
        """测试HunterService处理StrategyError"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        # Mock数据获取成功，但策略应用失败
        basic_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['测试'],
            'trade_date': ['20240101'],
            'pe_ttm': [15.0],
            'pb': [1.5],
            'mv': [1000000],
            'dividend_yield': [2.0],
            'list_date': ['20200101']
        })
        
        history_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'high': [10.5],
            'low': [9.5],
            'close': [10.2],
            'vol': [1000000]
        })
        
        mock_data_provider.get_daily_basic = MagicMock(return_value=basic_df)
        mock_data_provider.fetch_history_for_hunter = MagicMock(return_value=history_df)
        
        # Mock策略应用失败
        with patch.object(service, '_apply_strategy', side_effect=StrategyError("策略应用失败")):
            result = service.run_scan(trade_date='20240101')
        
        # 应该返回失败结果
        assert not result.success
        assert result.error is not None
    
    def test_hunter_service_factor_error(self, mock_data_provider, mock_config):
        """测试HunterService处理FactorError"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        basic_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'name': ['测试'],
            'trade_date': ['20240101'],
            'pe_ttm': [15.0],
            'pb': [1.5],
            'mv': [1000000],
            'dividend_yield': [2.0],
            'list_date': ['20200101']
        })
        
        history_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'high': [10.5],
            'low': [9.5],
            'close': [10.2],
            'vol': [1000000]
        })
        
        mock_data_provider.get_daily_basic = MagicMock(return_value=basic_df)
        mock_data_provider.fetch_history_for_hunter = MagicMock(return_value=history_df)
        
        # Mock因子计算失败
        with patch.object(service, '_compute_factors', side_effect=FactorError("因子计算失败")):
            result = service.run_scan(trade_date='20240101')
        
        # 应该返回失败结果
        assert not result.success
        assert result.error is not None


class TestBacktestServiceExceptions:
    """测试BacktestService异常处理"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """创建Mock DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def mock_config(self):
        """创建Mock ConfigManager"""
        from src.config_manager import ConfigManager
        return ConfigManager()
    
    def test_backtest_service_data_fetch_error(self, mock_data_provider, mock_config):
        """测试BacktestService处理DataFetchError"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        
        # Mock数据获取失败
        mock_data_provider.fetch_history_batch = MagicMock(return_value=pd.DataFrame())
        
        result = service.run_backtest(
            start_date='20240101',
            end_date='20240301'
        )
        
        # 应该返回失败结果
        assert not result.success
        assert result.error is not None
    
    def test_backtest_service_strategy_error(self, mock_data_provider, mock_config):
        """测试BacktestService处理StrategyError"""
        service = BacktestService(data_provider=mock_data_provider, config=mock_config)
        
        # Mock数据获取成功
        history_df = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'high': [10.5],
            'low': [9.5],
            'close': [10.2],
            'vol': [1000000],
            'pe_ttm': [15.0]
        })
        history_df['trade_date'] = pd.to_datetime(history_df['trade_date'], format='%Y%m%d')
        history_df['trade_date'] = history_df['trade_date'].dt.strftime('%Y%m%d')
        
        mock_data_provider.fetch_history_batch = MagicMock(return_value=history_df)
        mock_data_provider.get_stock_basic = MagicMock(return_value=pd.DataFrame())
        
        # Mock回测执行失败
        with patch('src.services.backtest_service.VectorBacktester') as mock_backtester_class:
            mock_backtester = MagicMock()
            mock_backtester_class.return_value = mock_backtester
            mock_backtester.run.side_effect = StrategyError("回测执行失败")
            
            result = service.run_backtest(
                start_date='20240101',
                end_date='20240301'
            )
        
        # 应该返回失败结果
        assert not result.success
        assert result.error is not None


class TestTruthServiceExceptions:
    """测试TruthService异常处理"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """创建Mock DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def mock_config(self):
        """创建Mock ConfigManager"""
        from src.config_manager import ConfigManager
        return ConfigManager()
    
    def test_truth_service_error_handling(self, mock_data_provider, mock_config):
        """测试TruthService错误处理"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        
        # Mock API调用失败
        mock_data_provider._pro.daily = MagicMock(side_effect=Exception("API Error"))
        
        # 应该能够处理错误并返回结果
        with patch('src.services.truth_service.time.sleep'):
            result = service.update_prices()
        
        # 验证结果结构
        assert hasattr(result, 'success')
        assert hasattr(result, 'updated_count')
        assert hasattr(result, 'total_count')
        assert hasattr(result, 'error')


class TestServiceExceptionPropagation:
    """测试Service异常传播"""
    
    def test_exception_types(self):
        """测试异常类型"""
        # 验证异常类可以实例化
        data_error = DataFetchError("数据获取错误")
        strategy_error = StrategyError("策略错误")
        factor_error = FactorError("因子错误")
        
        assert isinstance(data_error, DataFetchError)
        assert isinstance(strategy_error, StrategyError)
        assert isinstance(factor_error, FactorError)
    
    def test_exception_inheritance(self):
        """测试异常继承关系"""
        from src.exceptions import DAASError
        
        # 验证继承关系
        assert issubclass(DataFetchError, DAASError)
        assert issubclass(StrategyError, DAASError)
        assert issubclass(FactorError, DAASError)
