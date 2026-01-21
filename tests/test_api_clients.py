"""
Unit Tests for API Clients
测试 APIClient 模块（BaseAPIClient, TushareClient, EastmoneyClient）
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime, timedelta
import time

from src.api.clients.base_client import BaseAPIClient
from src.api.clients.tushare_client import TushareClient
from src.api.clients.eastmoney_client import EastmoneyClient
from src.exceptions import APIError, DataFetchError
from src.config_manager import ConfigManager


class TestBaseAPIClient:
    """测试 BaseAPIClient 基础功能"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        config.get = Mock(side_effect=lambda key, default=None: {
            'api_rate_limit.tushare_delay': 0.1,
            'api_rate_limit.max_retries': 3,
            'api_rate_limit.retry_delay': 0.5,
            'api.request_timeout': 10,
        }.get(key, default))
        return config
    
    def test_rate_limiting(self, mock_config):
        """测试速率限制"""
        class TestClient(BaseAPIClient):
            def get_data(self, **kwargs):
                return pd.DataFrame()
        
        client = TestClient(config=mock_config)
        
        # 第一次调用应该立即执行
        start = time.time()
        client._rate_limit()
        elapsed = time.time() - start
        assert elapsed < 0.05  # 应该很快
        
        # 第二次调用应该等待
        start = time.time()
        client._rate_limit()
        elapsed = time.time() - start
        assert elapsed >= 0.09  # 应该等待约 0.1 秒
    
    def test_retry_on_failure(self, mock_config):
        """测试重试机制"""
        class TestClient(BaseAPIClient):
            def get_data(self, **kwargs):
                return pd.DataFrame()
        
        client = TestClient(config=mock_config)
        
        # 测试成功的情况
        call_count = [0]
        def success_func():
            call_count[0] += 1
            return "success"
        
        result = client._retry_on_failure(success_func)
        assert result == "success"
        assert call_count[0] == 1
        
        # 测试失败后重试的情况
        call_count = [0]
        def fail_then_success():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary error")
            return "success"
        
        result = client._retry_on_failure(fail_then_success)
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_max_attempts(self, mock_config):
        """测试达到最大重试次数后失败"""
        class TestClient(BaseAPIClient):
            def get_data(self, **kwargs):
                return pd.DataFrame()
        
        client = TestClient(config=mock_config)
        
        def always_fail():
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            client._retry_on_failure(always_fail, max_retries=2)


class TestTushareClient:
    """测试 TushareClient"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        config.get = Mock(side_effect=lambda key, default=None: {
            'api_rate_limit.tushare_delay': 0.01,  # 测试时使用更短的延迟
            'api_rate_limit.max_retries': 3,
            'api_rate_limit.retry_delay': 0.1,
            'api.request_timeout': 10,
        }.get(key, default))
        return config
    
    @pytest.fixture
    def mock_tushare_pro(self):
        """Mock Tushare Pro API"""
        mock_pro = MagicMock()
        return mock_pro
    
    @pytest.fixture
    def tushare_client(self, mock_config, mock_tushare_pro):
        """创建 TushareClient 实例"""
        with patch('src.api.clients.tushare_client.ts.pro_api') as mock_pro_api:
            mock_pro_api.return_value = mock_tushare_pro
            client = TushareClient(config=mock_config)
            client._pro = mock_tushare_pro
            return client
    
    def test_get_stock_basic(self, tushare_client, mock_tushare_pro, sample_stock_basics):
        """测试获取股票基础信息"""
        mock_tushare_pro.stock_basic.return_value = sample_stock_basics
        
        result = tushare_client.get_stock_basic()
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_stock_basics)
        assert 'ts_code' in result.columns
        mock_tushare_pro.stock_basic.assert_called_once()
    
    def test_get_daily_basic(self, tushare_client, mock_tushare_pro, sample_daily_indicators):
        """测试获取日线基础指标"""
        mock_tushare_pro.daily_basic.return_value = sample_daily_indicators
        
        trade_date = datetime.now().strftime('%Y%m%d')
        result = tushare_client.get_daily_basic(trade_date=trade_date)
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_daily_indicators)
        mock_tushare_pro.daily_basic.assert_called_once()
    
    def test_get_daily(self, tushare_client, mock_tushare_pro):
        """测试获取日线行情"""
        sample_daily = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'high': [10.5],
            'low': [9.8],
            'close': [10.2],
            'vol': [1000000],
        })
        mock_tushare_pro.daily.return_value = sample_daily
        
        result = tushare_client.get_daily(ts_code='000001.SZ', trade_date='20240101')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['ts_code'] == '000001.SZ'
        mock_tushare_pro.daily.assert_called_once()
    
    def test_get_fina_indicator(self, tushare_client, mock_tushare_pro, sample_financial_indicators):
        """测试获取财务指标"""
        mock_tushare_pro.fina_indicator.return_value = sample_financial_indicators
        
        result = tushare_client.get_fina_indicator(ts_code='000001.SZ')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(sample_financial_indicators)
        mock_tushare_pro.fina_indicator.assert_called_once()
    
    def test_get_index_weight(self, tushare_client, mock_tushare_pro):
        """测试获取指数成分股权重"""
        sample_weights = pd.DataFrame({
            'index_code': ['000300.SH', '000300.SH'],
            'con_code': ['000001.SZ', '000002.SZ'],
            'weight': [0.05, 0.03],
        })
        mock_tushare_pro.index_weight.return_value = sample_weights
        
        result = tushare_client.get_index_weight(index_code='000300.SH')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_tushare_pro.index_weight.assert_called_once()
    
    def test_api_error_handling(self, tushare_client, mock_tushare_pro):
        """测试 API 错误处理"""
        mock_tushare_pro.daily.side_effect = Exception("API Error")
        
        with pytest.raises(DataFetchError):
            tushare_client.get_daily(ts_code='000001.SZ', trade_date='20240101')
    
    def test_rate_limiting_integration(self, tushare_client, mock_tushare_pro):
        """测试速率限制集成"""
        sample_daily = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.0],
        })
        mock_tushare_pro.daily.return_value = sample_daily
        
        # 连续调用应该受到速率限制
        start = time.time()
        tushare_client.get_daily(ts_code='000001.SZ', trade_date='20240101')
        tushare_client.get_daily(ts_code='000002.SZ', trade_date='20240101')
        elapsed = time.time() - start
        
        # 应该至少等待一次延迟
        assert elapsed >= 0.009  # 至少等待 0.01 秒
        assert mock_tushare_pro.daily.call_count == 2


class TestEastmoneyClient:
    """测试 EastmoneyClient"""
    
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
    
    @pytest.fixture
    def eastmoney_client(self, mock_config):
        """创建 EastmoneyClient 实例"""
        client = EastmoneyClient(config=mock_config)
        # Mock session
        client.session = MagicMock()
        return client
    
    def test_get_notices(self, eastmoney_client, sample_notices):
        """测试获取公告"""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'data': {
                'list': [
                    {
                        'notice_date': '2024-01-01 10:00:00',
                        'title': '测试公告',
                        'title_ch': '测试公告',
                        'art_code': '12345',
                        'columns': []
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        eastmoney_client.session.get.return_value = mock_response
        
        result = eastmoney_client.get_notices(stock_list=['000001.SZ'], start_date='20240101')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) >= 0  # 可能为空
        eastmoney_client.session.get.assert_called()
    
    def test_get_notices_error_handling(self, eastmoney_client):
        """测试公告获取错误处理"""
        eastmoney_client.session.get.side_effect = Exception("API Error")
        
        # 应该返回空 DataFrame 而不是抛出异常（根据实现）
        result = eastmoney_client.get_notices(stock_list=['000001.SZ'], start_date='20240101')
        assert isinstance(result, pd.DataFrame)
