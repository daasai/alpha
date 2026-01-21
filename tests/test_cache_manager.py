"""
Unit Tests for CacheManager
测试缓存管理模块
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.cache.cache_manager import CacheManager
from src.cache.cache_strategy import DatabaseCacheStrategy
from src.config_manager import ConfigManager
from src.exceptions import CacheError


class TestCacheManager:
    """测试 CacheManager"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock ConfigManager"""
        config = MagicMock(spec=ConfigManager)
        config.get = Mock(side_effect=lambda key, default=None: {
            'cache.constituents_ttl_days': 7,
            'cache.daily_history_ttl_days': 30,
        }.get(key, default))
        return config
    
    @pytest.fixture
    def mock_strategy(self):
        """Mock CacheStrategy"""
        strategy = MagicMock(spec=DatabaseCacheStrategy)
        return strategy
    
    @pytest.fixture
    def cache_manager(self, mock_config, mock_strategy):
        """创建 CacheManager 实例"""
        with patch('src.cache.cache_manager.DatabaseCacheStrategy') as mock_strategy_class:
            mock_strategy_class.return_value = mock_strategy
            manager = CacheManager(config=mock_config)
            manager._strategy = mock_strategy
            return manager
    
    def test_get_constituents_cache_hit(self, cache_manager, mock_strategy):
        """测试获取成分股缓存命中"""
        cached_data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'weight': [0.05, 0.03],
        })
        mock_strategy.get.return_value = cached_data
        
        result = cache_manager.get_constituents('000300.SH', '20240101')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_strategy.get.assert_called_once()
    
    def test_get_constituents_cache_miss(self, cache_manager, mock_strategy):
        """测试获取成分股缓存未命中"""
        mock_strategy.get.return_value = None
        
        result = cache_manager.get_constituents('000300.SH', '20240101')
        
        assert result is None
        mock_strategy.get.assert_called_once()
    
    def test_save_constituents(self, cache_manager, mock_strategy):
        """测试保存成分股"""
        data = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ'],
            'weight': [0.05, 0.03],
        })
        
        cache_manager.save_constituents('000300.SH', '20240101', data)
        
        mock_strategy.set.assert_called_once()
        call_args = mock_strategy.set.call_args
        assert call_args[0][0] == 'constituents:000300.SH:20240101'
        pd.testing.assert_frame_equal(call_args[0][1], data)
    
    def test_get_daily_history_cache_hit(self, cache_manager, mock_strategy):
        """测试获取日线历史缓存命中"""
        cached_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101', '20240102'],
            'close': [10.0, 10.1],
        })
        mock_strategy.get.return_value = cached_data
        
        result = cache_manager.get_daily_history('000001.SZ', '20240101', '20240102')
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_strategy.get.assert_called_once()
    
    def test_save_daily_history(self, cache_manager, mock_strategy):
        """测试保存日线历史"""
        data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.0],
        })
        
        cache_manager.save_daily_history('000001.SZ', data)
        
        mock_strategy.set.assert_called_once()
        call_args = mock_strategy.set.call_args
        assert 'daily_history:000001.SZ' in call_args[0][0]
        pd.testing.assert_frame_equal(call_args[0][1], data)
    
    def test_invalidate_constituents(self, cache_manager, mock_strategy):
        """测试失效成分股缓存"""
        cache_manager.invalidate_constituents('000300.SH')
        
        mock_strategy.invalidate.assert_called_once()
        call_args = mock_strategy.invalidate.call_args
        assert 'constituents:000300.SH' in call_args[0][0]
    
    def test_invalidate_daily_history(self, cache_manager, mock_strategy):
        """测试失效日线历史缓存"""
        cache_manager.invalidate_daily_history('000001.SZ')
        
        mock_strategy.invalidate.assert_called_once()
        call_args = mock_strategy.invalidate.call_args
        assert 'daily_history:000001.SZ' in call_args[0][0]
    
    def test_cache_error_handling(self, cache_manager, mock_strategy):
        """测试缓存错误处理"""
        mock_strategy.get.side_effect = Exception("Cache error")
        
        with pytest.raises(CacheError):
            cache_manager.get_constituents('000300.SH', '20240101')


class TestDatabaseCacheStrategy:
    """测试 DatabaseCacheStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """创建 DatabaseCacheStrategy 实例"""
        with patch('src.cache.cache_strategy.get_cached_constituents'), \
             patch('src.cache.cache_strategy.save_constituents'), \
             patch('src.cache.cache_strategy.get_cached_daily_history'), \
             patch('src.cache.cache_strategy.save_daily_history_batch'):
            strategy = DatabaseCacheStrategy()
            return strategy
    
    def test_get_constituents(self, strategy):
        """测试从数据库获取成分股"""
        with patch.object(strategy, '_get_cached_constituents') as mock_get:
            mock_get.return_value = ['000001.SZ', '000002.SZ']
            
            result = strategy.get('constituents:000300.SH:20240101')
            
            assert result is not None
            assert isinstance(result, list) or isinstance(result, pd.DataFrame)
            mock_get.assert_called_once()
    
    def test_set_constituents(self, strategy):
        """测试保存成分股到数据库"""
        data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'weight': [0.05],
        })
        
        with patch.object(strategy, '_save_constituents') as mock_save:
            strategy.set('constituents:000300.SH:20240101', data)
            
            mock_save.assert_called_once()
    
    def test_get_daily_history(self, strategy):
        """测试从数据库获取日线历史"""
        with patch.object(strategy, '_get_cached_daily_history') as mock_get:
            cached_data = pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'trade_date': ['20240101'],
                'close': [10.0],
            })
            mock_get.return_value = cached_data
            
            result = strategy.get('daily_history:000001.SZ:20240101:20240102')
            
            assert result is not None
            assert isinstance(result, pd.DataFrame)
            mock_get.assert_called_once()
    
    def test_set_daily_history(self, strategy):
        """测试保存日线历史到数据库"""
        data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [10.0],
        })
        
        with patch.object(strategy, '_save_daily_history_batch') as mock_save:
            strategy.set('daily_history:000001.SZ', data)
            
            mock_save.assert_called_once()
    
    def test_invalidate(self, strategy):
        """测试失效缓存"""
        with patch.object(strategy, '_clear_old_constituents') as mock_clear_constituents, \
             patch.object(strategy, '_clear_old_daily_history') as mock_clear_history:
            
            # 失效成分股缓存
            strategy.invalidate('constituents:000300.SH')
            mock_clear_constituents.assert_called_once()
            
            # 失效日线历史缓存
            strategy.invalidate('daily_history:000001.SZ')
            mock_clear_history.assert_called_once()
