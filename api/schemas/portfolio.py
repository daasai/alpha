"""
Portfolio API Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class PortfolioPosition(BaseModel):
    """持仓"""
    id: Optional[str] = Field(None, description="持仓ID")
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    cost: float = Field(..., description="成本价", gt=0)
    current_price: float = Field(..., description="当前价格", gt=0)
    shares: int = Field(..., description="持仓数量", gt=0)
    stop_loss_price: float = Field(..., description="止损价", gt=0)


class PortfolioMetrics(BaseModel):
    """组合指标"""
    total_return: float = Field(..., description="总收益率（百分比）")
    max_drawdown: float = Field(..., description="最大回撤（百分比）")
    sharpe_ratio: float = Field(..., description="夏普比率")


class PortfolioPositionsResponse(BaseModel):
    """持仓列表响应"""
    positions: List[PortfolioPosition] = Field(default_factory=list, description="持仓列表")


class PortfolioMetricsResponse(BaseModel):
    """组合指标响应"""
    metrics: PortfolioMetrics = Field(..., description="组合指标")


class AddPositionRequest(BaseModel):
    """添加持仓请求"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    cost: float = Field(..., description="成本价", gt=0)
    shares: Optional[int] = Field(None, description="持仓数量，如果未提供则使用配置默认值", gt=0)
    stop_loss_price: Optional[float] = Field(None, description="止损价，如果未提供则使用配置默认值", gt=0)


class UpdatePositionRequest(BaseModel):
    """更新持仓请求"""
    cost: Optional[float] = Field(None, description="成本价", gt=0)
    shares: Optional[int] = Field(None, description="持仓数量", gt=0)
    stop_loss_price: Optional[float] = Field(None, description="止损价", gt=0)
