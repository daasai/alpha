"""
Exception Handling Regression Tests
验证异常体系和Service层异常处理
"""

import pytest
import pandas as pd
from unittest.mock import patch

from src.exceptions import (
    DAASError,
    DataError,
    DataLoaderError,
    DataFetchError,
    DataValidationError,
    APIError,
    StrategyError,
    FactorError,
    ConfigurationError,
    CacheError,
    ValidationError
)


class TestExceptionHierarchy:
    """测试异常类层次结构"""
    
    def test_daas_error_base(self):
        """测试DAASError是基础异常"""
        assert issubclass(DataError, DAASError)
        assert issubclass(StrategyError, DAASError)
        assert issubclass(FactorError, DAASError)
        assert issubclass(ConfigurationError, DAASError)
        assert issubclass(CacheError, DAASError)
    
    def test_data_error_hierarchy(self):
        """测试DataError层次结构"""
        assert issubclass(DataLoaderError, DataError)
        assert issubclass(DataFetchError, DataError)
        assert issubclass(DataValidationError, DataError)
        assert issubclass(APIError, DataError)
    
    def test_validation_error_compatibility(self):
        """测试ValidationError向后兼容"""
        # ValidationError应该是DataValidationError的别名或子类
        assert issubclass(ValidationError, DataValidationError) or \
               ValidationError == DataValidationError
    
    def test_exception_instantiation(self):
        """测试异常可以实例化"""
        # 测试基础异常
        daas_error = DAASError("测试错误")
        assert str(daas_error) == "测试错误"
        
        # 测试数据错误
        data_error = DataError("数据错误")
        assert str(data_error) == "数据错误"
        
        # 测试策略错误
        strategy_error = StrategyError("策略错误")
        assert str(strategy_error) == "策略错误"
        
        # 测试因子错误
        factor_error = FactorError("因子错误")
        assert str(factor_error) == "因子错误"
    
    def test_exception_inheritance(self):
        """测试异常继承关系"""
        # DataFetchError应该是DataError的子类
        assert issubclass(DataFetchError, DataError)
        assert issubclass(DataFetchError, DAASError)
        
        # StrategyError应该是DAASError的子类
        assert issubclass(StrategyError, DAASError)
        
        # FactorError应该是DAASError的子类
        assert issubclass(FactorError, DAASError)


class TestServiceExceptionHandling:
    """测试Service层异常处理"""
    
    def test_hunter_service_data_fetch_error(self):
        """测试HunterService处理DataFetchError"""
        from src.services import HunterService
        from src.exceptions import DataFetchError
        
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = HunterService()
            
            # Mock数据获取失败
            service.data_provider.get_daily_basic = lambda x: pd.DataFrame()
            
            result = service.run_scan(trade_date='20240101')
            
            # 应该返回失败结果
            assert not result.success
            assert result.error is not None
    
    def test_hunter_service_strategy_error(self):
        """测试HunterService处理StrategyError"""
        from src.services import HunterService
        from src.exceptions import StrategyError
        import pandas as pd
        
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = HunterService()
            
            # Mock数据获取成功，但策略失败
            service.data_provider.get_daily_basic = lambda x: pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'name': ['测试'],
                'trade_date': ['20240101'],
                'pe_ttm': [15.0],
                'pb': [1.5],
                'mv': [1000000],
                'dividend_yield': [2.0],
                'list_date': ['20200101']
            })
            
            service.data_provider.fetch_history_for_hunter = lambda **kwargs: pd.DataFrame()
            
            result = service.run_scan(trade_date='20240101')
            
            # 应该处理错误
            assert not result.success or result.error is not None
    
    def test_backtest_service_error_handling(self):
        """测试BacktestService错误处理"""
        from src.services import BacktestService
        from src.exceptions import DataFetchError
        
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = BacktestService()
            
            # Mock数据获取失败
            service.data_provider.fetch_history_batch = lambda **kwargs: pd.DataFrame()
            
            result = service.run_backtest(
                start_date='20240101',
                end_date='20240301'
            )
            
            # 应该返回失败结果
            assert not result.success
            assert result.error is not None
    
    def test_exception_propagation(self):
        """测试异常传播"""
        from src.exceptions import DataFetchError
        
        # 测试异常可以正常抛出和捕获
        try:
            raise DataFetchError("测试数据获取错误")
        except DataFetchError as e:
            assert str(e) == "测试数据获取错误"
        except Exception:
            pytest.fail("应该捕获DataFetchError")
    
    def test_exception_chaining(self):
        """测试异常链"""
        from src.exceptions import DataFetchError
        
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as e:
                raise DataFetchError("数据获取失败") from e
        except DataFetchError as e:
            assert "数据获取失败" in str(e)
            assert e.__cause__ is not None
