"""
Hunter API Router
"""
from fastapi import APIRouter, Depends, Body, HTTPException
from typing import Optional

from api.dependencies import get_data_provider, get_config
from api.services.hunter_service import APIHunterService
from api.schemas.hunter import (
    HunterScanRequest,
    HunterScanResponse,
    HunterFiltersResponse
)
from api.utils.responses import success_response, error_response
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_hunter_service(
    data_provider: DataProvider = Depends(get_data_provider),
    config: ConfigManager = Depends(get_config)
) -> APIHunterService:
    """获取Hunter服务实例"""
    return APIHunterService(data_provider, config)


@router.post("/scan", response_model=HunterScanResponse)
async def scan_stocks(
    request: HunterScanRequest = Body(...),
    service: APIHunterService = Depends(get_hunter_service)
):
    """
    执行Hunter扫描
    
    基于Alpha Trident策略筛选符合条件的股票
    """
    try:
        result = service.run_scan(
            trade_date=request.trade_date,
            rps_threshold=request.rps_threshold,
            volume_ratio_threshold=request.volume_ratio_threshold
        )
        return success_response(data=result)
    except Exception as e:
        logger.exception("Hunter扫描API异常")
        # 如果服务层已经返回了错误响应，直接返回
        # 否则抛出HTTP异常
        raise HTTPException(
            status_code=500,
            detail=f"扫描过程发生错误: {str(e)}"
        )


@router.get("/filters", response_model=HunterFiltersResponse)
async def get_filters(
    service: APIHunterService = Depends(get_hunter_service)
):
    """
    获取可用筛选条件
    
    返回RPS阈值、量比阈值、PE最大值等配置，以及可用交易日期列表
    """
    try:
        filters = service.get_filters()
        return success_response(data=filters)
    except Exception as e:
        logger.exception("获取筛选条件API异常")
        raise HTTPException(
            status_code=500,
            detail=f"获取筛选条件失败: {str(e)}"
        )


@router.get("/history")
async def get_history(
    service: APIHunterService = Depends(get_hunter_service)
):
    """
    获取历史扫描记录
    
    返回历史扫描结果列表（如果数据库中有存储）
    目前作为占位符，返回空列表
    """
    try:
        # TODO: 如果将来需要存储扫描历史，可以从数据库查询
        # 目前返回空列表作为占位符
        return success_response(data=[])
    except Exception as e:
        logger.exception("获取历史记录API异常")
        raise HTTPException(
            status_code=500,
            detail=f"获取历史记录失败: {str(e)}"
        )
