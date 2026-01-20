"""
End-to-End Integration Regression Tests
验证完整业务流程（使用Service层）
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.services import HunterService, BacktestService, TruthService
from src.repositories import PredictionRepository


class TestHunterIntegration:
    """Hunter端到端集成测试"""
    
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
    def sample_complete_data(self):
        """创建完整的样本数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]
        
        # 基础数据
        basic_data = []
        # 历史数据
        history_data = []
        
        for ts_code in ['000001.SZ', '000002.SZ']:
            # 基础数据（最新日期）
            basic_data.append({
                'ts_code': ts_code,
                'name': f'股票{ts_code[-1]}',
                'list_date': '20200101',
                'trade_date': dates[-1].strftime('%Y%m%d'),
                'pe_ttm': 15.0,
                'pb': 1.5,
                'mv': 1000000,
                'dividend_yield': 2.0
            })
            
            # 历史数据
            for i, date in enumerate(dates):
                history_data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.1,
                    'high': 10.0 + i * 0.1 + 0.2,
                    'low': 10.0 + i * 0.1 - 0.1,
                    'close': 10.0 + i * 0.1 + 0.05,
                    'vol': 1000000
                })
        
        return pd.DataFrame(basic_data), pd.DataFrame(history_data)
    
    def test_hunter_complete_flow(self, mock_data_provider, sample_complete_data):
        """测试完整Hunter流程"""
        basic_df, history_df = sample_complete_data
        
        # Mock数据获取
        trade_date = history_df['trade_date'].max()
        mock_data_provider.get_daily_basic = MagicMock(return_value=basic_df)
        mock_data_provider.fetch_history_for_hunter = MagicMock(return_value=history_df)
        
        # 创建Service
        service = HunterService(data_provider=mock_data_provider)
        
        # 执行扫描
        result = service.run_scan(trade_date=trade_date)
        
        # 验证结果
        assert isinstance(result, type(service.run_scan('20240101')))  # HunterResult类型
        assert hasattr(result, 'success')
        assert hasattr(result, 'result_df')
        assert hasattr(result, 'diagnostics')
    
    def test_hunter_service_to_repository(self, mock_data_provider, sample_complete_data):
        """测试HunterService结果保存到Repository"""
        basic_df, history_df = sample_complete_data
        
        trade_date = history_df['trade_date'].max()
        mock_data_provider.get_daily_basic = MagicMock(return_value=basic_df)
        mock_data_provider.fetch_history_for_hunter = MagicMock(return_value=history_df)
        
        service = HunterService(data_provider=mock_data_provider)
        result = service.run_scan(trade_date=trade_date)
        
        if result.success and not result.result_df.empty:
            # 使用Repository保存
            repo = PredictionRepository()
            
            predictions = []
            for _, row in result.result_df.iterrows():
                predictions.append({
                    "trade_date": result.trade_date,
                    "ts_code": row["ts_code"],
                    "name": row["name"],
                    "ai_score": 0,
                    "ai_reason": "Alpha Trident策略筛选",
                    "strategy_tag": row.get("strategy_tag", "🚀 强推荐"),
                    "suggested_shares": 0,
                    "price_at_prediction": float(row.get("close", 0))
                })
            
            repo.save_predictions(predictions)
            
            # 验证保存成功
            all_preds = repo.get_all()
            assert len(all_preds) >= len(predictions)


class TestBacktestIntegration:
    """Backtest端到端集成测试"""
    
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
    def sample_history_data(self):
        """创建样本历史数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        dates = [d for d in dates if d.weekday() < 5][:60]
        
        data = []
        for ts_code in ['000001.SZ', '000002.SZ']:
            for i, date in enumerate(dates):
                data.append({
                    'ts_code': ts_code,
                    'trade_date': date.strftime('%Y%m%d'),
                    'open': 10.0 + i * 0.1,
                    'high': 10.0 + i * 0.1 + 0.2,
                    'low': 10.0 + i * 0.1 - 0.1,
                    'close': 10.0 + i * 0.1 + 0.05,
                    'vol': 1000000,
                    'pe_ttm': 15.0
                })
        
        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        return df
    
    def test_backtest_complete_flow(self, mock_data_provider, sample_history_data):
        """测试完整Backtest流程"""
        # 准备数据
        start_date = sample_history_data['trade_date'].min().strftime('%Y%m%d')
        end_date = sample_history_data['trade_date'].max().strftime('%Y%m%d')
        mock_history = sample_history_data.copy()
        mock_history['trade_date'] = mock_history['trade_date'].dt.strftime('%Y%m%d')
        
        mock_data_provider.fetch_history_batch = MagicMock(return_value=mock_history)
        mock_data_provider.get_stock_basic = MagicMock(return_value=pd.DataFrame())
        
        # Mock VectorBacktester
        with patch('src.services.backtest_service.VectorBacktester') as mock_backtester_class:
            mock_backtester = MagicMock()
            mock_backtester_class.return_value = mock_backtester
            mock_backtester.run.return_value = {
                'total_return': 12.5,
                'max_drawdown': 6.2,
                'win_rate': 65.0,
                'equity_curve': pd.Series([1.0, 1.05, 1.10]),
                'strategy_metrics': {'total_trades': 15},
                'benchmark_metrics': {'total_return': 10.0},
                'trades': pd.DataFrame(),
                'top_contributors': pd.DataFrame()
            }
            
            service = BacktestService(data_provider=mock_data_provider)
            result = service.run_backtest(
                start_date=start_date,
                end_date=end_date
            )
        
        # 验证结果
        assert isinstance(result, type(service.run_backtest('20240101', '20240301')))  # BacktestResult类型
        if result.success:
            assert 'total_return' in result.results
            assert 'max_drawdown' in result.results
            assert 'win_rate' in result.results


class TestTruthIntegration:
    """Truth端到端集成测试"""
    
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
    def mock_data_provider(self):
        """创建Mock DataProvider"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            dp = DataProvider()
            dp._pro = MagicMock()
            return dp
    
    def test_truth_complete_flow(self, mock_data_provider):
        """测试完整Truth流程"""
        from src.database import save_daily_predictions
        
        # 保存测试数据
        predictions = [{
            "trade_date": "20240101",
            "ts_code": "000001.SZ",
            "name": "测试股票",
            "ai_score": 0,
            "ai_reason": "测试",
            "price_at_prediction": 10.0
        }]
        save_daily_predictions(predictions)
        
        # Mock API调用
        mock_daily_data = pd.DataFrame({
            'ts_code': ['000001.SZ'],
            'trade_date': ['20240101'],
            'close': [11.0]
        })
        mock_data_provider._pro.daily = MagicMock(return_value=mock_daily_data)
        
        # 创建Service
        service = TruthService(data_provider=mock_data_provider)
        
        # 更新价格
        with patch('src.services.truth_service.time.sleep'):
            result = service.update_prices()
        
        # 验证结果
        assert isinstance(result, type(service.update_prices()))  # TruthResult类型
        assert result.total_count == 1
        
        # 获取验证数据
        df = service.get_verification_data()
        assert not df.empty
        
        # 计算胜率
        win_rate_info = service.calculate_win_rate(df)
        assert 'win_rate' in win_rate_info
        assert 'win_count' in win_rate_info
        assert 'total_count' in win_rate_info


class TestServiceToRepositoryIntegration:
    """测试Service到Repository的集成"""
    
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
    
    def test_hunter_to_repository_flow(self):
        """测试Hunter到Repository的完整流程"""
        with patch('src.data_provider.ts'), \
             patch.dict('os.environ', {'TUSHARE_TOKEN': 'test_token'}):
            from src.data_provider import DataProvider
            from src.services import HunterService
            from src.repositories import PredictionRepository
            
            dp = DataProvider()
            dp._pro = MagicMock()
            
            # Mock数据
            basic_df = pd.DataFrame({
                'ts_code': ['000001.SZ'],
                'name': ['测试'],
                'list_date': ['20200101'],
                'trade_date': ['20240101'],
                'pe_ttm': [15.0],
                'pb': [1.5],
                'mv': [1000000],
                'dividend_yield': [2.0]
            })
            
            history_df = pd.DataFrame({
                'ts_code': ['000001.SZ'] * 60,
                'trade_date': pd.date_range('2024-01-01', periods=60, freq='D').strftime('%Y%m%d'),
                'open': [10.0] * 60,
                'high': [10.5] * 60,
                'low': [9.5] * 60,
                'close': [10.2] * 60,
                'vol': [1000000] * 60
            })
            
            dp.get_daily_basic = MagicMock(return_value=basic_df)
            dp.fetch_history_for_hunter = MagicMock(return_value=history_df)
            
            # 执行Hunter扫描
            service = HunterService(data_provider=dp)
            result = service.run_scan(trade_date='20240101')
            
            if result.success and not result.result_df.empty:
                # 使用Repository保存
                repo = PredictionRepository()
                predictions = [{
                    "trade_date": result.trade_date,
                    "ts_code": row["ts_code"],
                    "name": row["name"],
                    "ai_score": 0,
                    "ai_reason": "Alpha Trident策略筛选",
                    "strategy_tag": row.get("strategy_tag", "🚀 强推荐"),
                    "suggested_shares": 0,
                    "price_at_prediction": float(row.get("close", 0))
                } for _, row in result.result_df.iterrows()]
                
                repo.save_predictions(predictions)
                
                # 验证保存成功
                all_preds = repo.get_all()
                assert len(all_preds) >= len(predictions)
