"""
API Exception Handlers
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
)
from src.logging_config import get_logger

logger = get_logger(__name__)


class APIException(Exception):
    """API异常基类"""
    def __init__(self, message: str, status_code: int = 500, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        super().__init__(self.message)


def map_daas_error_to_api_error(error: DAASError) -> APIException:
    """将DAAS错误映射为API异常"""
    if isinstance(error, DataFetchError):
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
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.error_code,
            "message": exc.message,
            "data": None
        }
    )


async def daas_exception_handler(request: Request, exc: DAASError):
    """DAAS异常处理器"""
    api_exc = map_daas_error_to_api_error(exc)
    return await api_exception_handler(request, api_exc)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "VALIDATION_ERROR",
            "message": "请求参数验证失败",
            "data": exc.errors()
        }
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理器"""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "data": None
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    logger.exception(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "INTERNAL_ERROR",
            "message": "服务器内部错误",
            "data": None
        }
    )
