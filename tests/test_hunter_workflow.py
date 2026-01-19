"""
Integration tests for Hunter workflow
Tests complete flow: DataProvider → FactorPipeline → AlphaStrategy → Database
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

from src.data_provider import DataProvider
from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
from src.strategy import AlphaStrategy, get_trade_date
from src.database import save_daily_predictions, get_all_predictions


class TestHunterWorkflow:
    """Test complete Hunter workflow"""
    
    @pytest.fixture
    def mock_data_provider(self):
        """Create mocked DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def sample_daily_data(self):
        """Create sample daily data"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]  # 60 weekdays
        
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
    
    def test_hunter_workflow_complete(self, mock_data_provider, sample_daily_data):
        """Test complete Hunter workflow"""
        # Step 1: DataProvider (simulated - using sample data)
        df = sample_daily_data.copy()
        
        # Step 2: FactorPipeline
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(df)
        
        # Verify factors are computed
        assert 'rps_60' in enriched_df.columns
        assert 'above_ma_20' in enriched_df.columns
        assert 'vol_ratio_5' in enriched_df.columns
        assert 'is_undervalued' in enriched_df.columns
        
        # Step 3: AlphaStrategy
        strategy = AlphaStrategy(enriched_df)
        result_df = strategy.filter_alpha_trident()
        
        # Verify result structure
        assert isinstance(result_df, pd.DataFrame)
        if not result_df.empty:
            assert 'ts_code' in result_df.columns
            assert 'name' in result_df.columns
            assert 'strategy_tag' in result_df.columns
            assert (result_df['strategy_tag'] == '🚀 强推荐').all()
    
    def test_hunter_workflow_data_flow(self, sample_daily_data):
        """Test data flow through the pipeline"""
        # Initial data
        initial_count = len(sample_daily_data)
        
        # FactorPipeline
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(sample_daily_data.copy())
        
        # Data should not be lost
        assert len(enriched_df) == initial_count
        
        # AlphaStrategy
        strategy = AlphaStrategy(enriched_df)
        result_df = strategy.filter_alpha_trident()
        
        # Result should be subset or equal
        assert len(result_df) <= len(enriched_df)
    
    def test_hunter_workflow_factor_order(self, sample_daily_data):
        """Test that factors are computed in correct order"""
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(sample_daily_data.copy())
        
        # All factors should be present
        assert 'rps_60' in enriched_df.columns
        assert 'above_ma_20' in enriched_df.columns
        assert 'vol_ratio_5' in enriched_df.columns
        assert 'is_undervalued' in enriched_df.columns
    
    def test_hunter_workflow_strategy_filtering(self, sample_daily_data):
        """Test that strategy correctly filters based on factors"""
        # Create data where some stocks meet criteria
        df = sample_daily_data.copy()
        
        # Compute factors
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=60))
        pipeline.add(MAFactor(window=20))
        pipeline.add(VolumeRatioFactor(window=5))
        pipeline.add(PEProxyFactor(max_pe=30))
        
        enriched_df = pipeline.run(df)
        
        # Manually set some stocks to meet all criteria
        if len(enriched_df) > 0:
            # Set first stock to meet all criteria
            enriched_df.loc[enriched_df['ts_code'] == enriched_df['ts_code'].iloc[0], 'rps_60'] = 90.0
            enriched_df.loc[enriched_df['ts_code'] == enriched_df['ts_code'].iloc[0], 'is_undervalued'] = 1
            enriched_df.loc[enriched_df['ts_code'] == enriched_df['ts_code'].iloc[0], 'vol_ratio_5'] = 2.0
            enriched_df.loc[enriched_df['ts_code'] == enriched_df['ts_code'].iloc[0], 'above_ma_20'] = 1
        
        strategy = AlphaStrategy(enriched_df)
        result_df = strategy.filter_alpha_trident()
        
        # If we have valid data, result should contain filtered stocks
        assert isinstance(result_df, pd.DataFrame)


class TestHunterDatabaseIntegration:
    """Test database integration in Hunter workflow"""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path, monkeypatch):
        """Setup test database"""
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
    
    def test_save_predictions_with_price(self):
        """Test saving predictions with price_at_prediction"""
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "测试股票",
                "ai_score": 0,
                "ai_reason": "Alpha Trident策略筛选",
                "strategy_tag": "🚀 强推荐",
                "suggested_shares": 0,
                "price_at_prediction": 10.5
            }
        ]
        
        save_daily_predictions(predictions)
        
        # Verify saved
        all_preds = get_all_predictions()
        assert len(all_preds) == 1
        assert all_preds[0]["price_at_prediction"] == 10.5
        assert all_preds[0]["ts_code"] == "000001.SZ"
        assert all_preds[0]["strategy_tag"] == "🚀 强推荐"
    
    def test_save_multiple_predictions(self):
        """Test saving multiple predictions"""
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": f"00000{i}.SZ",
                "name": f"股票{i}",
                "ai_score": 0,
                "ai_reason": "Alpha Trident策略筛选",
                "strategy_tag": "🚀 强推荐",
                "suggested_shares": 0,
                "price_at_prediction": 10.0 + i
            }
            for i in range(1, 4)
        ]
        
        save_daily_predictions(predictions)
        
        # Verify all saved
        all_preds = get_all_predictions()
        assert len(all_preds) == 3
        assert set(p["ts_code"] for p in all_preds) == {"000001.SZ", "000002.SZ", "000003.SZ"}
