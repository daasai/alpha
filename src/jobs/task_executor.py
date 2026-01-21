"""
Task Executor - 任务执行器

封装每日任务执行逻辑，提供：
- 幂等性检查
- 并发控制
- 超时控制
- 执行记录管理
"""
import uuid
import signal
import threading
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

from src.database import (
    create_daily_task_execution,
    update_daily_task_execution_status,
    get_daily_task_execution_by_id,
    get_latest_daily_task_execution,
    get_running_daily_task_execution
)
from src.jobs.daily_runner import DailyRunner
from src.logging_config import get_logger

logger = get_logger(__name__)


class TimeoutError(Exception):
    """超时异常"""
    pass


class TaskExecutor:
    """任务执行器"""
    
    def __init__(
        self,
        daily_runner: Optional[DailyRunner] = None,
        timeout_seconds: int = 3600,
        max_retries: int = 3
    ):
        """
        初始化任务执行器
        
        Args:
            daily_runner: DailyRunner实例，如果为None则创建新实例
            timeout_seconds: 任务超时时间（秒），默认3600秒（1小时）
            max_retries: 最大重试次数
        """
        self.daily_runner = daily_runner or DailyRunner()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._timeout_occurred = False
    
    def execute(
        self,
        trade_date: Optional[str] = None,
        trigger_type: str = "MANUAL",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        执行每日任务
        
        Args:
            trade_date: 交易日期（YYYYMMDD格式），如果为None则使用当前日期
            trigger_type: 触发类型（SCHEDULED/MANUAL/API）
            force: 是否强制执行（绕过幂等性检查）
        
        Returns:
            执行结果字典，包含 execution_id, success, status, errors 等
        """
        # 确定交易日期
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        result = {
            'execution_id': execution_id,
            'trade_date': trade_date,
            'trigger_type': trigger_type,
            'success': False,
            'status': 'FAILED',
            'errors': [],
            'steps_completed': [],
            'is_duplicate': False,
            'duration_seconds': None
        }
        
        try:
            # 1. 幂等性检查
            if not force:
                latest_execution = get_latest_daily_task_execution(trade_date=trade_date)
                if latest_execution and latest_execution.get('status') == 'SUCCESS':
                    logger.warning(
                        f"检测到重复执行: 交易日期 {trade_date} 已有成功记录 "
                        f"(execution_id: {latest_execution.get('execution_id')})"
                    )
                    result['is_duplicate'] = True
                    result['status'] = 'DUPLICATE'
                    result['errors'].append(
                        f"交易日期 {trade_date} 已有成功执行记录，如需重新执行请使用 force=True"
                    )
                    return result
            
            # 2. 并发控制检查
            running_execution = get_running_daily_task_execution()
            if running_execution:
                logger.warning(
                    f"检测到并发执行: 已有任务正在运行 "
                    f"(execution_id: {running_execution.get('execution_id')})"
                )
                result['status'] = 'BLOCKED'
                result['errors'].append(
                    f"已有任务正在执行中 (execution_id: {running_execution.get('execution_id')})，请等待完成"
                )
                return result
            
            # 3. 创建执行记录
            execution_record = create_daily_task_execution(
                execution_id=execution_id,
                trade_date=trade_date,
                trigger_type=trigger_type,
                max_retries=self.max_retries
            )
            
            # 4. 更新状态为RUNNING
            update_daily_task_execution_status(
                execution_id=execution_id,
                status='RUNNING'
            )
            
            # 5. 执行任务（带超时控制）
            try:
                runner_result = self._execute_with_timeout(
                    trade_date=trade_date,
                    execution_id=execution_id
                )
                
                # 6. 计算执行时长
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                # 7. 更新执行记录
                if runner_result.get('success'):
                    result['success'] = True
                    result['status'] = 'SUCCESS'
                    result['steps_completed'] = runner_result.get('steps_completed', [])
                    
                    update_daily_task_execution_status(
                        execution_id=execution_id,
                        status='SUCCESS',
                        steps_completed=runner_result.get('steps_completed', []),
                        duration_seconds=duration
                    )
                    logger.info(
                        f"任务执行成功: execution_id={execution_id}, "
                        f"trade_date={trade_date}, duration={duration:.2f}秒"
                    )
                else:
                    result['status'] = 'FAILED'
                    result['errors'] = runner_result.get('errors', [])
                    result['steps_completed'] = runner_result.get('steps_completed', [])
                    
                    update_daily_task_execution_status(
                        execution_id=execution_id,
                        status='FAILED',
                        steps_completed=runner_result.get('steps_completed', []),
                        errors=runner_result.get('errors', []),
                        duration_seconds=duration
                    )
                    logger.error(
                        f"任务执行失败: execution_id={execution_id}, "
                        f"trade_date={trade_date}, errors={result['errors']}"
                    )
                
                result['duration_seconds'] = duration
                
            except TimeoutError:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                error_msg = f"任务执行超时: 超过 {self.timeout_seconds} 秒"
                result['status'] = 'TIMEOUT'
                result['errors'].append(error_msg)
                result['duration_seconds'] = duration
                
                update_daily_task_execution_status(
                    execution_id=execution_id,
                    status='TIMEOUT',
                    errors=[error_msg],
                    duration_seconds=duration
                )
                logger.error(f"任务执行超时: execution_id={execution_id}, trade_date={trade_date}")
            
            except Exception as e:
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                error_msg = f"任务执行异常: {str(e)}"
                result['status'] = 'FAILED'
                result['errors'].append(error_msg)
                result['duration_seconds'] = duration
                
                update_daily_task_execution_status(
                    execution_id=execution_id,
                    status='FAILED',
                    errors=[error_msg],
                    duration_seconds=duration
                )
                logger.exception(f"任务执行异常: execution_id={execution_id}, trade_date={trade_date}")
        
        except Exception as e:
            # 创建执行记录失败等异常
            error_msg = f"任务执行器异常: {str(e)}"
            result['errors'].append(error_msg)
            logger.exception(f"任务执行器异常: execution_id={execution_id}, trade_date={trade_date}")
        
        return result
    
    def _execute_with_timeout(
        self,
        trade_date: str,
        execution_id: str
    ) -> Dict[str, Any]:
        """
        带超时控制的执行方法
        
        Args:
            trade_date: 交易日期
            execution_id: 执行ID
            
        Returns:
            DailyRunner.run() 的返回结果
            
        Raises:
            TimeoutError: 如果执行超时
        """
        result_container = {'result': None, 'exception': None}
        
        def target():
            try:
                result_container['result'] = self.daily_runner.run(
                    trade_date=trade_date,
                    execution_id=execution_id
                )
            except Exception as e:
                result_container['exception'] = e
        
        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout_seconds)
        
        if thread.is_alive():
            # 线程仍在运行，说明超时
            self._timeout_occurred = True
            raise TimeoutError(f"任务执行超过 {self.timeout_seconds} 秒")
        
        if result_container['exception']:
            raise result_container['exception']
        
        if result_container['result'] is None:
            raise Exception("任务执行返回None")
        
        return result_container['result']
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取执行状态
        
        Args:
            execution_id: 执行ID
            
        Returns:
            执行记录字典，如果不存在返回None
        """
        return get_daily_task_execution_by_id(execution_id)
