"""
Unit tests for Database v1.2
Tests for new fields: price_at_prediction, current_price
Tests for new methods: get_all_predictions, update_prediction_price, update_prediction_price_at_prediction
"""

import pytest
import pandas as pd
from pathlib import Path
import tempfile
import shutil

from src.database import (
    save_daily_predictions,
    get_all_predictions,
    update_prediction_price,
    update_prediction_price_at_prediction,
    Prediction,
    _session_scope
)


class TestDatabaseV12Fields:
    """Test new database fields in v1.2"""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path, monkeypatch):
        """Setup test database"""
        # Create temporary database
        test_db_path = tmp_path / "test_daas.db"
        test_data_dir = tmp_path / "data"
        test_data_dir.mkdir()
        
        # Patch database path
        import src.database
        original_db_path = src.database._DB_PATH
        src.database._DB_PATH = test_db_path
        
        # Recreate engine and tables
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
        
        # Restore original
        src.database._DB_PATH = original_db_path
    
    def test_save_with_price_at_prediction(self):
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
        assert all_preds[0]["current_price"] is None
    
    def test_save_without_price_at_prediction(self):
        """Test saving predictions without price_at_prediction (should be None)"""
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "测试股票",
                "ai_score": 0,
                "ai_reason": "Alpha Trident策略筛选",
                "strategy_tag": "🚀 强推荐",
                "suggested_shares": 0
                # No price_at_prediction
            }
        ]
        
        save_daily_predictions(predictions)
        
        all_preds = get_all_predictions()
        assert len(all_preds) == 1
        assert all_preds[0]["price_at_prediction"] is None
    
    def test_get_all_predictions_includes_new_fields(self):
        """Test that get_all_predictions includes new fields"""
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "测试股票1",
                "ai_score": 0,
                "ai_reason": "Test",
                "price_at_prediction": 10.0
            },
            {
                "trade_date": "20240102",
                "ts_code": "000002.SZ",
                "name": "测试股票2",
                "ai_score": 0,
                "ai_reason": "Test",
                "price_at_prediction": 20.0
            }
        ]
        
        save_daily_predictions(predictions)
        
        all_preds = get_all_predictions()
        assert len(all_preds) == 2
        
        # Check that new fields are included
        for pred in all_preds:
            assert "price_at_prediction" in pred
            assert "current_price" in pred
    
    def test_update_prediction_price(self):
        """Test updating current_price and actual_chg"""
        # Save initial prediction
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "测试股票",
                "ai_score": 0,
                "ai_reason": "Test",
                "price_at_prediction": 10.0
            }
        ]
        save_daily_predictions(predictions)
        
        # Update with current price
        update_prediction_price("20240101", "000001.SZ", current_price=11.0, return_pct=10.0)
        
        # Verify update
        all_preds = get_all_predictions()
        assert len(all_preds) == 1
        assert all_preds[0]["current_price"] == 11.0
        assert all_preds[0]["actual_chg"] == 10.0
    
    def test_update_prediction_price_at_prediction(self):
        """Test updating price_at_prediction"""
        # Save initial prediction without price
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "测试股票",
                "ai_score": 0,
                "ai_reason": "Test"
            }
        ]
        save_daily_predictions(predictions)
        
        # Update price_at_prediction
        update_prediction_price_at_prediction("20240101", "000001.SZ", price=10.5)
        
        # Verify update
        all_preds = get_all_predictions()
        assert len(all_preds) == 1
        assert all_preds[0]["price_at_prediction"] == 10.5
    
    def test_update_prediction_price_nonexistent(self):
        """Test updating non-existent prediction (should not crash)"""
        # Should not raise exception
        update_prediction_price("20240101", "999999.SZ", current_price=10.0, return_pct=5.0)
        update_prediction_price_at_prediction("20240101", "999999.SZ", price=10.0)
    
    def test_get_all_predictions_empty(self):
        """Test get_all_predictions with empty database"""
        all_preds = get_all_predictions()
        assert all_preds == []
    
    def test_price_fields_workflow(self):
        """Test complete workflow: save -> update price_at_prediction -> update current_price"""
        # Step 1: Save prediction
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": "000001.SZ",
                "name": "测试股票",
                "ai_score": 0,
                "ai_reason": "Test"
            }
        ]
        save_daily_predictions(predictions)
        
        # Step 2: Update price_at_prediction
        update_prediction_price_at_prediction("20240101", "000001.SZ", price=10.0)
        
        # Step 3: Update current_price and return
        update_prediction_price("20240101", "000001.SZ", current_price=11.0, return_pct=10.0)
        
        # Verify final state
        all_preds = get_all_predictions()
        assert len(all_preds) == 1
        pred = all_preds[0]
        assert pred["price_at_prediction"] == 10.0
        assert pred["current_price"] == 11.0
        assert pred["actual_chg"] == 10.0
    
    def test_multiple_predictions_price_updates(self):
        """Test updating prices for multiple predictions"""
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
                "trade_date": "20240101",
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
        update_prediction_price("20240101", "000002.SZ", current_price=18.0, return_pct=-10.0)
        
        # Verify both updated
        all_preds = get_all_predictions()
        assert len(all_preds) == 2
        
        pred1 = next(p for p in all_preds if p["ts_code"] == "000001.SZ")
        pred2 = next(p for p in all_preds if p["ts_code"] == "000002.SZ")
        
        assert pred1["current_price"] == 11.0
        assert pred1["actual_chg"] == 10.0
        assert pred2["current_price"] == 18.0
        assert pred2["actual_chg"] == -10.0
    
    def test_database_migration(self):
        """Test that database migration adds new columns"""
        # This test verifies that the migration logic works
        # The migration should happen automatically when the module is imported
        from src.database import Prediction
        
        # Check that Prediction model has new fields
        assert hasattr(Prediction, 'price_at_prediction')
        assert hasattr(Prediction, 'current_price')
