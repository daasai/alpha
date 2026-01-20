"""
Lab API Router
"""
from fastapi import APIRouter, Depends, Body

from api.dependencies import get_data_provider, get_config
from api.services.lab_service import APILabService
from api.schemas.lab import (
    BacktestRequest,
    BacktestResponse
)
from api.utils.responses import success_response
from src.data_provider import DataProvider
from src.config_manager import ConfigManager

router = APIRouter()


def get_lab_service(
    data_provider: DataProvider = Depends(get_data_provider),
    config: ConfigManager = Depends(get_config)
) -> APILabService:
    """获取Lab服务实例"""
    return APILabService(data_provider, config)


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(
    request: BacktestRequest = Body(...),
    service: APILabService = Depends(get_lab_service)
):
    """
    运行回测
    
    基于Alpha Trident策略进行历史回测
    """
    try:
        result = service.run_backtest(
            start_date=request.start_date,
            end_date=request.end_date,
            holding_days=request.holding_days,
            stop_loss_pct=request.stop_loss_pct,
            cost_rate=request.cost_rate,
            benchmark_code=request.benchmark_code,
            index_code=request.index_code,
            max_positions=request.max_positions
        )
        return success_response(data=result)
    except Exception as e:
        from src.logging_config import get_logger
        logger = get_logger(__name__)
        logger.exception(f"回测路由异常: {type(e).__name__}: {str(e)}")
        # 如果服务层已经返回了错误结果，直接返回
        # 否则抛出异常让异常处理器处理
        raise
