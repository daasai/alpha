"""
Dashboard API Router
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional

from api.dependencies import get_data_provider, get_config, get_portfolio_repository
from api.services.dashboard_service import DashboardService
from api.schemas.dashboard import (
    DashboardOverviewResponse,
    MarketTrendResponse
)
from api.utils.responses import success_response
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.repositories.portfolio_repository import PortfolioRepository

router = APIRouter()


def get_dashboard_service(
    data_provider: DataProvider = Depends(get_data_provider),
    config: ConfigManager = Depends(get_config),
    portfolio_repository: PortfolioRepository = Depends(get_portfolio_repository)
) -> DashboardService:
    """获取Dashboard服务实例"""
    return DashboardService(data_provider, config, portfolio_repository)


@router.get("/overview", response_model=DashboardOverviewResponse)
async def get_overview(
    trade_date: Optional[str] = Query(None, description="交易日期 (YYYYMMDD)，默认最新交易日"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    获取市场概览
    
    返回市场状态、赚钱效应、建议仓位、组合净值
    """
    result = service.get_overview(trade_date)
    return success_response(data=result)


@router.get("/market-trend", response_model=MarketTrendResponse)
async def get_market_trend(
    days: int = Query(60, description="获取天数", ge=1, le=365),
    index_code: str = Query("000001.SH", description="指数代码"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    获取市场趋势数据（指数价格和BBI）
    
    返回指定天数的指数收盘价和BBI指标数据
    """
    result = service.get_market_trend(days=days, index_code=index_code)
    return success_response(data=result)
