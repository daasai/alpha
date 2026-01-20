"""
API Response Utilities
"""
from typing import Any, Optional
from fastapi.responses import JSONResponse
from fastapi import status


def success_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = status.HTTP_200_OK
) -> JSONResponse:
    """
    成功响应
    
    Args:
        data: 响应数据
        message: 响应消息
        status_code: HTTP状态码
        
    Returns:
        JSONResponse
    """
    content = {
        "success": True,
        "data": data,
        "error": None,
    }
    if message:
        content["message"] = message
    
    return JSONResponse(status_code=status_code, content=content)


def error_response(
    error: str,
    message: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    data: Any = None
) -> JSONResponse:
    """
    错误响应
    
    Args:
        error: 错误代码
        message: 错误消息
        status_code: HTTP状态码
        data: 可选的错误数据
        
    Returns:
        JSONResponse
    """
    content = {
        "success": False,
        "error": error,
        "message": message,
        "data": data
    }
    
    return JSONResponse(status_code=status_code, content=content)
