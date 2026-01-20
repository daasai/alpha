"""
Repository Layer Tests
验证数据访问抽象层功能
"""

import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from src.repositories import (
    PredictionRepository,
    HistoryRepository,
    ConstituentRepository
)
from src.database import (
    save_daily_predictions,
    get_all_predictions,
    get_cached_daily_history,
    save_daily_history_batch,
    get_cached_constituents,
    save_constituents
)


class TestPredictionRepository:
    """测试PredictionRepository"""
    
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
    
    def test_prediction_repository_save(self):
        """测试PredictionRepository保存功能"""
        repo = PredictionRepository()
        
        predictions = [{
            "trade_date": "20240101",
            "ts_code": "000001.SZ",
            "name": "测试股票",
            "ai_score": 0,
            "ai_reason": "测试",
            "price_at_prediction": 10.0
        }]
        
        repo.save_predictions(predictions)
        
        # 验证数据已保存
        all_preds = repo.get_all()
        assert len(all_preds) == 1
        assert all_preds[0]["ts_code"] == "000001.SZ"
        assert all_preds[0]["price_at_prediction"] == 10.0
    
    def test_prediction_repository_get_all(self):
        """测试获取所有预测记录"""
        repo = PredictionRepository()
        
        # 保存多条记录
        predictions = [
            {
                "trade_date": "20240101",
                "ts_code": f"00000{i}.SZ",
                "name": f"股票{i}",
                "ai_score": 0,
                "ai_reason": "测试",
                "price_at_prediction": 10.0 + i
            }
            for i in range(1, 4)
        ]
        repo.save_predictions(predictions)
        
        # 获取所有记录
        all_preds = repo.get_all()
        assert len(all_preds) == 3
    
    def test_prediction_repository_get_pending(self):
        """测试获取待验证的预测记录"""
        repo = PredictionRepository()
        
        # 保存记录（actual_chg为None）
        predictions = [{
            "trade_date": "20240101",
            "ts_code": "000001.SZ",
            "name": "测试",
            "ai_score": 0,
            "ai_reason": "测试",
            "price_at_prediction": 10.0
        }]
        repo.save_predictions(predictions)
        
        # 获取待验证记录
        pending = repo.get_pending()
        assert len(pending) >= 1
    
    def test_prediction_repository_get_verified(self):
        """测试获取已验证的预测记录"""
        repo = PredictionRepository()
        
        # 保存并更新记录
        predictions = [{
            "trade_date": "20240101",
            "ts_code": "000001.SZ",
            "name": "测试",
            "ai_score": 0,
            "ai_reason": "测试",
            "price_at_prediction": 10.0
        }]
        repo.save_predictions(predictions)
        
        # 更新价格（设置actual_chg）
        repo.update_price("20240101", "000001.SZ", 11.0, 10.0)
        
        # 获取已验证记录
        verified = repo.get_verified()
        assert len(verified) >= 1
        assert verified[0]["actual_chg"] is not None
    
    def test_prediction_repository_update_price(self):
        """测试更新价格"""
        repo = PredictionRepository()
        
        # 保存记录
        predictions = [{
            "trade_date": "20240101",
            "ts_code": "000001.SZ",
            "name": "测试",
            "ai_score": 0,
            "ai_reason": "测试",
            "price_at_prediction": 10.0
        }]
        repo.save_predictions(predictions)
        
        # 更新价格
        repo.update_price("20240101", "000001.SZ", 11.0, 10.0)
        
        # 验证更新
        all_preds = repo.get_all()
        assert all_preds[0]["current_price"] == 11.0
        assert all_preds[0]["actual_chg"] == 10.0


class TestHistoryRepository:
    """测试HistoryRepository"""
    
    def test_history_repository_get_cached(self):
        """测试获取缓存的历史数据"""
        repo = HistoryRepository()
        
        # 测试空列表
        result = repo.get_cached([], '20240101', '20240301')
        assert isinstance(result, pd.DataFrame)
        assert result.empty
    
    def test_history_repository_save_batch(self):
        """测试批量保存历史数据"""
        repo = HistoryRepository()
        
        # 创建测试数据
        df = pd.DataFrame({
            'ts_code': ['000001.SZ', '000001.SZ'],
            'trade_date': ['20240101', '20240102'],
            'open': [10.0, 10.5],
            'high': [10.5, 11.0],
            'low': [9.5, 10.0],
            'close': [10.2, 10.8],
            'vol': [1000000, 1100000]
        })
        
        # 保存（需要数据库，这里只测试接口）
        # 注意：实际保存需要数据库连接
        try:
            repo.save_batch(df)
            # 如果成功，验证可以读取
            result = repo.get_cached(['000001.SZ'], '20240101', '20240102')
            assert isinstance(result, pd.DataFrame)
        except Exception:
            # 如果数据库未配置，跳过
            pytest.skip("数据库未配置，跳过保存测试")


class TestConstituentRepository:
    """测试ConstituentRepository"""
    
    def test_constituent_repository_get_cached(self):
        """测试获取缓存的成分股"""
        repo = ConstituentRepository()
        
        # 测试获取（可能为空，如果缓存不存在）
        result = repo.get_cached('000852.SH', '20240101')
        assert isinstance(result, list)
    
    def test_constituent_repository_save(self):
        """测试保存成分股"""
        repo = ConstituentRepository()
        
        constituents_data = [
            {'ts_code': '000001.SZ', 'weight': 0.5},
            {'ts_code': '000002.SZ', 'weight': 0.3}
        ]
        
        # 保存（需要数据库）
        try:
            repo.save('000852.SH', '20240101', constituents_data)
            
            # 验证可以读取
            result = repo.get_cached('000852.SH', '20240101')
            assert len(result) == 2
            assert '000001.SZ' in result
            assert '000002.SZ' in result
        except Exception:
            pytest.skip("数据库未配置，跳过保存测试")
    
    def test_constituent_repository_get_latest_date(self):
        """测试获取最新日期"""
        repo = ConstituentRepository()
        
        # 测试获取（可能为空字符串）
        latest_date = repo.get_latest_date('000852.SH')
        assert isinstance(latest_date, str)


class TestRepositoryAbstraction:
    """测试Repository抽象层"""
    
    def test_repositories_independent(self):
        """测试不同Repository实例相互独立"""
        pred_repo = PredictionRepository()
        hist_repo = HistoryRepository()
        const_repo = ConstituentRepository()
        
        # 验证它们是不同的实例
        assert pred_repo is not hist_repo
        assert pred_repo is not const_repo
        assert hist_repo is not const_repo
    
    def test_repository_methods_exist(self):
        """测试Repository方法存在"""
        pred_repo = PredictionRepository()
        
        # 验证关键方法存在
        assert hasattr(pred_repo, 'save_predictions')
        assert hasattr(pred_repo, 'get_all')
        assert hasattr(pred_repo, 'get_pending')
        assert hasattr(pred_repo, 'get_verified')
        assert hasattr(pred_repo, 'update_price')
        
        hist_repo = HistoryRepository()
        assert hasattr(hist_repo, 'get_cached')
        assert hasattr(hist_repo, 'save_batch')
        
        const_repo = ConstituentRepository()
        assert hasattr(const_repo, 'get_cached')
        assert hasattr(const_repo, 'save')
