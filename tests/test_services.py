"""
Service Layer Functional Tests
测试Service层基础功能：初始化、依赖注入、配置读取
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services import (
    BaseService,
    HunterService,
    BacktestService,
    TruthService
)
from src.config_manager import ConfigManager
from src.data_provider import DataProvider


class TestBaseService:
    """测试BaseService基础功能"""
    
    def test_base_service_initialization(self):
        """测试BaseService可以正确初始化"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = BaseService()
            assert service.data_provider is not None
            assert service.config is not None
            assert isinstance(service.data_provider, DataProvider)
            assert isinstance(service.config, ConfigManager)
    
    def test_base_service_dependency_injection(self):
        """测试依赖注入功能"""
        mock_dp = MagicMock()
        mock_config = MagicMock()
        
        service = BaseService(data_provider=mock_dp, config=mock_config)
        
        assert service.data_provider == mock_dp
        assert service.config == mock_config
    
    def test_base_service_partial_injection(self):
        """测试部分依赖注入（只注入一个依赖）"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            mock_config = MagicMock()
            
            service = BaseService(config=mock_config)
            
            assert service.config == mock_config
            assert service.data_provider is not None
            assert isinstance(service.data_provider, DataProvider)


class TestHunterService:
    """测试HunterService功能"""
    
    def test_hunter_service_initialization(self):
        """测试HunterService可以正确初始化"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = HunterService()
            assert service.data_provider is not None
            assert service.config is not None
    
    def test_hunter_service_with_dependency_injection(self):
        """测试依赖注入功能"""
        mock_dp = MagicMock()
        mock_config = MagicMock()
        
        service = HunterService(data_provider=mock_dp, config=mock_config)
        
        assert service.data_provider == mock_dp
        assert service.config == mock_config
    
    def test_hunter_service_config_usage(self):
        """测试配置使用"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = HunterService()
            
            # 验证可以访问配置
            history_days = service.config.get('hunter.history_days', 120)
            assert history_days > 0


class TestBacktestService:
    """测试BacktestService功能"""
    
    def test_backtest_service_initialization(self):
        """测试BacktestService可以正确初始化"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = BacktestService()
            assert service.data_provider is not None
            assert service.config is not None
    
    def test_backtest_service_with_dependency_injection(self):
        """测试依赖注入功能"""
        mock_dp = MagicMock()
        mock_config = MagicMock()
        
        service = BacktestService(data_provider=mock_dp, config=mock_config)
        
        assert service.data_provider == mock_dp
        assert service.config == mock_config
    
    def test_backtest_service_config_usage(self):
        """测试配置使用"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = BacktestService()
            
            # 验证可以访问配置
            index_code = service.config.get('backtest.index_code', '000300.SH')
            assert index_code is not None


class TestTruthService:
    """测试TruthService功能"""
    
    def test_truth_service_initialization(self):
        """测试TruthService可以正确初始化"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = TruthService()
            assert service.data_provider is not None
            assert service.config is not None
    
    def test_truth_service_with_dependency_injection(self):
        """测试依赖注入功能"""
        mock_dp = MagicMock()
        mock_config = MagicMock()
        
        service = TruthService(data_provider=mock_dp, config=mock_config)
        
        assert service.data_provider == mock_dp
        assert service.config == mock_config
    
    def test_truth_service_config_usage(self):
        """测试配置使用"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = TruthService()
            
            # 验证可以访问配置
            api_delay = service.config.get('api_rate_limit.tushare_delay', 0.1)
            assert api_delay > 0


class TestServiceIsolation:
    """测试Service之间的隔离性"""
    
    def test_services_independent(self):
        """测试不同Service实例相互独立"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            hunter_service = HunterService()
            backtest_service = BacktestService()
            truth_service = TruthService()
            
            # 验证它们是不同的实例
            assert hunter_service is not backtest_service
            assert hunter_service is not truth_service
            assert backtest_service is not truth_service
            
            # 验证它们都有独立的配置和数据提供者
            assert hunter_service.config is not None
            assert backtest_service.config is not None
            assert truth_service.config is not None
