"""
Retry Manager - 重试管理器

实现失败任务的自动重试机制：
- 指数退避策略
- 最大重试次数控制
- 重试间隔配置
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from src.database import (
    get_latest_daily_task_execution,
    get_daily_task_execution_by_id,
    update_daily_task_execution_status,
    list_daily_task_executions
)
from src.logging_config import get_logger

logger = get_logger(__name__)


class RetryManager:
    """重试管理器"""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delays: Optional[List[int]] = None
    ):
        """
        初始化重试管理器
        
        Args:
            max_retries: 最大重试次数，默认3次
            retry_delays: 重试延迟列表（秒），如果为None则使用指数退避
        """
        self.max_retries = max_retries
        
        if retry_delays is None:
            # 默认指数退避：5分钟、10分钟、30分钟
            self.retry_delays = [300, 600, 1800]
        else:
            self.retry_delays = retry_delays
    
    def should_retry(
        self,
        execution_id: str,
        trade_date: Optional[str] = None
    ) -> bool:
        """
        判断是否应该重试
        
        Args:
            execution_id: 执行ID
            trade_date: 交易日期（可选，用于验证）
        
        Returns:
            如果应该重试返回True，否则返回False
        """
        execution = get_daily_task_execution_by_id(execution_id)
        
        if not execution:
            logger.warning(f"未找到执行记录: {execution_id}")
            return False
        
        # 验证trade_date是否匹配（如果提供了trade_date）
        if trade_date and execution.get('trade_date') != trade_date:
            logger.warning(f"执行记录trade_date不匹配: {execution_id}")
            return False
        
        status = execution.get('status')
        retry_count = execution.get('retry_count', 0)
        max_retries = execution.get('max_retries', self.max_retries)
        
        # 只有失败状态才需要重试
        if status not in ['FAILED', 'TIMEOUT']:
            return False
        
        # 检查是否超过最大重试次数
        if retry_count >= max_retries:
            logger.info(
                f"执行 {execution_id} 已达到最大重试次数 {max_retries}，不再重试"
            )
            return False
        
        return True
    
    def schedule_retry(
        self,
        execution_id: str,
        trade_date: Optional[str] = None
    ) -> Optional[datetime]:
        """
        安排重试
        
        Args:
            execution_id: 执行ID
            trade_date: 交易日期（可选）
        
        Returns:
            下次重试时间，如果无法安排重试返回None
        """
        if not self.should_retry(execution_id, trade_date):
            return None
        
        execution = get_daily_task_execution_by_id(execution_id)
        if not execution:
            return None
        
        retry_count = execution.get('retry_count', 0)
        
        # 计算重试延迟
        if retry_count < len(self.retry_delays):
            delay_seconds = self.retry_delays[retry_count]
        else:
            # 如果重试次数超过配置的延迟列表，使用最后一个延迟值
            delay_seconds = self.retry_delays[-1] if self.retry_delays else 600
        
        next_retry_at = datetime.now() + timedelta(seconds=delay_seconds)
        
        # 更新执行记录
        update_daily_task_execution_status(
            execution_id=execution_id,
            status='RETRYING',
            next_retry_at=next_retry_at
        )
        
        logger.info(
            f"安排重试: execution_id={execution_id}, "
            f"retry_count={retry_count + 1}/{execution.get('max_retries')}, "
            f"next_retry_at={next_retry_at.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        return next_retry_at
    
    def increment_retry_count(self, execution_id: str) -> int:
        """
        增加重试计数
        
        Args:
            execution_id: 执行ID
        
        Returns:
            新的重试计数
        """
        execution = get_daily_task_execution_by_id(execution_id)
        if not execution:
            logger.warning(f"未找到执行记录: {execution_id}")
            return 0
        
        current_count = execution.get('retry_count', 0)
        new_count = current_count + 1
        
        # 更新数据库中的retry_count
        update_daily_task_execution_status(
            execution_id=execution_id,
            status=execution.get('status', 'FAILED'),  # 保持当前状态
            retry_count=new_count
        )
        
        logger.debug(f"增加重试计数: execution_id={execution_id}, retry_count={new_count}")
        return new_count
    
    def get_pending_retries(self) -> List[Dict[str, Any]]:
        """
        获取待重试的任务列表
        
        Returns:
            待重试任务列表
        """
        now = datetime.now()
        pending_retries = []
        
        # 获取所有RETRYING状态的执行记录
        retrying_executions = list_daily_task_executions(status='RETRYING', limit=100)
        
        for execution in retrying_executions:
            next_retry_at = execution.get('next_retry_at')
            if next_retry_at and isinstance(next_retry_at, str):
                try:
                    next_retry_at = datetime.fromisoformat(next_retry_at.replace('Z', '+00:00'))
                except:
                    try:
                        next_retry_at = datetime.strptime(next_retry_at, '%Y-%m-%d %H:%M:%S')
                    except:
                        continue
            
            if next_retry_at and next_retry_at <= now:
                pending_retries.append(execution)
        
        return pending_retries
    
    def cancel_retry(self, execution_id: str) -> bool:
        """
        取消重试
        
        Args:
            execution_id: 执行ID
        
        Returns:
            如果成功取消返回True
        """
        execution = get_daily_task_execution_by_id(execution_id)
        if not execution:
            return False
        
        if execution.get('status') == 'RETRYING':
            update_daily_task_execution_status(
                execution_id=execution_id,
                status='FAILED',
                next_retry_at=None
            )
            logger.info(f"取消重试: execution_id={execution_id}")
            return True
        
        return False
