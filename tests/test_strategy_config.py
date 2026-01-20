"""
Strategy Configuration Integration Tests
验证AlphaStrategy从配置读取阈值
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock

from src.strategy import AlphaStrategy
from src.config_manager import ConfigManager
from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor


class TestAlphaStrategyConfigIntegration:
    """AlphaStrategy配置集成测试"""
    
    @pytest.fixture
    def sample_enriched_data(self):
        """创建已计算因子的样本数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ', '000003.SZ']:
            for i, date in enumerate(dates):
                data.append({
                    'ts_code': ts_code,
                    'name': f'股票{ts_code[-1]}',
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.1,
                    'high': 10.0 + i * 0.1 + 0.2,
                    'low': 10.0 + i * 0.1 - 0.1,
                    'close': 10.0 + i * 0.1 + 0.05,
                    'vol': 1000000,
                    'pe_ttm': 15.0,
                    'pb': 1.5,
                    'mv': 1000000,
                    'dividend_yield': 2.0,
                    'list_date': '20200101'
                })
        
        df = pd.DataFrame(data)
        
        # 计算因子
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        return pipeline.run(df)
    
    def test_alpha_strategy_with_config(self, sample_enriched_data):
        """测试AlphaStrategy使用配置"""
        config = ConfigManager()
        strategy = AlphaStrategy(sample_enriched_data.copy(), config=config)
        
        # 验证阈值从配置读取
        assert hasattr(strategy, 'rps_threshold')
        assert hasattr(strategy, 'vol_ratio_threshold')
        assert strategy.rps_threshold > 0
        assert strategy.vol_ratio_threshold > 0
    
    def test_alpha_strategy_default_values(self, sample_enriched_data):
        """测试AlphaStrategy使用默认值（无配置时）"""
        # 不传入config，应该使用默认值
        strategy = AlphaStrategy(sample_enriched_data.copy())
        
        # 验证有默认值
        assert strategy.rps_threshold == 85  # 默认值
        assert strategy.vol_ratio_threshold == 1.5  # 默认值
    
    def test_alpha_strategy_config_threshold(self, sample_enriched_data):
        """测试配置阈值生效"""
        config = ConfigManager()
        
        # 获取配置中的阈值
        rps_threshold = config.get('strategy.alpha_trident.rps_threshold', 85)
        vol_ratio_threshold = config.get('strategy.alpha_trident.vol_ratio_threshold', 1.5)
        
        strategy = AlphaStrategy(sample_enriched_data.copy(), config=config)
        
        # 验证策略使用了配置的阈值
        assert strategy.rps_threshold == rps_threshold
        assert strategy.vol_ratio_threshold == vol_ratio_threshold
    
    def test_alpha_strategy_filtering_with_config(self, sample_enriched_data):
        """测试使用配置阈值进行筛选"""
        config = ConfigManager()
        strategy = AlphaStrategy(sample_enriched_data.copy(), config=config)
        
        # 手动设置一些股票满足条件
        if len(sample_enriched_data) > 0:
            first_code = sample_enriched_data['ts_code'].iloc[0]
            mask = sample_enriched_data['ts_code'] == first_code
            
            # 设置满足配置阈值
            rps_threshold = strategy.rps_threshold
            vol_ratio_threshold = strategy.vol_ratio_threshold
            
            sample_enriched_data.loc[mask, 'rps_60'] = rps_threshold + 5
            sample_enriched_data.loc[mask, 'is_undervalued'] = 1
            sample_enriched_data.loc[mask, 'vol_ratio_5'] = vol_ratio_threshold + 0.5
            sample_enriched_data.loc[mask, 'above_ma_20'] = 1
        
        result_df = strategy.filter_alpha_trident()
        
        # 验证筛选结果
        assert isinstance(result_df, pd.DataFrame)
        if not result_df.empty:
            # 验证筛选条件
            assert (result_df['rps_60'] > strategy.rps_threshold).all()
            assert (result_df['vol_ratio_5'] > strategy.vol_ratio_threshold).all()
    
    def test_alpha_strategy_backward_compatibility(self, sample_enriched_data):
        """测试向后兼容性（无config参数时使用默认值）"""
        # 不传config参数
        strategy = AlphaStrategy(sample_enriched_data.copy())
        
        # 应该使用默认值
        assert strategy.rps_threshold == 85
        assert strategy.vol_ratio_threshold == 1.5
        
        # 应该能正常筛选
        result_df = strategy.filter_alpha_trident()
        assert isinstance(result_df, pd.DataFrame)
