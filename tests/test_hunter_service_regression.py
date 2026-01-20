"""
Hunter Service Regression Tests
验证HunterService与原有逻辑的等价性
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.services import HunterService, HunterResult
from src.data_provider import DataProvider
from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
from src.strategy import AlphaStrategy, get_trade_date
from src.exceptions import DataFetchError, StrategyError, FactorError


class TestHunterServiceRegression:
    """Hunter Service回归测试 - 验证与原有逻辑等价"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """创建Mock DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def mock_config(self):
        """创建Mock ConfigManager"""
        from src.config_manager import ConfigManager
        config = ConfigManager()
        return config
    
    @pytest.fixture
    def sample_daily_data(self):
        """创建样本日线数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]  # 60个交易日
        
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
                    'vol': 1000000 + np.random.randint(-100000, 100000),
                    'pe_ttm': 15.0 + np.random.normal(0, 5),
                    'pb': 1.5,
                    'mv': 1000000,
                    'dividend_yield': 2.0,
                    'list_date': '20200101'
                })
        
        return pd.DataFrame(data)
    
    @pytest.fixture
    def sample_basic_data(self, sample_daily_data):
        """创建样本基础数据"""
        # 从日线数据提取基础数据
        latest_date = sample_daily_data['trade_date'].max()
        latest_data = sample_daily_data[sample_daily_data['trade_date'] == latest_date].copy()
        
        basic_df = latest_data[['ts_code', 'name', 'list_date', 'pe_ttm', 'pb', 'mv', 'dividend_yield']].copy()
        basic_df['trade_date'] = latest_date
        return basic_df
    
    def test_hunter_service_initialization(self, mock_data_provider, mock_config):
        """测试HunterService可以正确初始化"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        assert service.data_provider is not None
        assert service.config is not None
        assert service.data_provider == mock_data_provider
        assert service.config == mock_config
    
    def test_hunter_service_auto_initialization(self):
        """测试HunterService自动初始化依赖"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            service = HunterService()
            assert service.data_provider is not None
            assert service.config is not None
    
    def test_hunter_service_run_scan_structure(self, mock_data_provider, mock_config, 
                                                sample_basic_data, sample_daily_data):
        """测试HunterService.run_scan()返回结构"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        # Mock数据获取
        trade_date = sample_daily_data['trade_date'].max()
        mock_data_provider.get_daily_basic = MagicMock(return_value=sample_basic_data)
        mock_data_provider.fetch_history_for_hunter = MagicMock(return_value=sample_daily_data)
        
        result = service.run_scan(trade_date=trade_date)
        
        # 验证返回结构
        assert isinstance(result, HunterResult)
        assert hasattr(result, 'success')
        assert hasattr(result, 'result_df')
        assert hasattr(result, 'trade_date')
        assert hasattr(result, 'diagnostics')
        assert hasattr(result, 'error')
    
    def test_hunter_service_factor_computation(self, mock_data_provider, mock_config,
                                                sample_daily_data):
        """测试因子计算逻辑与原有方式一致"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        # 测试因子计算
        enriched_df = service._compute_factors(sample_daily_data.copy())
        
        # 验证因子列存在
        assert 'rps_60' in enriched_df.columns
        assert 'above_ma_20' in enriched_df.columns
        assert 'vol_ratio_5' in enriched_df.columns
        assert 'is_undervalued' in enriched_df.columns
        
        # 验证因子值合理性
        if not enriched_df['rps_60'].isna().all():
            assert enriched_df['rps_60'].min() >= 0
            assert enriched_df['rps_60'].max() <= 100
    
    def test_hunter_service_strategy_application(self, mock_data_provider, mock_config,
                                                 sample_daily_data):
        """测试策略应用逻辑"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        # 计算因子
        enriched_df = service._compute_factors(sample_daily_data.copy())
        
        # 手动设置一些股票满足条件
        if len(enriched_df) > 0:
            trade_date = enriched_df['trade_date'].max()
            # 设置第一个股票满足所有条件
            first_code = enriched_df['ts_code'].iloc[0]
            mask = enriched_df['ts_code'] == first_code
            enriched_df.loc[mask, 'rps_60'] = 90.0
            enriched_df.loc[mask, 'is_undervalued'] = 1
            enriched_df.loc[mask, 'vol_ratio_5'] = 2.0
            enriched_df.loc[mask, 'above_ma_20'] = 1
        
        # 应用策略
        result_df = service._apply_strategy(enriched_df, trade_date)
        
        # 验证结果
        assert isinstance(result_df, pd.DataFrame)
        if not result_df.empty:
            assert 'ts_code' in result_df.columns
            assert 'name' in result_df.columns
            assert 'strategy_tag' in result_df.columns
    
    def test_hunter_service_error_handling(self, mock_data_provider, mock_config):
        """测试错误处理"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        # 测试数据获取失败
        mock_data_provider.get_daily_basic = MagicMock(return_value=pd.DataFrame())
        
        result = service.run_scan(trade_date='20240101')
        
        assert not result.success
        assert result.error is not None
        assert '基础数据' in result.error or '数据' in result.error
    
    def test_hunter_service_config_integration(self, mock_data_provider, mock_config,
                                                   sample_daily_data):
        """测试配置集成"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        # 测试从配置读取因子参数
        enriched_df = service._compute_factors(sample_daily_data.copy())
        
        # 验证因子计算使用了配置（或默认值）
        assert 'rps_60' in enriched_df.columns
        
        # 测试配置中的阈值
        rps_threshold = mock_config.get('strategy.alpha_trident.rps_threshold', 85)
        assert rps_threshold == 85  # 默认值或配置值
    
    def test_hunter_service_diagnostics(self, mock_data_provider, mock_config,
                                        sample_basic_data, sample_daily_data):
        """测试诊断信息生成"""
        service = HunterService(data_provider=mock_data_provider, config=mock_config)
        
        trade_date = sample_daily_data['trade_date'].max()
        mock_data_provider.get_daily_basic = MagicMock(return_value=sample_basic_data)
        mock_data_provider.fetch_history_for_hunter = MagicMock(return_value=sample_daily_data)
        
        result = service.run_scan(trade_date=trade_date)
        
        if result.success:
            # 验证诊断信息
            assert 'diagnostics' in result.__dict__
            diagnostics = result.diagnostics
            assert isinstance(diagnostics, dict)
            
            # 验证关键诊断字段
            if 'total_stocks' in diagnostics:
                assert diagnostics['total_stocks'] > 0
            if 'result_count' in diagnostics:
                assert diagnostics['result_count'] >= 0


class TestHunterServiceEquivalence:
    """测试HunterService与原有逻辑的等价性"""
    
    @pytest.fixture
    def sample_enriched_data(self):
        """创建已计算因子的样本数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ']:
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
    
    def test_strategy_filtering_equivalence(self, sample_enriched_data):
        """测试策略筛选结果与原有方式一致"""
        # 原有方式
        strategy_old = AlphaStrategy(sample_enriched_data.copy())
        result_old = strategy_old.filter_alpha_trident()
        
        # 新方式（通过Service）
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.config_manager import ConfigManager
            config = ConfigManager()
            service = HunterService(config=config)
            
            trade_date = sample_enriched_data['trade_date'].max()
            result_new = service._apply_strategy(sample_enriched_data.copy(), trade_date)
        
        # 验证结果结构一致
        if not result_old.empty and not result_new.empty:
            # 验证关键列存在
            assert set(result_old.columns) == set(result_new.columns)
            
            # 验证筛选逻辑一致（股票代码集合应该相同）
            old_codes = set(result_old['ts_code'].unique())
            new_codes = set(result_new['ts_code'].unique())
            assert old_codes == new_codes
