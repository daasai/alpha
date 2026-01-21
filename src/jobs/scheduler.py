"""
Task Scheduler - 任务调度器

使用APScheduler实现应用内任务调度
"""
import pytz
from datetime import datetime, time
from typing import Optional, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.jobs.task_executor import TaskExecutor
from src.jobs.notification_service import NotificationService
from src.jobs.retry_manager import RetryManager
from src.config_manager import ConfigManager
from src.logging_config import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(
        self,
        config: Optional[ConfigManager] = None,
        task_executor: Optional[TaskExecutor] = None,
        notification_service: Optional[NotificationService] = None
    ):
        """
        初始化任务调度器
        
        Args:
            config: 配置管理器
            task_executor: 任务执行器
            notification_service: 通知服务
        """
        self.config = config or ConfigManager()
        self.task_executor = task_executor or TaskExecutor()
        self.notification_service = notification_service or NotificationService()
        self.retry_manager = RetryManager()
        
        self.scheduler = None
        self.job_id = 'daily_runner_job'
        self._is_running = False
    
    def start(self) -> bool:
        """
        启动调度器
        
        Returns:
            如果成功启动返回True
        """
        if self._is_running:
            logger.warning("调度器已在运行")
            return False
        
        try:
            # 读取配置
            jobs_config = self.config.get('jobs.daily_runner', {})
            enabled = jobs_config.get('enabled', True)
            
            if not enabled:
                logger.info("任务调度器已禁用")
                return False
            
            schedule_time = jobs_config.get('schedule_time', '17:30')
            timezone_str = jobs_config.get('timezone', 'Asia/Shanghai')
            
            # 解析时间
            hour, minute = map(int, schedule_time.split(':'))
            
            # 创建调度器
            self.scheduler = BackgroundScheduler(
                timezone=pytz.timezone(timezone_str)
            )
            
            # 添加每日任务
            self.scheduler.add_job(
                func=self._execute_scheduled_task,
                trigger=CronTrigger(hour=hour, minute=minute),
                id=self.job_id,
                name='Daily Runner',
                replace_existing=True
            )
            
            # 添加重试任务（每分钟检查一次）
            self.scheduler.add_job(
                func=self._check_retries,
                trigger='cron',
                minute='*',
                id='retry_checker',
                name='Retry Checker',
                replace_existing=True
            )
            
            # 启动调度器
            self.scheduler.start()
            self._is_running = True
            
            logger.info(
                f"任务调度器已启动: 每日 {schedule_time} ({timezone_str}) 执行"
            )
            return True
        
        except Exception as e:
            logger.error(f"启动任务调度器失败: {e}")
            return False
    
    def stop(self) -> bool:
        """
        停止调度器
        
        Returns:
            如果成功停止返回True
        """
        if not self._is_running or not self.scheduler:
            return False
        
        try:
            self.scheduler.shutdown(wait=True)
            self._is_running = False
            logger.info("任务调度器已停止")
            return True
        except Exception as e:
            logger.error(f"停止任务调度器失败: {e}")
            return False
    
    def is_running(self) -> bool:
        """检查调度器是否在运行"""
        return self._is_running and self.scheduler and self.scheduler.running
    
    def get_next_run_time(self) -> Optional[datetime]:
        """
        获取下次执行时间
        
        Returns:
            下次执行时间，如果调度器未运行返回None
        """
        if not self.is_running():
            return None
        
        job = self.scheduler.get_job(self.job_id)
        if job:
            return job.next_run_time
        return None
    
    def _execute_scheduled_task(self) -> None:
        """执行定时任务"""
        logger.info("定时任务触发: 开始执行每日任务")
        
        try:
            result = self.task_executor.execute(
                trade_date=None,  # 使用当前日期
                trigger_type='SCHEDULED',
                force=False
            )
            
            # 发送通知
            self.notification_service.notify_execution_result(
                execution_id=result.get('execution_id', ''),
                trade_date=result.get('trade_date', ''),
                status=result.get('status', 'FAILED'),
                errors=result.get('errors', []),
                duration_seconds=result.get('duration_seconds')
            )
        
        except Exception as e:
            logger.exception(f"执行定时任务异常: {e}")
            self.notification_service.notify(
                title="定时任务执行异常",
                message=f"执行定时任务时发生异常: {str(e)}",
                level='error'
            )
    
    def _check_retries(self) -> None:
        """检查并执行待重试的任务"""
        try:
            pending_retries = self.retry_manager.get_pending_retries()
            
            for execution in pending_retries:
                execution_id = execution.get('execution_id')
                trade_date = execution.get('trade_date')
                
                logger.info(f"执行重试任务: execution_id={execution_id}, trade_date={trade_date}")
                
                try:
                    result = self.task_executor.execute(
                        trade_date=trade_date,
                        trigger_type='SCHEDULED',  # 重试任务也标记为SCHEDULED
                        force=False
                    )
                    
                    # 发送通知
                    self.notification_service.notify_execution_result(
                        execution_id=result.get('execution_id', ''),
                        trade_date=result.get('trade_date', ''),
                        status=result.get('status', 'FAILED'),
                        errors=result.get('errors', []),
                        duration_seconds=result.get('duration_seconds')
                    )
                
                except Exception as e:
                    logger.exception(f"执行重试任务异常: {e}")
        
        except Exception as e:
            logger.exception(f"检查重试任务异常: {e}")
