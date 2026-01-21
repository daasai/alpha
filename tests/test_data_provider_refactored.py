"""
Integration Tests for Refactored DataProvider
测试重构后的 DataProvider（集成测试）
验证 Facade 模式、依赖注入、缓存集成等功能
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.data_provider import DataProvider
from src.api.clients.tushare_client import TushareClient
from src.api.clients.eastmoney_client import EastmoneyClient
from src.cache.cache_manager import CacheManager
from src.config_manager import ConfigManager
from src.exceptions import DataFetchError, CacheError


class TestDataProviderRefactored:
    """测试重构后的 DataProvider"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        config.get = Mock(side_effect=lambda key, default=None: {
            'api_rate_limit.tushare_delay': 0.01,
            'api_rate_limit.max_retries': 3,
            'api_rate_limit.retry_delay': 0.1,
            'api.request_timeout': 10,
            'cache.constituents_ttl_days': 7,
            'cache.daily_history_ttl_days': 30,
        }.get(key, default))
        return config
    
    @pytest.fixture
    def mock_tushare_client(self):
        """Mock TushareClient"""
        client = MagicMock(spec=TushareClient)
        return client
    
    @pytest.fixture
    def mock_eastmoney_client(self):
        """Mock EastmoneyClient"""
        client = MagicMock(spec=EastmoneyClient)
        return client
    
    @pytest.fixture
    def mock_cache_manager(self):
        """Mock CacheManager"""
        manager = MagicMock(spec=CacheManager)
        return manager
    
    @pytest.fixture
    def data_provider(self, mock_config, mock_tushare_client, mock_eastmoney_client, mock_cache_manager):
        """创建 DataProvider 实例（使用依赖注入）"""
        provider = DataProvider(
            tushare_client=mock_tushare_client,
            eastmoney_client=mock_eastmoney_client,
            cache_manager=mock_cache_manager,
            config=mock_config
        )
        return provider
    
    def test_dependency_injection(self, data_provider, mock_tushare_client, mock_eastmoney_client, mock_cache_manager):
        """测试依赖注入"""
        assert data_provider._tushare_client is mock_tushare_client
        assert data_provider._eastmoney_client is mock_eastmoney_client
        assert data_provider._cache_manager is mock_cache_manager
    
    def test_get_stock_basic_facade(self, data_provider, mock_tushare_client, sample_stock_basics):
        """测试 Facade 模式：获取股票基础信息"""
        mock_tushare_client.get_stock_basic.return_value = sample_stock_basics
        
        result = data_provider.get_stock_basic()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_stock_basics)
        mock_tushare_client.get_stock_basic.assert_called_once()
    
    def test_get_daily_with_cache(self, data_provider, mock_tushare_client, mock_cache_manager):
        """测试获取日线数据（带缓存）"""
        # 缓存未命中
        mock_cache_manager.get_daily_history.return_value = None
        
        sample_daily = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.0],
        })
        mock_tushare_client.get_daily.return_value = sample_daily
        
        result = data_provider.get_daily(ts_code='000001.SZ', trade_date='20240101')
        
        assert isinstance(result, pd.DataFrame)
        # 应该调用 API
        mock_tushare_client.get_daily.assert_called_once()
        # 应该保存到缓存
        mock_cache_manager.save_daily_history.assert_called_once()
    
    def test_get_daily_cache_hit(self, data_provider, mock_cache_manager):
        """测试获取日线数据（缓存命中）"""
        cached_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.0],
        })
        mock_cache_manager.get_daily_history.return_value = cached_data
        
        result = data_provider.get_daily(ts_code='000001.SZ', trade_date='20240101')
        
        assert isinstance(result, pd.DataFrame)
        pd.testing.assert_frame_equal(result, cached_data)
        # 不应该调用 API
        assert not hasattr(data_provider._tushare_client, 'get_daily') or \
               not data_provider._tushare_client.get_daily.called
    
    def test_get_constituents_with_cache(self, data_provider, mock_tushare_client, mock_cache_manager):
        """测试获取成分股（带缓存）"""
        # 缓存未命中
        mock_cache_manager.get_constituents.return_value = None
        
        sample_weights = pd.DataFrame({
            'index_code': ['000300.SH'],
            'con_code': ['000001.SZ', '000002.SZ'],
            'weight': [0.05, 0.03],
        })
        mock_tushare_client.get_index_weight.return_value = sample_weights
        
        result = data_provider.get_index_constituents('000300.SH', '20240101')
        
        assert isinstance(result, list)
        assert len(result) == 2
        # 应该调用 API
        mock_tushare_client.get_index_weight.assert_called_once()
        # 应该保存到缓存
        mock_cache_manager.save_constituents.assert_called_once()
    
    def test_get_notices_facade(self, data_provider, mock_eastmoney_client, sample_notices):
        """测试 Facade 模式：获取公告"""
        mock_eastmoney_client.get_notices.return_value = sample_notices
        
        result = data_provider.get_notices(ts_code='000001.SZ')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_notices)
        mock_eastmoney_client.get_notices.assert_called_once()
    
    def test_error_propagation(self, data_provider, mock_tushare_client):
        """测试错误传播"""
        mock_tushare_client.get_daily.side_effect = DataFetchError("API Error")
        
        with pytest.raises(DataFetchError, match="API Error"):
            data_provider.get_daily(ts_code='000001.SZ', trade_date='20240101')
    
    def test_cache_error_handling(self, data_provider, mock_cache_manager, mock_tushare_client):
        """测试缓存错误处理"""
        # 缓存抛出错误
        mock_cache_manager.get_daily_history.side_effect = CacheError("Cache error")
        # API 正常
        sample_daily = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.0],
        })
        mock_tushare_client.get_daily.return_value = sample_daily
        
        # 应该降级到 API 调用
        result = data_provider.get_daily(ts_code='000001.SZ', trade_date='20240101')
        
        assert isinstance(result, pd.DataFrame)
        mock_tushare_client.get_daily.assert_called_once()
    
    def test_batch_operations(self, data_provider, mock_tushare_client):
        """测试批量操作"""
        sample_daily = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': ['20240101', '20240101'],
            'close': [10.0, 20.0],
        })
        mock_tushare_client.get_daily.return_value = sample_daily
        
        result = data_provider.get_daily_batch(['000001.SZ', '000002.SZ'], '20240101')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        # 应该使用批量方法
        assert mock_tushare_client.get_daily.called


class TestDataProviderBackwardCompatibility:
    """测试 DataProvider 向后兼容性"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        config.get = Mock(side_effect=lambda key, default=None: {
            'api_rate_limit.tushare_delay': 0.01,
            'api_rate_limit.max_retries': 3,
            'api_rate_limit.retry_delay': 0.1,
            'api.request_timeout': 10,
        }.get(key, default))
        return config
    
    def test_auto_initialization(self, mock_config):
        """测试自动初始化（无依赖注入时）"""
        with patch('src.data_provider.TushareClient') as mock_tushare_class, \
             patch('src.data_provider.EastmoneyClient') as mock_eastmoney_class, \
             patch('src.data_provider.CacheManager') as mock_cache_class:
            
            mock_tushare_class.return_value = MagicMock()
            mock_eastmoney_class.return_value = MagicMock()
            mock_cache_class.return_value = MagicMock()
            
            provider = DataProvider(config=mock_config)
            
            # 应该自动创建依赖
            mock_tushare_class.assert_called_once()
            mock_eastmoney_class.assert_called_once()
            mock_cache_class.assert_called_once()
    
    def test_api_methods_still_work(self, mock_config):
        """测试原有 API 方法仍然可用"""
        with patch('src.data_provider.TushareClient') as mock_tushare_class, \
             patch('src.data_provider.EastmoneyClient'), \
             patch('src.data_provider.CacheManager'):
            
            mock_client = MagicMock()
            mock_client.get_stock_basic.return_value = pd.DataFrame()
            mock_tushare_class.return_value = mock_client
            
            provider = DataProvider(config=mock_config)
            result = provider.get_stock_basic()
            
            assert isinstance(result, pd.DataFrame)
            mock_client.get_stock_basic.assert_called_once()
