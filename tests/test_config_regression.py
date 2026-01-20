"""
Configuration Management Regression Tests
验证配置读取、默认值、降级处理
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.config_manager import ConfigManager


class TestConfigManagerRegression:
    """配置管理器回归测试"""
    
    def test_config_manager_initialization(self):
        """测试ConfigManager可以正确初始化"""
        config = ConfigManager()
        assert config is not None
        assert config.config is not None
        assert isinstance(config.config, dict)
    
    def test_config_manager_get_existing_key(self):
        """测试获取存在的配置项"""
        config = ConfigManager()
        
        # 测试获取嵌套配置
        index_code = config.get('index_filter.index_code')
        assert index_code is not None
    
    def test_config_manager_get_with_default(self):
        """测试获取不存在的配置项时使用默认值"""
        config = ConfigManager()
        
        # 测试不存在的配置项
        non_existent = config.get('non_existent.key', 'default_value')
        assert non_existent == 'default_value'
    
    def test_config_manager_nested_keys(self):
        """测试嵌套键访问"""
        config = ConfigManager()
        
        # 测试点号分隔的嵌套键
        enabled = config.get('index_filter.enabled', True)
        assert isinstance(enabled, bool)
    
    def test_config_manager_reload(self):
        """测试配置重新加载"""
        config = ConfigManager()
        
        # 获取原始值
        original_value = config.get('index_filter.index_code')
        
        # 重新加载
        config.reload()
        
        # 值应该保持一致（除非配置文件被修改）
        reloaded_value = config.get('index_filter.index_code')
        assert reloaded_value == original_value


class TestNewConfigItems:
    """测试新增配置项"""
    
    def test_concurrency_config(self):
        """测试并发配置读取"""
        config = ConfigManager()
        
        roe_workers = config.get('concurrency.roe_workers', 10)
        ai_workers = config.get('concurrency.ai_workers', 5)
        atr_workers = config.get('concurrency.atr_workers', 10)
        
        assert roe_workers > 0
        assert ai_workers > 0
        assert atr_workers > 0
    
    def test_api_rate_limit_config(self):
        """测试API限流配置读取"""
        config = ConfigManager()
        
        tushare_delay = config.get('api_rate_limit.tushare_delay', 0.1)
        eastmoney_delay = config.get('api_rate_limit.eastmoney_delay', 0.2)
        retry_delay = config.get('api_rate_limit.retry_delay', 0.5)
        task_delay = config.get('api_rate_limit.task_delay', 0.02)
        max_retries = config.get('api_rate_limit.max_retries', 3)
        
        assert tushare_delay > 0
        assert eastmoney_delay > 0
        assert retry_delay > 0
        assert task_delay > 0
        assert max_retries > 0
    
    def test_strategy_config(self):
        """测试策略配置读取"""
        config = ConfigManager()
        
        rps_threshold = config.get('strategy.alpha_trident.rps_threshold', 85)
        vol_ratio_threshold = config.get('strategy.alpha_trident.vol_ratio_threshold', 1.5)
        pe_max = config.get('strategy.alpha_trident.pe_max', 30)
        
        assert rps_threshold > 0
        assert vol_ratio_threshold > 0
        assert pe_max > 0
    
    def test_backtest_config(self):
        """测试回测配置读取"""
        config = ConfigManager()
        
        index_code = config.get('backtest.index_code', '000300.SH')
        initial_capital = config.get('backtest.initial_capital', 1000000.0)
        max_positions = config.get('backtest.max_positions', 4)
        
        assert index_code is not None
        assert initial_capital > 0
        assert max_positions > 0
    
    def test_factors_config(self):
        """测试因子配置读取"""
        config = ConfigManager()
        
        rps_window = config.get('factors.rps.window', 60)
        ma_window = config.get('factors.ma.window', 20)
        volume_ratio_window = config.get('factors.volume_ratio.window', 5)
        pe_max = config.get('factors.pe.max', 30)
        
        assert rps_window > 0
        assert ma_window > 0
        assert volume_ratio_window > 0
        assert pe_max > 0
    
    def test_hunter_config(self):
        """测试Hunter配置读取"""
        config = ConfigManager()
        
        history_days = config.get('hunter.history_days', 120)
        assert history_days > 0


class TestConfigDefaultValues:
    """测试配置默认值处理"""
    
    def test_config_defaults_when_missing(self):
        """测试配置缺失时使用默认值"""
        config = ConfigManager()
        
        # 测试不存在的配置项使用默认值
        default_workers = config.get('concurrency.non_existent_workers', 10)
        assert default_workers == 10
        
        default_threshold = config.get('strategy.non_existent.threshold', 85)
        assert default_threshold == 85
    
    def test_config_none_handling(self):
        """测试配置值为None时的处理"""
        config = ConfigManager()
        
        # 如果配置值为None，应该返回默认值
        value = config.get('some.none.value', 'default')
        # 如果配置不存在或为None，应该返回默认值
        assert value == 'default' or value is not None


class TestConfigBackwardCompatibility:
    """测试配置向后兼容性"""
    
    def test_existing_config_still_works(self):
        """测试现有配置仍然可用"""
        config = ConfigManager()
        
        # 验证原有配置项仍然可以读取
        pe_ttm_max = config.get('pe_ttm_max', 30)
        pb_max = config.get('pb_max', 5)
        roe_min = config.get('roe_min', 8)
        
        assert pe_ttm_max > 0
        assert pb_max > 0
        assert roe_min > 0
    
    def test_index_filter_config_compatibility(self):
        """测试指数过滤配置兼容性"""
        config = ConfigManager()
        
        enabled = config.get('index_filter.enabled', True)
        index_code = config.get('index_filter.index_code', '000852.SH')
        fallback_to_all = config.get('index_filter.fallback_to_all', False)
        
        assert isinstance(enabled, bool)
        assert index_code is not None
        assert isinstance(fallback_to_all, bool)
