"""
Truth Service Regression Tests
验证TruthService功能正确性
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.services import TruthService, TruthResult
from src.database import get_all_predictions, save_daily_predictions


class TestTruthServiceRegression:
    """Truth Service回归测试"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """创建Mock DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def mock_config(self):
        """创建Mock ConfigManager"""
        from src.config_manager import ConfigManager
        return ConfigManager()
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path, monkeypatch):
        """设置测试数据库"""
        import src.database
        test_db_path = tmp_path / "test_daas.db"
        test_data_dir = tmp_path / "data"
        test_data_dir.mkdir()
        
        original_db_path = src.database._DB_PATH
        src.database._DB_PATH = test_db_path
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        src.database._engine = create_engine(
            f"sqlite:///{test_db_path}",
            connect_args={"check_same_thread": False}
        )
        src.database._SessionLocal = sessionmaker(
            bind=src.database._engine,
            autoflush=False,
            autocommit=False
        )
        from src.database import Base
        Base.metadata.create_all(src.database._engine)
        
        yield
        
        src.database._DB_PATH = original_db_path
    
    @pytest.fixture
    def sample_predictions(self):
        """创建样本预测记录"""
        return [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "测试股票1",
                "ai_score": 0,
                "ai_reason": "Alpha Trident策略筛选",
                "strategy_tag": "🚀 强推荐",
                "suggested_shares": 0,
                "price_at_prediction": 10.0
            },
            {
                "trade_date": "20240102",
                "ts_code": "000002.SZ",
                "name": "测试股票2",
                "ai_score": 0,
                "ai_reason": "Alpha Trident策略筛选",
                "strategy_tag": "🚀 强推荐",
                "suggested_shares": 0,
                "price_at_prediction": 20.0
            }
        ]
    
    def test_truth_service_initialization(self, mock_data_provider, mock_config):
        """测试TruthService可以正确初始化"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        assert service.data_provider is not None
        assert service.config is not None
        assert service.data_provider == mock_data_provider
        assert service.config == mock_config
    
    def test_truth_service_get_verification_data(self, mock_data_provider, mock_config,
                                                  sample_predictions):
        """测试获取验证数据"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        
        # 保存测试数据
        save_daily_predictions(sample_predictions)
        
        # 获取验证数据
        df = service.get_verification_data()
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_predictions)
        assert 'ts_code' in df.columns
        assert 'trade_date' in df.columns
    
    def test_truth_service_calculate_win_rate(self, mock_data_provider, mock_config):
        """测试胜率计算"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        
        # 测试空数据（需要包含actual_chg列）
        empty_df = pd.DataFrame(columns=['ts_code', 'actual_chg'])
        result = service.calculate_win_rate(empty_df)
        assert result['win_rate'] == 0.0
        assert result['win_count'] == 0
        assert result['total_count'] == 0
        
        # 测试有数据但无验证结果
        df_no_actual = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'actual_chg': [None]
        })
        result = service.calculate_win_rate(df_no_actual)
        assert result['win_rate'] == 0.0
        assert result['total_count'] == 0
        
        # 测试有验证结果
        df_with_actual = pd.DataFrame({
            'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ'],
            'actual_chg': [5.0, -3.0, 2.0]  # 2胜1负
        })
        result = service.calculate_win_rate(df_with_actual)
        assert result['win_rate'] == pytest.approx(66.67, abs=0.01)
        assert result['win_count'] == 2
        assert result['total_count'] == 3
    
    def test_truth_service_update_prices_empty(self, mock_data_provider, mock_config):
        """测试更新价格（无预测记录）"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        
        result = service.update_prices()
        
        assert result.success
        assert result.updated_count == 0
        assert result.total_count == 0
    
    def test_truth_service_update_prices_with_mock(self, mock_data_provider, mock_config,
                                                     sample_predictions):
        """测试更新价格（有预测记录）"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        
        # 保存测试数据
        save_daily_predictions(sample_predictions)
        
        # Mock API调用
        mock_daily_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [11.0]  # 从10.0涨到11.0，收益率10%
        })
        
        mock_data_provider._pro.daily = MagicMock(return_value=mock_daily_data)
        
        # Mock time.sleep
        with patch('src.services.truth_service.time.sleep'):
            result = service.update_prices()
        
        # 验证结果
        assert result.success
        assert result.total_count == len(sample_predictions)
        # updated_count可能为0（如果API返回空）或大于0
    
    def test_truth_service_config_integration(self, mock_data_provider, mock_config):
        """测试配置集成"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        
        # 验证从配置读取API延迟
        api_delay = mock_config.get('api_rate_limit.tushare_delay', 0.1)
        assert api_delay > 0
    
    def test_truth_service_error_handling(self, mock_data_provider, mock_config,
                                          sample_predictions):
        """测试错误处理"""
        service = TruthService(data_provider=mock_data_provider, config=mock_config)
        
        # 保存测试数据
        save_daily_predictions(sample_predictions)
        
        # Mock API调用抛出异常
        mock_data_provider._pro.daily = MagicMock(side_effect=Exception("API Error"))
        
        # Mock time.sleep
        with patch('src.services.truth_service.time.sleep'):
            result = service.update_prices()
        
        # 应该成功完成（跳过失败的记录）
        assert result.success
        assert result.total_count == len(sample_predictions)
        # updated_count应该为0（因为所有更新都失败）


class TestTruthServiceEquivalence:
    """测试TruthService与原有逻辑的等价性"""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path, monkeypatch):
        """设置测试数据库"""
        import src.database
        test_db_path = tmp_path / "test_daas.db"
        test_data_dir = tmp_path / "data"
        test_data_dir.mkdir()
        
        original_db_path = src.database._DB_PATH
        src.database._DB_PATH = test_db_path
        
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        src.database._engine = create_engine(
            f"sqlite:///{test_db_path}",
            connect_args={"check_same_thread": False}
        )
        src.database._SessionLocal = sessionmaker(
            bind=src.database._engine,
            autoflush=False,
            autocommit=False
        )
        from src.database import Base
        Base.metadata.create_all(src.database._engine)
        
        yield
        
        src.database._DB_PATH = original_db_path
    
    def test_win_rate_calculation_equivalence(self):
        """测试胜率计算与原有逻辑一致"""
        from src.services import TruthService
        
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            from src.config_manager import ConfigManager
            
            dp = DataProvider()
            dp._pro = MagicMock()
            config = ConfigManager()
            service = TruthService(data_provider=dp, config=config)
            
            # 测试数据
            df = pd.DataFrame({
                'ts_code': ['000001.SZ', '000002.SZ', '000003.SZ', '000004.SZ'],
                'actual_chg': [5.0, -2.0, 3.0, None]  # 2胜1负1未验证
            })
            
            result = service.calculate_win_rate(df)
            
            # 验证结果
            assert result['total_count'] == 3  # 只有3条已验证
            assert result['win_count'] == 2
            assert result['win_rate'] == pytest.approx(66.67, abs=0.01)
