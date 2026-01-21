"""
Portfolio API Router
"""
from fastapi import APIRouter, Depends, Path, HTTPException, status, Query
from typing import List, Optional

from api.dependencies import get_data_provider, get_config, get_portfolio_repository
from api.services.portfolio_service import PortfolioService
from api.schemas.portfolio import (
    PortfolioPosition,
    PortfolioPositionsResponse,
    PortfolioMetricsResponse,
    AddPositionRequest,
    UpdatePositionRequest,
    BuyOrderRequest,
    SellOrderRequest,
    OrderRequest,
    OrderResponse,
    AccountResponse,
)
from api.utils.responses import success_response
from api.utils.exceptions import PositionNotFoundError
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.repositories.portfolio_repository import PortfolioRepository

router = APIRouter()


def get_portfolio_service(
    data_provider: DataProvider = Depends(get_data_provider),
    config: ConfigManager = Depends(get_config),
    repository: PortfolioRepository = Depends(get_portfolio_repository)
) -> PortfolioService:
    """获取Portfolio服务实例"""
    return PortfolioService(data_provider, config, repository)


@router.get("/overview")
async def get_portfolio_overview(
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    获取组合概览和持仓
    
    返回账户信息和持仓列表（自动同步最新价格以确保实时净值）
    """
    status_data = service.get_portfolio_status()
    return success_response(data=status_data)


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


# 注意：旧的 update_position 端点已移除
# 请使用新的 /buy 和 /sell 端点来执行交易
# 持仓可以通过买入订单创建，通过卖出订单减少或删除
# 但为了管理方便，保留了 add_position 和 delete_position 端点用于直接管理持仓

@router.post("/positions", response_model=PortfolioPositionsResponse, status_code=status.HTTP_201_CREATED)
async def add_position(
    request: AddPositionRequest,
    service: PortfolioService = Depends(get_portfolio_service),
    data_provider: DataProvider = Depends(get_data_provider)
):
    """
    添加持仓（兼容端点）
    
    内部使用 /buy 端点来执行买入订单
    """
    try:
        # 尝试获取当前价格（如果没有提供，使用成本价）
        try:
            current_price = data_provider.get_latest_price(request.code)
            if current_price is None or current_price <= 0:
                current_price = request.cost
        except:
            current_price = request.cost
        
        # 使用 /buy 端点逻辑
        order = service.execute_buy(
            ts_code=request.code,
            price=current_price,
            volume=request.shares or 100,  # 默认100股
            strategy_tag=None
        )
        
        # 返回更新后的持仓列表
        positions = service.get_positions()
        return success_response(data={"positions": positions}, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        from api.utils.exceptions import (
            AccountNotInitializedError,
            InsufficientFundsError,
        )
        if isinstance(e, AccountNotInitializedError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        elif isinstance(e, InsufficientFundsError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise

@router.delete("/positions/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: int = Path(..., description="持仓ID"),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    删除持仓
    
    直接删除指定的持仓（用于管理目的）
    """
    try:
        success = service.delete_position(position_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"持仓 ID {position_id} 不存在"
            )
    except PositionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.post("/refresh-prices")
async def refresh_prices(
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    刷新持仓价格
    
    更新所有持仓的最新价格
    """
    result = service.sync_latest_prices()
    return success_response(data=result)


@router.post("/buy", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def execute_buy(
    request: BuyOrderRequest,
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    执行买入订单
    
    买入股票并更新账户和持仓
    """
    try:
        order = service.execute_buy(
            ts_code=request.ts_code,
            price=request.price,
            volume=request.volume,
            strategy_tag=request.strategy_tag
        )
        return success_response(data=order, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        from api.utils.exceptions import (
            AccountNotInitializedError,
            InsufficientFundsError,
        )
        if isinstance(e, AccountNotInitializedError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        elif isinstance(e, InsufficientFundsError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise


@router.post("/sell", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def execute_sell(
    request: SellOrderRequest,
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    执行卖出订单
    
    卖出股票并更新账户和持仓
    """
    try:
        order = service.execute_sell(
            ts_code=request.ts_code,
            price=request.price,
            volume=request.volume,
            reason=request.reason
        )
        return success_response(data=order, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        from api.utils.exceptions import (
            PositionNotFoundError,
            InsufficientVolumeError,
        )
        if isinstance(e, PositionNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif isinstance(e, InsufficientVolumeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise


@router.get("/account", response_model=AccountResponse)
async def get_account(
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    获取账户信息
    
    返回账户的现金、市值、总资产等信息
    """
    account = service.get_account()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户未初始化"
        )
    return success_response(data=account)


@router.get("/history")
async def get_order_history(
    limit: Optional[int] = Query(50, ge=1, le=500, description="返回的最大订单数量"),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    获取订单历史/交易记录
    
    返回最近的订单列表，按创建时间倒序排列
    """
    orders = service.get_order_history(limit=limit)
    return success_response(data={"orders": orders})


@router.post("/order", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def execute_order(
    request: OrderRequest,
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    执行买入/卖出订单（统一端点）
    
    根据 action 字段执行买入或卖出操作
    """
    try:
        order = service.execute_order(
            action=request.action,
            ts_code=request.ts_code,
            price=request.price,
            volume=request.volume,
            strategy_tag=request.strategy_tag,
            reason=request.reason
        )
        return success_response(data=order, status_code=status.HTTP_201_CREATED)
    except Exception as e:
        from api.utils.exceptions import (
            AccountNotInitializedError,
            InsufficientFundsError,
            PositionNotFoundError,
            InsufficientVolumeError,
        )
        if isinstance(e, AccountNotInitializedError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        elif isinstance(e, InsufficientFundsError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        elif isinstance(e, PositionNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        elif isinstance(e, InsufficientVolumeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise
