"""
Portfolio API Router
"""
from fastapi import APIRouter, Depends, Path, HTTPException, status
from typing import List

from api.dependencies import get_data_provider, get_config
from api.services.portfolio_service import PortfolioService
from api.schemas.portfolio import (
    PortfolioPosition,
    PortfolioPositionsResponse,
    PortfolioMetricsResponse,
    AddPositionRequest,
    UpdatePositionRequest
)
from api.utils.responses import success_response
from src.data_provider import DataProvider
from src.config_manager import ConfigManager

router = APIRouter()


def get_portfolio_service(
    data_provider: DataProvider = Depends(get_data_provider),
    config: ConfigManager = Depends(get_config)
) -> PortfolioService:
    """获取Portfolio服务实例"""
    return PortfolioService(data_provider, config)


@router.get("/positions", response_model=PortfolioPositionsResponse)
async def get_positions(
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    获取持仓列表
    
    返回所有持仓及其最新价格
    """
    positions = service.get_positions()
    return success_response(data={"positions": positions})


@router.get("/metrics", response_model=PortfolioMetricsResponse)
async def get_metrics(
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    获取组合指标
    
    返回总收益、最大回撤、夏普比率
    """
    metrics = service.get_metrics()
    return success_response(data={"metrics": metrics})


@router.post("/positions", response_model=PortfolioPosition, status_code=status.HTTP_201_CREATED)
async def add_position(
    request: AddPositionRequest,
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    添加持仓
    
    将股票添加到模拟组合
    """
    position_data = request.dict()
    position = service.add_position(position_data)
    return success_response(data=position, status_code=status.HTTP_201_CREATED)


@router.put("/positions/{position_id}", response_model=PortfolioPosition)
async def update_position(
    position_id: str = Path(..., description="持仓ID"),
    request: UpdatePositionRequest = ...,
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    更新持仓
    
    更新持仓的成本、数量或止损价
    """
    update_data = request.dict(exclude_unset=True)
    position = service.update_position(position_id, update_data)
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="持仓不存在"
        )
    
    return success_response(data=position)


@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: str = Path(..., description="持仓ID"),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    删除持仓
    
    从模拟组合中移除持仓
    """
    success = service.delete_position(position_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="持仓不存在"
        )
    
    return None


@router.post("/refresh-prices")
async def refresh_prices(
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    刷新持仓价格
    
    更新所有持仓的最新价格
    """
    result = service.refresh_prices()
    return success_response(data=result)
