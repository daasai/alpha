"""
Integration tests for Truth workflow
Tests complete flow: get_all_predictions → fetch latest prices → update_prediction_price
"""

import pytest
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.data_provider import DataProvider
from src.database import (
    save_daily_predictions,
    get_all_predictions,
    update_prediction_price,
    update_prediction_price_at_prediction
)


class TestTruthWorkflow:
    """Test complete Truth workflow"""
    
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
    
    @pytest.fixture
    def mock_data_provider(self):
        """Create mocked DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    @pytest.fixture
    def sample_predictions(self):
        """Create sample predictions in database"""
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "股票1",
                "ai_score": 0,
                "ai_reason": "Alpha Trident策略筛选",
                "strategy_tag": "🚀 强推荐",
                "suggested_shares": 0,
                "price_at_prediction": 10.0
            },
            {
                "trade_date": "20240101",
                "ts_code": "000002.SZ",
                "name": "股票2",
                "ai_score": 0,
                "ai_reason": "Alpha Trident策略筛选",
                "strategy_tag": "🚀 强推荐",
                "suggested_shares": 0,
                "price_at_prediction": 20.0
            }
        ]
        save_daily_predictions(predictions)
        return predictions
    
    def test_truth_workflow_get_all_predictions(self, sample_predictions):
        """Test getting all predictions"""
        all_preds = get_all_predictions()
        
        assert len(all_preds) == 2
        assert all_preds[0]["price_at_prediction"] == 10.0
        assert all_preds[1]["price_at_prediction"] == 20.0
    
    def test_truth_workflow_update_prices(self, mock_data_provider, sample_predictions):
        """Test updating prices for predictions"""
        # Get all predictions
        all_preds = get_all_predictions()
        assert len(all_preds) == 2
        
        # Update prices
        update_prediction_price("20240101", "000001.SZ", current_price=11.0, return_pct=10.0)
        update_prediction_price("20240101", "000002.SZ", current_price=18.0, return_pct=-10.0)
        
        # Verify updates
        updated_preds = get_all_predictions()
        pred1 = next(p for p in updated_preds if p["ts_code"] == "000001.SZ")
        pred2 = next(p for p in updated_preds if p["ts_code"] == "000002.SZ")
        
        assert pred1["current_price"] == 11.0
        assert pred1["actual_chg"] == 10.0
        assert pred2["current_price"] == 18.0
        assert pred2["actual_chg"] == -10.0
    
    def test_truth_workflow_return_calculation(self, sample_predictions):
        """Test return calculation accuracy"""
        # Update with known prices
        price_at_pred = 10.0
        current_price = 11.0
        expected_return = (current_price - price_at_pred) / price_at_pred * 100  # 10.0%
        
        update_prediction_price("20240101", "000001.SZ", current_price=current_price, return_pct=expected_return)
        
        # Verify calculation
        all_preds = get_all_predictions()
        pred = next(p for p in all_preds if p["ts_code"] == "000001.SZ")
        
        assert abs(pred["actual_chg"] - expected_return) < 0.01
    
    def test_truth_workflow_price_at_prediction_update(self, sample_predictions):
        """Test updating price_at_prediction separately"""
        # Initially price_at_prediction is set
        all_preds = get_all_predictions()
        pred = next(p for p in all_preds if p["ts_code"] == "000001.SZ")
        assert pred["price_at_prediction"] == 10.0
        
        # Update price_at_prediction
        update_prediction_price_at_prediction("20240101", "000001.SZ", price=10.5)
        
        # Verify update
        updated_preds = get_all_predictions()
        updated_pred = next(p for p in updated_preds if p["ts_code"] == "000001.SZ")
        assert updated_pred["price_at_prediction"] == 10.5
    
    def test_truth_workflow_win_rate_calculation(self, sample_predictions):
        """Test win rate calculation from updated predictions"""
        # Update predictions with different returns
        update_prediction_price("20240101", "000001.SZ", current_price=11.0, return_pct=10.0)  # Win
        update_prediction_price("20240101", "000002.SZ", current_price=18.0, return_pct=-10.0)  # Loss
        
        # Get all predictions
        all_preds = get_all_predictions()
        
        # Calculate win rate
        verified_preds = [p for p in all_preds if p["actual_chg"] is not None]
        wins = [p for p in verified_preds if p["actual_chg"] > 0]
        win_rate = len(wins) / len(verified_preds) * 100 if verified_preds else 0
        
        assert win_rate == 50.0  # 1 win, 1 loss
    
    def test_truth_workflow_multiple_dates(self):
        """Test workflow with predictions from multiple dates"""
        # Save predictions from different dates
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "股票1",
                "ai_score": 0,
                "ai_reason": "Test",
                "price_at_prediction": 10.0
            },
            {
                "trade_date": "20240102",
                "ts_code": "000002.SZ",
                "name": "股票2",
                "ai_score": 0,
                "ai_reason": "Test",
                "price_at_prediction": 20.0
            }
        ]
        save_daily_predictions(predictions)
        
        # Update both
        update_prediction_price("20240101", "000001.SZ", current_price=11.0, return_pct=10.0)
        update_prediction_price("20240102", "000002.SZ", current_price=22.0, return_pct=10.0)
        
        # Verify both updated
        all_preds = get_all_predictions()
        assert len(all_preds) == 2
        assert all(p["actual_chg"] is not None for p in all_preds)
    
    def test_truth_workflow_empty_predictions(self):
        """Test workflow with no predictions"""
        all_preds = get_all_predictions()
        assert all_preds == []
    
    def test_truth_workflow_partial_updates(self, sample_predictions):
        """Test updating only some predictions"""
        # Update only one
        update_prediction_price("20240101", "000001.SZ", current_price=11.0, return_pct=10.0)
        
        # Verify one updated, one not
        all_preds = get_all_predictions()
        pred1 = next(p for p in all_preds if p["ts_code"] == "000001.SZ")
        pred2 = next(p for p in all_preds if p["ts_code"] == "000002.SZ")
        
        assert pred1["actual_chg"] is not None
        assert pred2["actual_chg"] is None
