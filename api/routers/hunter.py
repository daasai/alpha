"""
Hunter API Router
"""
from fastapi import APIRouter, Depends, Body
from typing import Optional

from api.dependencies import get_data_provider, get_config
from api.services.hunter_service import APIHunterService
from api.schemas.hunter import (
    HunterScanRequest,
    HunterScanResponse,
    HunterFiltersResponse
)
from api.utils.responses import success_response
from src.data_provider import DataProvider
from src.config_manager import ConfigManager

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
    result = service.run_scan(
        trade_date=request.trade_date,
        rps_threshold=request.rps_threshold,
        volume_ratio_threshold=request.volume_ratio_threshold
    )
    return success_response(data=result)


@router.get("/filters", response_model=HunterFiltersResponse)
async def get_filters(
    service: APIHunterService = Depends(get_hunter_service)
):
    """
    获取可用筛选条件
    
    返回RPS阈值、量比阈值、PE最大值等配置
    """
    filters = service.get_filters()
    return success_response(data=filters)
