"""
自定义异常类 - 统一异常体系
增强版本：添加错误追踪字段
"""
from datetime import datetime
from typing import Optional, Dict, Any
import traceback
import json


class ErrorContext:
    """错误上下文信息"""
    def __init__(self, **kwargs):
        self.data = kwargs
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.data
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.data, ensure_ascii=False, default=str)


class DAASError(Exception):
    """DAAS系统基础异常"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化异常
        
        Args:
            message: 错误消息
            error_code: 错误代码
            context: 错误上下文
            cause: 原始异常（用于异常链）
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or ErrorContext()
        self.timestamp = datetime.now()
        self.cause = cause
        
        # 自动捕获堆栈跟踪
        self.stack_trace = traceback.format_exc()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context.to_dict(),
            'timestamp': self.timestamp.isoformat(),
            'stack_trace': self.stack_trace
        }
    
    def __str__(self) -> str:
        context_str = f", 上下文: {self.context.to_dict()}" if self.context.data else ""
        return f"{self.__class__.__name__}({self.error_code}): {self.message}{context_str}"


class DataError(DAASError):
    """数据相关错误"""
    pass


class DataLoaderError(DataError):
    """数据加载错误"""
    pass


class DataFetchError(DataError):
    """数据获取错误"""
    pass


class DataValidationError(DataError):
    """数据验证错误"""
    pass


class APIError(DataError):
    """API 调用错误"""
    pass


class RateLimitError(APIError):
    """API 速率限制错误（QPS限制）"""
    
    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        error_code: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None
    ):
        """
        初始化速率限制错误
        
        Args:
            message: 错误消息
            retry_after: 建议重试时间（秒），如果为None则使用默认值60秒
            error_code: 错误代码
            context: 错误上下文
            cause: 原始异常
        """
        super().__init__(message, error_code, context, cause)
        self.retry_after = retry_after or 60  # 默认60秒后重试


class StrategyError(DAASError):
    """策略相关错误"""
    pass


class FactorError(DAASError):
    """因子计算错误"""
    pass


class ConfigurationError(DAASError):
    """配置错误"""
    pass


class CacheError(DAASError):
    """缓存错误"""
    pass


class ValidationError(DataValidationError):
    """数据验证错误（向后兼容）"""
    pass
