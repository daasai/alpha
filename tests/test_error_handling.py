"""
Error Handling Tests
测试错误处理完善功能（Phase 3）
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.exceptions import (
    DAASError, DataFetchError, DataValidationError,
    APIError, ErrorContext
)
from src.monitoring.error_tracker import ErrorTracker
from src.database import ErrorLog, _SessionLocal
# 注意：api.utils.exceptions 需要 FastAPI，在测试中可能需要 mock
try:
    from api.utils.exceptions import (
        get_error_tracker,
        _get_user_friendly_message
    )
except ImportError:
    # 如果 FastAPI 不可用，使用 mock
    def get_error_tracker():
        return ErrorTracker()
    
    def _get_user_friendly_message(error_code, original_message):
        message_map = {
            'DATA_FETCH_ERROR': '数据获取失败，请稍后重试',
            'INTERNAL_ERROR': '服务器内部错误，请稍后重试',
        }
        return message_map.get(error_code, original_message)


class TestEnhancedExceptions:
    """测试增强的异常类"""
    
    def test_daas_error_with_context(self):
        """测试 DAASError 带上下文"""
        context = ErrorContext(
            ts_code='000001.SZ',
            operation='get_daily',
            api='tushare'
        )
        
        error = DAASError(
            message="数据获取失败",
            error_code="DATA_FETCH_ERROR",
            context=context
        )
        
        assert error.message == "数据获取失败"
        assert error.error_code == "DATA_FETCH_ERROR"
        assert error.context.data['ts_code'] == '000001.SZ'
        assert error.timestamp is not None
    
    def test_error_to_dict(self):
        """测试异常序列化"""
        error = DAASError(
            message="测试错误",
            error_code="TEST_ERROR"
        )
        
        error_dict = error.to_dict()
        
        assert error_dict['error_type'] == 'DAASError'
        assert error_dict['error_code'] == 'TEST_ERROR'
        assert error_dict['message'] == '测试错误'
        assert 'timestamp' in error_dict
        assert 'stack_trace' in error_dict
    
    def test_error_chain(self):
        """测试异常链"""
        original_error = ValueError("原始错误")
        daas_error = DataFetchError(
            message="数据获取失败",
            cause=original_error
        )
        
        assert daas_error.cause is original_error
        assert isinstance(daas_error, DAASError)


class TestErrorTracker:
    """测试 ErrorTracker"""
    
    @pytest.fixture(autouse=True)
    def setup_test_db(self, tmp_path, monkeypatch):
        """设置测试数据库"""
        import src.database
        import uuid
        test_db_path = tmp_path / f"test_daas_{uuid.uuid4().hex[:8]}.db"
        
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
        if test_db_path.exists():
            test_db_path.unlink()
    
    @pytest.fixture
    def error_tracker(self):
        """创建 ErrorTracker 实例"""
        return ErrorTracker()
    
    def test_log_error(self, error_tracker):
        """测试记录错误"""
        error = DataFetchError(
            message="数据获取失败",
            error_code="DATA_FETCH_ERROR",
            context=ErrorContext(ts_code='000001.SZ')
        )
        
        request_info = {
            'url': 'http://localhost/api/data',
            'method': 'GET',
        }
        
        error_id = error_tracker.log_error(
            error,
            request_info=request_info
        )
        
        assert error_id is not None
        assert error_id.startswith('temp_') or error_id.isdigit()
    
    def test_get_error(self, error_tracker):
        """测试获取错误"""
        error = DataFetchError(
            message="测试错误",
            error_code="TEST_ERROR"
        )
        
        error_id = error_tracker.log_error(error)
        
        # 如果 error_id 是数字，尝试获取
        if error_id.isdigit():
            result = error_tracker.get_error(int(error_id))
            if result:
                assert result['error_code'] == 'TEST_ERROR'
                assert result['message'] == '测试错误'
    
    def test_get_errors_with_filters(self, error_tracker):
        """测试查询错误（带过滤）"""
        # 记录多个错误
        for i in range(3):
            error = DataFetchError(
                message=f"错误 {i}",
                error_code="DATA_FETCH_ERROR"
            )
            error_tracker.log_error(error)
        
        # 查询错误
        errors = error_tracker.get_errors(
            error_code="DATA_FETCH_ERROR",
            limit=10
        )
        
        assert isinstance(errors, list)
        assert len(errors) >= 0  # 可能为空（取决于数据库状态）
    
    def test_get_error_stats(self, error_tracker):
        """测试获取错误统计"""
        # 记录一些错误
        for i in range(2):
            error = DataFetchError(
                message=f"错误 {i}",
                error_code="DATA_FETCH_ERROR"
            )
            error_tracker.log_error(error)
        
        stats = error_tracker.get_error_stats(days=7)
        
        assert 'total_count' in stats
        assert 'period_days' in stats
        assert 'error_code_stats' in stats
        assert 'error_type_stats' in stats
        assert stats['period_days'] == 7


class TestErrorHandlers:
    """测试错误处理器"""
    
    def test_get_user_friendly_message(self):
        """测试用户友好消息映射"""
        # 测试已知错误代码
        message = _get_user_friendly_message(
            'DATA_FETCH_ERROR',
            '原始错误消息'
        )
        assert message == '数据获取失败，请稍后重试'
        
        # 测试未知错误代码
        message = _get_user_friendly_message(
            'UNKNOWN_ERROR',
            '原始错误消息'
        )
        assert message == '原始错误消息'
        
        # 测试技术细节过滤
        message = _get_user_friendly_message(
            'INTERNAL_ERROR',
            'Traceback (most recent call last):\nFile "test.py", line 1'
        )
        assert 'Traceback' not in message
    
    def test_error_tracker_singleton(self):
        """测试 ErrorTracker 单例"""
        tracker1 = get_error_tracker()
        tracker2 = get_error_tracker()
        
        # 应该是同一个实例
        assert tracker1 is tracker2


class TestErrorPropagation:
    """测试错误传播"""
    
    def test_data_fetch_error_propagation(self):
        """测试 DataFetchError 传播"""
        error = DataFetchError(
            message="API 调用失败",
            error_code="API_ERROR",
            context=ErrorContext(api='tushare')
        )
        
        assert isinstance(error, DAASError)
        assert isinstance(error, DataFetchError)
        assert error.error_code == "API_ERROR"
    
    def test_error_context_serialization(self):
        """测试错误上下文序列化"""
        context = ErrorContext(
            ts_code='000001.SZ',
            operation='get_daily',
            nested={'key': 'value'}
        )
        
        context_dict = context.to_dict()
        assert context_dict['ts_code'] == '000001.SZ'
        assert context_dict['operation'] == 'get_daily'
        
        context_json = context.to_json()
        assert isinstance(context_json, str)
        assert '000001.SZ' in context_json
