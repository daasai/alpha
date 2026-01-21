"""
Jobs Router - 任务管理API

提供任务执行、查询、重试等API接口
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel

from src.jobs.task_executor import TaskExecutor
from src.jobs.retry_manager import RetryManager
from src.database import (
    get_daily_task_execution_by_id,
    list_daily_task_executions,
    get_latest_daily_task_execution
)
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


# Request/Response Models
class TriggerRequest(BaseModel):
    """触发任务请求"""
    trade_date: Optional[str] = None  # 交易日期（YYYYMMDD格式）
    force: bool = False  # 是否强制执行（绕过幂等性检查）


class TriggerResponse(BaseModel):
    """触发任务响应"""
    success: bool
    execution_id: str
    message: str
    trade_date: str


class ExecutionStatusResponse(BaseModel):
    """执行状态响应"""
    execution_id: str
    trade_date: str
    trigger_type: str
    status: str
    is_duplicate: bool
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    steps_completed: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    retry_count: int
    max_retries: int
    next_retry_at: Optional[str] = None


class ExecutionHistoryResponse(BaseModel):
    """执行历史响应"""
    total: int
    executions: List[ExecutionStatusResponse]


# 全局实例
_task_executor = None
_retry_manager = None


def get_task_executor() -> TaskExecutor:
    """获取任务执行器实例（单例）"""
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor()
    return _task_executor


def get_retry_manager() -> RetryManager:
    """获取重试管理器实例（单例）"""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
    return _retry_manager


def _execute_task_async(
    task_executor: TaskExecutor,
    trade_date: Optional[str],
    trigger_type: str,
    force: bool
) -> None:
    """异步执行任务"""
    try:
        result = task_executor.execute(
            trade_date=trade_date,
            trigger_type=trigger_type,
            force=force
        )
        logger.info(f"异步任务执行完成: execution_id={result.get('execution_id')}")
    except Exception as e:
        logger.exception(f"异步任务执行异常: {e}")


@router.post("/daily-runner/trigger", response_model=TriggerResponse)
async def trigger_daily_runner(
    request: TriggerRequest,
    background_tasks: BackgroundTasks
):
    """
    手动触发每日任务
    
    Args:
        request: 触发请求
        background_tasks: FastAPI后台任务
    
    Returns:
        触发响应
    """
    try:
        task_executor = get_task_executor()
        
        # 确定交易日期
        trade_date = request.trade_date
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        # 幂等性检查（如果未设置force）
        if not request.force:
            latest_execution = get_latest_daily_task_execution(trade_date=trade_date)
            if latest_execution and latest_execution.get('status') == 'SUCCESS':
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": f"交易日期 {trade_date} 已有成功执行记录",
                        "execution_id": latest_execution.get('execution_id'),
                        "hint": "如需重新执行，请设置 force=true"
                    }
                )
        
        # 并发控制检查
        running_execution = get_latest_daily_task_execution()
        if running_execution and running_execution.get('status') == 'RUNNING':
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "已有任务正在执行中",
                    "execution_id": running_execution.get('execution_id'),
                    "hint": "请等待当前任务完成"
                }
            )
        
        # 创建执行记录（在后台任务中执行）
        # 先创建执行记录，然后异步执行
        execution_id = task_executor.execute(
            trade_date=trade_date,
            trigger_type='API',
            force=request.force
        ).get('execution_id')
        
        # 如果执行被阻止（如重复执行），返回相应信息
        execution = get_daily_task_execution_by_id(execution_id)
        if execution and execution.get('status') in ['DUPLICATE', 'BLOCKED']:
            return TriggerResponse(
                success=False,
                execution_id=execution_id,
                message=execution.get('errors', ['执行被阻止'])[0] if execution.get('errors') else '执行被阻止',
                trade_date=trade_date
            )
        
        # 在后台异步执行任务
        background_tasks.add_task(
            _execute_task_async,
            task_executor,
            trade_date,
            'API',
            request.force
        )
        
        return TriggerResponse(
            success=True,
            execution_id=execution_id,
            message="任务已触发，正在后台执行",
            trade_date=trade_date
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"触发任务异常: {e}")
        raise HTTPException(status_code=500, detail=f"触发任务失败: {str(e)}")


@router.get("/daily-runner/status", response_model=ExecutionStatusResponse)
async def get_daily_runner_status(
    trade_date: Optional[str] = Query(None, description="交易日期（YYYYMMDD格式）")
):
    """
    获取每日任务执行状态
    
    Args:
        trade_date: 交易日期，如果不提供则返回最新的执行记录
    
    Returns:
        执行状态
    """
    try:
        execution = get_latest_daily_task_execution(trade_date=trade_date)
        
        if not execution:
            raise HTTPException(
                status_code=404,
                detail="未找到执行记录"
            )
        
        return ExecutionStatusResponse(
            execution_id=execution.get('execution_id', ''),
            trade_date=execution.get('trade_date', ''),
            trigger_type=execution.get('trigger_type', ''),
            status=execution.get('status', ''),
            is_duplicate=execution.get('is_duplicate', False),
            started_at=execution.get('started_at').isoformat() if execution.get('started_at') else '',
            completed_at=execution.get('completed_at').isoformat() if execution.get('completed_at') else None,
            duration_seconds=execution.get('duration_seconds'),
            steps_completed=execution.get('steps_completed', []),
            errors=execution.get('errors', []),
            retry_count=execution.get('retry_count', 0),
            max_retries=execution.get('max_retries', 3),
            next_retry_at=execution.get('next_retry_at').isoformat() if execution.get('next_retry_at') else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取执行状态异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取执行状态失败: {str(e)}")


@router.get("/daily-runner/history", response_model=ExecutionHistoryResponse)
async def get_daily_runner_history(
    trade_date: Optional[str] = Query(None, description="交易日期（YYYYMMDD格式）"),
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回记录数限制")
):
    """
    获取每日任务执行历史
    
    Args:
        trade_date: 交易日期（可选）
        status: 状态过滤（可选）
        limit: 返回记录数限制
    
    Returns:
        执行历史
    """
    try:
        executions = list_daily_task_executions(
            trade_date=trade_date,
            status=status,
            limit=limit
        )
        
        execution_responses = []
        for exec_data in executions:
            execution_responses.append(
                ExecutionStatusResponse(
                    execution_id=exec_data.get('execution_id', ''),
                    trade_date=exec_data.get('trade_date', ''),
                    trigger_type=exec_data.get('trigger_type', ''),
                    status=exec_data.get('status', ''),
                    is_duplicate=exec_data.get('is_duplicate', False),
                    started_at=exec_data.get('started_at').isoformat() if exec_data.get('started_at') else '',
                    completed_at=exec_data.get('completed_at').isoformat() if exec_data.get('completed_at') else None,
                    duration_seconds=exec_data.get('duration_seconds'),
                    steps_completed=exec_data.get('steps_completed', []),
                    errors=exec_data.get('errors', []),
                    retry_count=exec_data.get('retry_count', 0),
                    max_retries=exec_data.get('max_retries', 3),
                    next_retry_at=exec_data.get('next_retry_at').isoformat() if exec_data.get('next_retry_at') else None
                )
            )
        
        return ExecutionHistoryResponse(
            total=len(execution_responses),
            executions=execution_responses
        )
    
    except Exception as e:
        logger.exception(f"获取执行历史异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取执行历史失败: {str(e)}")


@router.get("/daily-runner/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_detail(execution_id: str):
    """
    获取单次执行详情
    
    Args:
        execution_id: 执行ID
    
    Returns:
        执行详情
    """
    try:
        execution = get_daily_task_execution_by_id(execution_id)
        
        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"未找到执行记录: {execution_id}"
            )
        
        return ExecutionStatusResponse(
            execution_id=execution.get('execution_id', ''),
            trade_date=execution.get('trade_date', ''),
            trigger_type=execution.get('trigger_type', ''),
            status=execution.get('status', ''),
            is_duplicate=execution.get('is_duplicate', False),
            started_at=execution.get('started_at').isoformat() if execution.get('started_at') else '',
            completed_at=execution.get('completed_at').isoformat() if execution.get('completed_at') else None,
            duration_seconds=execution.get('duration_seconds'),
            steps_completed=execution.get('steps_completed', []),
            errors=execution.get('errors', []),
            retry_count=execution.get('retry_count', 0),
            max_retries=execution.get('max_retries', 3),
            next_retry_at=execution.get('next_retry_at').isoformat() if execution.get('next_retry_at') else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"获取执行详情异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取执行详情失败: {str(e)}")


@router.post("/daily-runner/{execution_id}/retry")
async def retry_execution(
    execution_id: str,
    background_tasks: BackgroundTasks
):
    """
    手动重试失败的任务
    
    Args:
        execution_id: 执行ID
        background_tasks: FastAPI后台任务
    
    Returns:
        重试响应
    """
    try:
        retry_manager = get_retry_manager()
        task_executor = get_task_executor()
        
        # 检查是否可以重试
        execution = get_daily_task_execution_by_id(execution_id)
        if not execution:
            raise HTTPException(
                status_code=404,
                detail=f"未找到执行记录: {execution_id}"
            )
        
        if not retry_manager.should_retry(execution_id, execution.get('trade_date')):
            raise HTTPException(
                status_code=400,
                detail="该任务不符合重试条件（可能已成功或已达到最大重试次数）"
            )
        
        # 安排重试
        next_retry_at = retry_manager.schedule_retry(
            execution_id,
            execution.get('trade_date')
        )
        
        if not next_retry_at:
            raise HTTPException(
                status_code=400,
                detail="无法安排重试"
            )
        
        # 在后台执行重试
        trade_date = execution.get('trade_date')
        background_tasks.add_task(
            _execute_task_async,
            task_executor,
            trade_date,
            'SCHEDULED',  # 重试任务标记为SCHEDULED
            False
        )
        
        return {
            "success": True,
            "message": "重试任务已安排",
            "execution_id": execution_id,
            "next_retry_at": next_retry_at.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"重试任务异常: {e}")
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")
