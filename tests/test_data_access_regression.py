"""
Regression Tests for Data Access Layer Refactoring
回归测试：确保重构后功能与之前一致
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


class TestDataAccessRegression:
    """数据访问层回归测试"""
    
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
        """创建 DataProvider 实例"""
        provider = DataProvider(
            tushare_client=mock_tushare_client,
            eastmoney_client=mock_eastmoney_client,
            cache_manager=mock_cache_manager,
            config=mock_config
        )
        return provider
    
    def test_get_stock_basic_regression(self, data_provider, mock_tushare_client, sample_stock_basics):
        """回归测试：get_stock_basic 方法"""
        mock_tushare_client.get_stock_basic.return_value = sample_stock_basics
        
        result = data_provider.get_stock_basic()
        
        # 验证返回类型和结构
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'ts_code' in result.columns
        assert 'name' in result.columns
        
        # 验证调用了正确的客户端
        mock_tushare_client.get_stock_basic.assert_called_once()
    
    def test_get_daily_regression(self, data_provider, mock_tushare_client, mock_cache_manager):
        """回归测试：get_daily 方法"""
        # 缓存未命中
        mock_cache_manager.get_daily_history.return_value = None
        
        sample_daily = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'high': [10.5],
            'low': [9.8],
            'close': [10.2],
            'vol': [1000000],
        })
        mock_tushare_client.get_daily.return_value = sample_daily
        
        result = data_provider.get_daily(ts_code='000001.SZ', trade_date='20240101')
        
        # 验证返回数据
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['ts_code'] == '000001.SZ'
        assert 'close' in result.columns
        
        # 验证缓存逻辑
        mock_cache_manager.get_daily_history.assert_called_once()
        mock_tushare_client.get_daily.assert_called_once()
        mock_cache_manager.save_daily_history.assert_called_once()
    
    def test_get_index_constituents_regression(self, data_provider, mock_tushare_client, mock_cache_manager):
        """回归测试：get_index_constituents 方法"""
        # 缓存未命中
        mock_cache_manager.get_constituents.return_value = None
        
        sample_weights = pd.DataFrame({
            'index_code': ['000300.SH'],
            'con_code': ['000001.SZ', '000002.SZ', '600000.SH'],
            'weight': [0.05, 0.03, 0.02],
        })
        mock_tushare_client.get_index_weight.return_value = sample_weights
        
        result = data_provider.get_index_constituents('000300.SH', '20240101')
        
        # 验证返回类型和内容
        assert isinstance(result, list)
        assert len(result) == 3
        assert '000001.SZ' in result
        assert '000002.SZ' in result
        
        # 验证缓存逻辑
        mock_cache_manager.get_constituents.assert_called_once()
        mock_tushare_client.get_index_weight.assert_called_once()
        mock_cache_manager.save_constituents.assert_called_once()
    
    def test_get_notices_regression(self, data_provider, mock_eastmoney_client, sample_notices):
        """回归测试：get_notices 方法"""
        mock_eastmoney_client.get_notices.return_value = sample_notices
        
        result = data_provider.get_notices(ts_code='000001.SZ')
        
        # 验证返回数据
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert 'ts_code' in result.columns or 'ann_date' in result.columns
        
        # 验证调用了正确的客户端
        mock_eastmoney_client.get_notices.assert_called_once()
    
    def test_get_fina_indicator_regression(self, data_provider, mock_tushare_client, sample_financial_indicators):
        """回归测试：get_fina_indicator 方法"""
        mock_tushare_client.get_fina_indicator.return_value = sample_financial_indicators
        
        result = data_provider.get_fina_indicator(ts_code='000001.SZ')
        
        # 验证返回数据
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        
        # 验证调用了正确的客户端
        mock_tushare_client.get_fina_indicator.assert_called_once()
    
    def test_get_daily_batch_regression(self, data_provider, mock_tushare_client, mock_cache_manager):
        """回归测试：get_daily_batch 方法"""
        # 缓存未命中
        mock_cache_manager.get_daily_history.return_value = None
        
        sample_daily = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': ['20240101', '20240101'],
            'close': [10.0, 20.0],
        })
        mock_tushare_client.get_daily.return_value = sample_daily
        
        result = data_provider.get_daily_batch(['000001.SZ', '000002.SZ'], '20240101')
        
        # 验证返回数据
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        
        # 验证批量处理逻辑
        assert mock_tushare_client.get_daily.called
    
    def test_cache_integration_regression(self, data_provider, mock_cache_manager, mock_tushare_client):
        """回归测试：缓存集成"""
        # 测试缓存命中
        cached_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.0],
        })
        mock_cache_manager.get_daily_history.return_value = cached_data
        
        result = data_provider.get_daily(ts_code='000001.SZ', trade_date='20240101')
        
        # 验证使用缓存数据
        pd.testing.assert_frame_equal(result, cached_data)
        
        # 验证未调用 API
        assert not mock_tushare_client.get_daily.called
    
    def test_error_handling_regression(self, data_provider, mock_tushare_client):
        """回归测试：错误处理"""
        # 测试 API 错误
        mock_tushare_client.get_daily.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            data_provider.get_daily(ts_code='000001.SZ', trade_date='20240101')
        
        # 验证错误被正确传播
        assert mock_tushare_client.get_daily.called
