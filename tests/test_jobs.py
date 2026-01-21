"""
Tests for Jobs Module
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.jobs.task_executor import TaskExecutor, TimeoutError
from src.jobs.retry_manager import RetryManager
from src.jobs.notification_service import NotificationService
from src.jobs.daily_runner import DailyRunner


class TestTaskExecutor:
    """测试任务执行器"""
    
    def test_executor_initialization(self):
        """测试执行器初始化"""
        executor = TaskExecutor(timeout_seconds=1800, max_retries=3)
        assert executor.timeout_seconds == 1800
        assert executor.max_retries == 3
        assert executor.daily_runner is not None
    
    @patch('src.jobs.task_executor.get_latest_daily_task_execution')
    @patch('src.jobs.task_executor.get_running_daily_task_execution')
    @patch('src.jobs.task_executor.create_daily_task_execution')
    @patch('src.jobs.task_executor.update_daily_task_execution_status')
    def test_execute_idempotency_check(self, mock_update, mock_create, mock_running, mock_latest):
        """测试幂等性检查"""
        # 模拟已有成功记录
        mock_latest.return_value = {
            'execution_id': 'test-id',
            'trade_date': '20240101',
            'status': 'SUCCESS'
        }
        mock_running.return_value = None
        
        executor = TaskExecutor()
        result = executor.execute(trade_date='20240101', force=False)
        
        assert result['is_duplicate'] is True
        assert result['status'] == 'DUPLICATE'
        assert len(result['errors']) > 0
    
    @patch('src.jobs.task_executor.get_latest_daily_task_execution')
    @patch('src.jobs.task_executor.get_running_daily_task_execution')
    @patch('src.jobs.task_executor.create_daily_task_execution')
    @patch('src.jobs.task_executor.update_daily_task_execution_status')
    def test_execute_concurrency_check(self, mock_update, mock_create, mock_running, mock_latest):
        """测试并发控制检查"""
        mock_latest.return_value = None
        # 模拟已有运行中的任务
        mock_running.return_value = {
            'execution_id': 'running-id',
            'status': 'RUNNING'
        }
        
        executor = TaskExecutor()
        result = executor.execute(trade_date='20240101', force=False)
        
        assert result['status'] == 'BLOCKED'
        assert len(result['errors']) > 0


class TestRetryManager:
    """测试重试管理器"""
    
    def test_retry_manager_initialization(self):
        """测试重试管理器初始化"""
        manager = RetryManager(max_retries=5, retry_delays=[100, 200, 300])
        assert manager.max_retries == 5
        assert manager.retry_delays == [100, 200, 300]
    
    @patch('src.jobs.retry_manager.get_latest_daily_task_execution')
    def test_should_retry(self, mock_get):
        """测试是否应该重试"""
        manager = RetryManager(max_retries=3)
        
        # 测试失败状态且未达最大重试次数
        mock_get.return_value = {
            'execution_id': 'test-id',
            'status': 'FAILED',
            'retry_count': 1,
            'max_retries': 3
        }
        assert manager.should_retry('test-id') is True
        
        # 测试已达到最大重试次数
        mock_get.return_value = {
            'execution_id': 'test-id',
            'status': 'FAILED',
            'retry_count': 3,
            'max_retries': 3
        }
        assert manager.should_retry('test-id') is False
        
        # 测试成功状态不需要重试
        mock_get.return_value = {
            'execution_id': 'test-id',
            'status': 'SUCCESS',
            'retry_count': 0,
            'max_retries': 3
        }
        assert manager.should_retry('test-id') is False


class TestNotificationService:
    """测试通知服务"""
    
    def test_notification_service_initialization(self):
        """测试通知服务初始化"""
        service = NotificationService(
            enabled=True,
            channels=['log', 'email'],
            email_config={
                'smtp_host': 'smtp.example.com',
                'smtp_port': 587,
                'smtp_user': 'user@example.com',
                'smtp_password': 'password',
                'recipients': ['recipient@example.com']
            }
        )
        assert service.enabled is True
        assert 'log' in service.channels
        assert 'email' in service.channels
    
    @patch('src.jobs.notification_service.logger')
    def test_notify_log(self, mock_logger):
        """测试日志通知"""
        service = NotificationService(channels=['log'])
        service._notify_log('Test Title', 'Test Message', 'info')
        mock_logger.info.assert_called_once()
    
    def test_notify_execution_result_success(self):
        """测试执行结果通知（成功）"""
        service = NotificationService(channels=['log'])
        service.notify_execution_result(
            execution_id='test-id',
            trade_date='20240101',
            status='SUCCESS',
            duration_seconds=120.5
        )
        # 如果没有异常则测试通过


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
