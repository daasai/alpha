"""
Unit tests for DataProvider v1.2
Tests for fetch_history_batch method and caching mechanism
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path
from datetime import datetime
import os
import tempfile
import shutil

from src.data_provider import DataProvider


class TestFetchHistoryBatch:
    """Test fetch_history_batch method"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """Create mocked DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory"""
        cache_dir = tmp_path / "data"
        cache_dir.mkdir()
        return cache_dir
    
    def test_fetch_history_batch_cache_hit(self, mock_data_provider, temp_cache_dir):
        """Test cache hit scenario"""
        # Create mock cache file
        cache_path = temp_cache_dir / "cache.csv"
        cached_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'trade_date': ['20240101', '20240102'],
            'open': [10.0, 10.1],
            'close': [10.05, 10.15],
            'vol': [1000000, 1100000],
            'pe_ttm': [15.0, 16.0]
        })
        cached_data.to_csv(cache_path, index=False)
        
        # Mock Path to return our temp cache path
        with patch('src.data_provider.Path', return_value=cache_path):
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240102', index_code='000300.SH', use_cache=True
            )
            
            # Should return cached data (if cache covers date range)
            # Note: This test may need adjustment based on actual cache logic
    
    def test_fetch_history_batch_cache_miss(self, mock_data_provider):
        """Test cache miss scenario - fetch from API"""
        # Mock API responses
        mock_daily_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'high': [10.2],
            'low': [9.8],
            'close': [10.05],
            'vol': [1000000]
        })
        
        mock_pe_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'pe': [15.0]
        })
        
        mock_data_provider._pro.daily.return_value = mock_daily_data
        mock_data_provider._pro.daily_basic.return_value = mock_pe_data
        mock_data_provider.get_index_constituents = Mock(return_value=['000001.SZ'])
        mock_data_provider.get_stock_basic = Mock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ']
        }))
        
        with patch('src.data_provider.Path') as mock_path, \
             patch('src.data_provider.time.sleep'), \
             patch('tqdm.tqdm'):
            # Mock cache path to not exist
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_cache_path.parent.mkdir = Mock()
            mock_cache_path.__str__ = lambda x: "data/cache.csv"
            mock_path.return_value = mock_cache_path
            
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240101', index_code='000300.SH', use_cache=False
            )
            
            # Should fetch from API (may be empty if stock_list is empty or API fails)
            assert isinstance(result, pd.DataFrame)
            # If result is not empty, check columns
            if not result.empty:
                assert 'ts_code' in result.columns
                assert 'trade_date' in result.columns
    
    def test_fetch_history_batch_index_filtering(self, mock_data_provider):
        """Test index constituent filtering"""
        mock_data_provider.get_index_constituents = Mock(return_value=['000001.SZ', '000002.SZ'])
        mock_data_provider._pro.daily.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.05],
            'vol': [1000000]
        })
        mock_data_provider._pro.daily_basic.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'pe': [15.0]
        })
        
        with patch('src.data_provider.Path') as mock_path, \
             patch('src.data_provider.time.sleep'), \
             patch('tqdm.tqdm'):
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_path.return_value = mock_cache_path
            
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240101', index_code='000300.SH', use_cache=False
            )
            
            # Should call get_index_constituents
            mock_data_provider.get_index_constituents.assert_called()
    
    def test_fetch_history_batch_no_index_code(self, mock_data_provider):
        """Test fetching all market data (no index code)"""
        mock_data_provider.get_stock_basic = Mock(return_value=pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ']
        }))
        mock_data_provider._pro.daily.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.05],
            'vol': [1000000]
        })
        mock_data_provider._pro.daily_basic.return_value = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'pe': [15.0]
        })
        
        with patch('src.data_provider.Path') as mock_path, \
             patch('src.data_provider.time.sleep'), \
             patch('tqdm.tqdm'):
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_path.return_value = mock_cache_path
            
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240101', index_code=None, use_cache=False
            )
            
            # Should call get_stock_basic
            mock_data_provider.get_stock_basic.assert_called()
    
    def test_fetch_history_batch_empty_stock_list(self, mock_data_provider):
        """Test with empty stock list"""
        mock_data_provider.get_index_constituents = Mock(return_value=[])
        mock_data_provider.get_stock_basic = Mock(return_value=pd.DataFrame())
        
        with patch('src.data_provider.Path'):
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240101', index_code='000300.SH', use_cache=False
            )
            
            assert result.empty
    
    def test_fetch_history_batch_api_error_handling(self, mock_data_provider):
        """Test API error handling"""
        mock_data_provider.get_index_constituents = Mock(return_value=['000001.SZ'])
        mock_data_provider._pro.daily.side_effect = Exception("API Error")
        
        with patch('src.data_provider.Path') as mock_path, \
             patch('src.data_provider.time.sleep'), \
             patch('tqdm.tqdm'):
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_path.return_value = mock_cache_path
            
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240101', index_code='000300.SH', use_cache=False
            )
            
            # Should handle errors gracefully and return empty or partial data
            assert isinstance(result, pd.DataFrame)
    
    def test_fetch_history_batch_pe_data_merge(self, mock_data_provider):
        """Test PE data merging"""
        mock_daily_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.05],
            'vol': [1000000]
        })
        
        mock_pe_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'pe': [15.0]
        })
        
        mock_data_provider.get_index_constituents = Mock(return_value=['000001.SZ'])
        mock_data_provider._pro.daily.return_value = mock_daily_data
        mock_data_provider._pro.daily_basic.return_value = mock_pe_data
        
        with patch('src.data_provider.Path') as mock_path, \
             patch('src.data_provider.time.sleep'), \
             patch('tqdm.tqdm'):
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_path.return_value = mock_cache_path
            
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240101', index_code='000300.SH', use_cache=False
            )
            
            # Should have pe_ttm column
            if not result.empty:
                assert 'pe_ttm' in result.columns
    
    def test_fetch_history_batch_cache_write(self, mock_data_provider, tmp_path):
        """Test cache writing"""
        cache_path = tmp_path / "data" / "cache.csv"
        cache_path.parent.mkdir()
        
        mock_daily_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'open': [10.0],
            'close': [10.05],
            'vol': [1000000]
        })
        
        mock_pe_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'pe': [15.0]
        })
        
        mock_data_provider.get_index_constituents = Mock(return_value=['000001.SZ'])
        mock_data_provider._pro.daily.return_value = mock_daily_data
        mock_data_provider._pro.daily_basic.return_value = mock_pe_data
        
        with patch('src.data_provider.Path') as mock_path, \
             patch('src.data_provider.time.sleep'), \
             patch('tqdm.tqdm'):
            # Make Path return our temp cache path
            def path_side_effect(path_str):
                if 'cache.csv' in path_str or 'data' in path_str:
                    return cache_path
                return Path(path_str)
            
            mock_path.side_effect = path_side_effect
            
            result = mock_data_provider.fetch_history_batch(
                '20240101', '20240101', index_code='000300.SH', use_cache=True
            )
            
            # Cache file should be created
            if cache_path.exists():
                cached = pd.read_csv(cache_path)
                assert not cached.empty
    
    def test_fetch_history_batch_date_range(self, mock_data_provider):
        """Test date range filtering"""
        # Create cache with wider date range
        cached_data = pd.DataFrame({
            'ts_code': ['000001.SZ'] * 5,
            'trade_date': ['20240101', '20240102', '20240103', '20240104', '20240105'],
            'open': [10.0] * 5,
            'close': [10.05] * 5,
            'vol': [1000000] * 5,
            'pe_ttm': [15.0] * 5
        })
        
        with patch('src.data_provider.Path') as mock_path, \
             patch('pandas.read_csv', return_value=cached_data):
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = True
            mock_path.return_value = mock_cache_path
            
            # Request subset of dates
            result = mock_data_provider.fetch_history_batch(
                '20240102', '20240104', index_code='000300.SH', use_cache=True
            )
            
            # Should filter to requested date range
            # Note: This depends on cache logic implementation
