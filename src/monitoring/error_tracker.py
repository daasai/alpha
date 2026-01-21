"""
Error Tracker - 错误追踪和记录
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import contextmanager

from ..database import _SessionLocal, ErrorLog
from ..exceptions import DAASError, ErrorContext
from ..logging_config import get_logger

logger = get_logger(__name__)


@contextmanager
def _session_scope():
    """数据库会话上下文管理器"""
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


class ErrorTracker:
    """错误追踪器"""
    
    def __init__(self):
        """初始化错误追踪器"""
        logger.info("ErrorTracker 初始化完成")
    
    def log_error(
        self,
        error: Exception,
        error_code: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        request_info: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        记录错误到数据库
        
        Args:
            error: 异常对象
            error_code: 错误代码
            context: 错误上下文
            request_info: 请求信息（如URL、方法等）
        
        Returns:
            错误日志ID
        """
        import traceback
        
        # 确定错误代码
        if error_code is None:
            if isinstance(error, DAASError):
                error_code = error.error_code
            else:
                error_code = error.__class__.__name__
        
        # 获取错误类型
        error_type = error.__class__.__name__
        
        # 获取错误消息
        message = str(error)
        
        # 获取上下文
        if context is None:
            if isinstance(error, DAASError):
                context = error.context
            else:
                context = ErrorContext()
        
        # 合并请求信息到上下文
        if request_info:
            context.data.update(request_info)
        
        # 获取堆栈跟踪
        stack_trace = traceback.format_exc()
        
        # 保存到数据库
        try:
            with _session_scope() as s:
                error_log = ErrorLog(
                    error_code=error_code,
                    error_type=error_type,
                    message=message,
                    context=context.to_json(),
                    stack_trace=stack_trace,
                    created_at=datetime.now()
                )
                s.add(error_log)
                s.flush()
                error_id = str(error_log.id)
                
                logger.debug(f"错误已记录: ID={error_id}, code={error_code}")
                return error_id
        except Exception as e:
            logger.error(f"记录错误失败: {e}")
            # 返回临时ID
            return f"temp_{datetime.now().timestamp()}"
    
    def get_error(self, error_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取错误日志
        
        Args:
            error_id: 错误日志ID
        
        Returns:
            错误日志字典，如果不存在则返回None
        """
        try:
            with _session_scope() as s:
                error_log = s.query(ErrorLog).filter(ErrorLog.id == error_id).first()
                
                if error_log:
                    return self._to_dict(error_log)
                return None
        except Exception as e:
            logger.error(f"获取错误日志失败: {e}")
            return None
    
    def get_errors(
        self,
        error_code: Optional[str] = None,
        error_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询错误日志
        
        Args:
            error_code: 错误代码过滤
            error_type: 错误类型过滤
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制
        
        Returns:
            错误日志列表
        """
        try:
            with _session_scope() as s:
                query = s.query(ErrorLog)
                
                if error_code:
                    query = query.filter(ErrorLog.error_code == error_code)
                if error_type:
                    query = query.filter(ErrorLog.error_type == error_type)
                if start_date:
                    query = query.filter(ErrorLog.created_at >= start_date)
                if end_date:
                    query = query.filter(ErrorLog.created_at <= end_date)
                
                error_logs = query.order_by(ErrorLog.created_at.desc()).limit(limit).all()
                
                return [self._to_dict(log) for log in error_logs]
        except Exception as e:
            logger.error(f"查询错误日志失败: {e}")
            return []
    
    def get_error_stats(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Args:
            days: 统计天数
        
        Returns:
            统计信息字典
        """
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            with _session_scope() as s:
                # 总错误数
                total_count = s.query(ErrorLog).filter(
                    ErrorLog.created_at >= start_date
                ).count()
                
                # 按错误代码分组统计
                from sqlalchemy import func
                error_code_stats = s.query(
                    ErrorLog.error_code,
                    func.count(ErrorLog.id).label('count')
                ).filter(
                    ErrorLog.created_at >= start_date
                ).group_by(ErrorLog.error_code).all()
                
                # 按错误类型分组统计
                error_type_stats = s.query(
                    ErrorLog.error_type,
                    func.count(ErrorLog.id).label('count')
                ).filter(
                    ErrorLog.created_at >= start_date
                ).group_by(ErrorLog.error_type).all()
                
                return {
                    'total_count': total_count,
                    'period_days': days,
                    'error_code_stats': {code: count for code, count in error_code_stats},
                    'error_type_stats': {error_type: count for error_type, count in error_type_stats}
                }
        except Exception as e:
            logger.error(f"获取错误统计失败: {e}")
            return {
                'total_count': 0,
                'period_days': days,
                'error_code_stats': {},
                'error_type_stats': {}
            }
    
    def _to_dict(self, error_log: ErrorLog) -> Dict[str, Any]:
        """
        将 ORM 对象转换为字典
        
        Args:
            error_log: ErrorLog 对象
        
        Returns:
            字典
        """
        import json
        
        context_dict = {}
        if error_log.context:
            try:
                context_dict = json.loads(error_log.context)
            except Exception:
                context_dict = {}
        
        return {
            'id': error_log.id,
            'error_code': error_log.error_code,
            'error_type': error_log.error_type,
            'message': error_log.message,
            'context': context_dict,
            'stack_trace': error_log.stack_trace,
            'created_at': error_log.created_at.isoformat() if error_log.created_at else None
        }
