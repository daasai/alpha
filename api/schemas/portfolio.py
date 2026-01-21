"""
Portfolio API Schemas
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class PortfolioPosition(BaseModel):
    """持仓（新模型）"""
    id: Optional[int] = Field(None, description="持仓ID")
    ts_code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    total_vol: int = Field(..., description="总持仓量", ge=0)
    avail_vol: int = Field(..., description="可用持仓量", ge=0)
    avg_price: float = Field(..., description="平均成本价", ge=0)
    current_price: Optional[float] = Field(None, description="当前价格", gt=0)
    profit: float = Field(default=0.0, description="浮动盈亏")
    profit_pct: float = Field(default=0.0, description="盈亏百分比")


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


class BuyOrderRequest(BaseModel):
    """买入订单请求"""
    ts_code: str = Field(..., description="股票代码")
    price: float = Field(..., description="买入价格", gt=0)
    volume: int = Field(..., description="买入数量", gt=0)
    strategy_tag: Optional[str] = Field(None, description="策略标签")


class SellOrderRequest(BaseModel):
    """卖出订单请求"""
    ts_code: str = Field(..., description="股票代码")
    price: float = Field(..., description="卖出价格", gt=0)
    volume: int = Field(..., description="卖出数量", gt=0)
    reason: Optional[str] = Field(None, description="卖出原因")


class OrderRequest(BaseModel):
    """统一订单请求"""
    action: Literal['BUY', 'SELL'] = Field(..., description="订单动作：BUY 或 SELL")
    ts_code: str = Field(..., description="股票代码")
    price: float = Field(..., description="成交价格", gt=0)
    volume: int = Field(..., description="成交数量", gt=0)
    strategy_tag: Optional[str] = Field(None, description="策略标签（买入时可选）")
    reason: Optional[str] = Field(None, description="卖出原因（卖出时可选）")


class OrderResponse(BaseModel):
    """订单响应"""
    order_id: str = Field(..., description="订单ID")
    trade_date: str = Field(..., description="交易日期")
    ts_code: str = Field(..., description="股票代码")
    action: str = Field(..., description="动作（BUY/SELL）")
    price: float = Field(..., description="成交价格")
    volume: int = Field(..., description="成交数量")
    fee: float = Field(..., description="手续费")
    status: str = Field(..., description="状态（FILLED/CANCELLED）")
    strategy_tag: Optional[str] = Field(None, description="策略标签")
    reason: Optional[str] = Field(None, description="卖出原因")
    created_at: Optional[str] = Field(None, description="创建时间")


class AccountResponse(BaseModel):
    """账户响应"""
    id: int = Field(..., description="账户ID")
    total_asset: float = Field(..., description="总资产")
    cash: float = Field(..., description="现金")
    market_value: float = Field(..., description="市值")
    frozen_cash: float = Field(..., description="冻结资金")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
