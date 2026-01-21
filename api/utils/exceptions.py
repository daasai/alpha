"""
API Exception Handlers
增强版本：集成 ErrorTracker，返回错误ID
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.exceptions import (
    DAASError,
    DataFetchError,
    DataValidationError,
    StrategyError,
    FactorError,
    ConfigurationError,
    APIError,
    ErrorContext,
)


# 组合管理相关异常
class PortfolioError(DAASError):
    """组合管理基础异常"""
    pass


class InsufficientFundsError(PortfolioError):
    """资金不足错误"""
    def __init__(self, required: float, available: float, **kwargs):
        message = f"资金不足: 需要 {required:.2f}，可用 {available:.2f}"
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_FUNDS",
            context=ErrorContext(required=required, available=available, **kwargs)
        )


class PositionNotFoundError(PortfolioError):
    """持仓不存在错误"""
    def __init__(self, ts_code: str, **kwargs):
        message = f"持仓不存在: {ts_code}"
        super().__init__(
            message=message,
            error_code="POSITION_NOT_FOUND",
            context=ErrorContext(ts_code=ts_code, **kwargs)
        )


class InsufficientVolumeError(PortfolioError):
    """可用数量不足错误"""
    def __init__(self, ts_code: str, required: int, available: int, **kwargs):
        message = f"可用数量不足: {ts_code} 需要 {required}，可用 {available}"
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_VOLUME",
            context=ErrorContext(ts_code=ts_code, required=required, available=available, **kwargs)
        )


class AccountNotInitializedError(PortfolioError):
    """账户未初始化错误"""
    def __init__(self, **kwargs):
        message = "账户未初始化，请先初始化账户"
        super().__init__(
            message=message,
            error_code="ACCOUNT_NOT_INITIALIZED",
            context=ErrorContext(**kwargs)
        )
from src.monitoring.error_tracker import ErrorTracker
from src.logging_config import get_logger

logger = get_logger(__name__)

# 全局 ErrorTracker 实例（单例）
_error_tracker = None


def get_error_tracker() -> ErrorTracker:
    """获取 ErrorTracker 实例（单例）"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
    return _error_tracker


class APIException(Exception):
    """API异常基类"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        super().__init__(self.message)


def map_daas_error_to_api_error(error: DAASError) -> APIException:
    """将DAAS错误映射为API异常"""
    from src.exceptions import RateLimitError
    
    if isinstance(error, RateLimitError):
        # QPS限制错误：返回429状态码和友好的错误消息
        retry_after = getattr(error, 'retry_after', 60)
        return APIException(
            message=f"Tushare API访问频率超限，请等待{retry_after}秒后重试",
            status_code=429,
            error_code="RATE_LIMIT_ERROR"
        )
    elif isinstance(error, DataFetchError):
        return APIException(
            message=str(error),
            status_code=503,
            error_code="DATA_FETCH_ERROR"
        )
    elif isinstance(error, DataValidationError):
        return APIException(
            message=str(error),
            status_code=400,
            error_code="DATA_VALIDATION_ERROR"
        )
    elif isinstance(error, StrategyError):
        return APIException(
            message=str(error),
            status_code=500,
            error_code="STRATEGY_ERROR"
        )
    elif isinstance(error, FactorError):
        return APIException(
            message=str(error),
            status_code=500,
            error_code="FACTOR_ERROR"
        )
    elif isinstance(error, ConfigurationError):
        return APIException(
            message=str(error),
            status_code=500,
            error_code="CONFIGURATION_ERROR"
        )
    elif isinstance(error, APIError):
        return APIException(
            message=str(error),
            status_code=503,
            error_code="API_ERROR"
        )
    else:
        return APIException(
            message=str(error),
            status_code=500,
            error_code="INTERNAL_ERROR"
        )


async def api_exception_handler(request: Request, exc: APIException):
    """API异常处理器"""
    logger.error(f"API Exception: {exc.message} (code: {exc.error_code})")
    
    # 记录错误到 ErrorTracker
    error_id = None
    try:
        request_info = {
            'url': str(request.url),
            'method': request.method,
            'path': request.url.path,
            'query_params': str(request.query_params),
        }
        error_id = get_error_tracker().log_error(
            exc,
            error_code=exc.error_code,
            request_info=request_info
        )
    except Exception as e:
        logger.warning(f"记录错误失败: {e}")
    
    # 改进错误消息（更友好）
    user_message = _get_user_friendly_message(exc.error_code, exc.message)
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.error_code,
            "message": user_message,
            "error_id": error_id,  # 错误ID用于追踪
            "data": None
        }
    )


async def daas_exception_handler(request: Request, exc: DAASError):
    """DAAS异常处理器"""
    logger.error(f"DAAS Error: {exc.message} (code: {exc.error_code})")
    
    # 记录错误到 ErrorTracker
    error_id = None
    try:
        request_info = {
            'url': str(request.url),
            'method': request.method,
            'path': request.url.path,
            'query_params': str(request.query_params),
        }
        error_id = get_error_tracker().log_error(
            exc,
            error_code=exc.error_code,
            context=exc.context,
            request_info=request_info
        )
    except Exception as e:
        logger.warning(f"记录错误失败: {e}")
    
    api_exc = map_daas_error_to_api_error(exc)
    
    # 改进错误消息
    user_message = _get_user_friendly_message(api_exc.error_code, api_exc.message)
    
    return JSONResponse(
        status_code=api_exc.status_code,
        content={
            "success": False,
            "error": api_exc.error_code,
            "message": user_message,
            "error_id": error_id,  # 错误ID用于追踪
            "data": None
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    logger.warning(f"Validation error: {exc.errors()}")
    
    # 记录错误到 ErrorTracker
    error_id = None
    try:
        from src.exceptions import DataValidationError, ErrorContext
        validation_error = DataValidationError(
            message="请求参数验证失败",
            error_code="VALIDATION_ERROR",
            context=ErrorContext(validation_errors=exc.errors())
        )
        request_info = {
            'url': str(request.url),
            'method': request.method,
            'path': request.url.path,
        }
        error_id = get_error_tracker().log_error(
            validation_error,
            request_info=request_info
        )
    except Exception as e:
        logger.warning(f"记录验证错误失败: {e}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": "请求参数验证失败，请检查输入参数",
            "error_id": error_id,
            "data": exc.errors()
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理器"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    # 处理detail为字典的情况（如重复执行错误）
    if isinstance(exc.detail, dict):
        error_code = exc.detail.get('error', 'HTTP_ERROR')
        message = exc.detail.get('message', str(exc.detail))
        hint = exc.detail.get('hint')
        execution_id = exc.detail.get('execution_id')
        user_friendly = exc.detail.get('user_friendly', False)
        
        # 构建响应内容
        response_content = {
            "success": False,
            "error": error_code,
            "message": message,
            "error_id": None,
            "data": None
        }
        
        # 如果是用户友好的错误，添加额外信息
        if user_friendly:
            response_content["detail"] = {
                "hint": hint,
                "execution_id": execution_id,
                "user_friendly": True
            }
        
        return JSONResponse(
            status_code=exc.status_code,
            content=response_content
        )
    
    # 记录错误到 ErrorTracker（仅记录 5xx 错误）
    error_id = None
    if exc.status_code >= 500:
        try:
            from src.exceptions import DAASError, ErrorContext
            http_error = DAASError(
                message=str(exc.detail),
                error_code=f"HTTP_{exc.status_code}",
                context=ErrorContext(status_code=exc.status_code)
            )
            request_info = {
                'url': str(request.url),
                'method': request.method,
                'path': request.url.path,
            }
            error_id = get_error_tracker().log_error(
                http_error,
                request_info=request_info
            )
        except Exception as e:
            logger.warning(f"记录HTTP错误失败: {e}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": "HTTP_ERROR",
            "message": str(exc.detail),
            "error_id": error_id,
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.exception(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    
    # 记录错误到 ErrorTracker
    error_id = None
    try:
        from src.exceptions import DAASError, ErrorContext
        unhandled_error = DAASError(
            message=str(exc),
            error_code="UNHANDLED_ERROR",
            context=ErrorContext(exception_type=type(exc).__name__)
        )
        request_info = {
            'url': str(request.url),
            'method': request.method,
            'path': request.url.path,
        }
        error_id = get_error_tracker().log_error(
            unhandled_error,
            request_info=request_info
        )
    except Exception as e:
        logger.warning(f"记录未处理错误失败: {e}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": "服务器内部错误，请稍后重试。如问题持续，请联系技术支持并提供错误ID。",
            "error_id": error_id,
            "data": None
        }
    )


def _get_user_friendly_message(error_code: str, original_message: str) -> str:
    """
    获取用户友好的错误消息
    
    Args:
        error_code: 错误代码
        original_message: 原始错误消息
    
    Returns:
        用户友好的错误消息
    """
    # 错误消息映射
    message_map = {
        "DATA_FETCH_ERROR": "数据获取失败，请稍后重试",
        "DATA_VALIDATION_ERROR": "数据验证失败，请检查输入数据",
        "STRATEGY_ERROR": "策略执行失败，请检查策略配置",
        "FACTOR_ERROR": "因子计算失败，请检查因子配置",
        "CONFIGURATION_ERROR": "配置错误，请检查配置文件",
        "API_ERROR": "API调用失败，请稍后重试",
        "VALIDATION_ERROR": "请求参数验证失败，请检查输入参数",
        "HTTP_ERROR": "请求处理失败",
        "INTERNAL_ERROR": "服务器内部错误，请稍后重试",
        "UNHANDLED_ERROR": "发生未知错误，请联系技术支持",
    }
    
    # 优先使用映射的消息，否则使用原始消息（但简化技术细节）
    user_message = message_map.get(error_code, original_message)
    
    # 如果原始消息包含技术细节，尝试简化
    if "Traceback" in user_message or "File" in user_message:
        user_message = message_map.get(error_code, "操作失败，请稍后重试")
    
    return user_message
