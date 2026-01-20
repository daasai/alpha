"""
Dashboard API Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date


class MarketRegimeResponse(BaseModel):
    """市场状态响应"""
    regime: str = Field(..., description="市场状态：多头 (进攻) 或 空头 (防守)")
    is_bull: bool = Field(..., description="是否为多头市场")


class SentimentResponse(BaseModel):
    """赚钱效应响应"""
    sentiment: float = Field(..., description="赚钱效应百分比", ge=0, le=100)
    change: Optional[float] = Field(None, description="变化百分比")


class TargetPositionResponse(BaseModel):
    """建议仓位响应"""
    position: float = Field(..., description="建议仓位百分比", ge=0, le=100)
    label: str = Field(..., description="仓位标签，如 'Full On'")


class PortfolioNAVResponse(BaseModel):
    """组合净值响应"""
    nav: float = Field(..., description="组合净值")
    change_percent: Optional[float] = Field(None, description="今日变化百分比")


class MarketTrendDataPoint(BaseModel):
    """市场趋势数据点"""
    date: str = Field(..., description="日期 (YYYY-MM-DD)")
    price: float = Field(..., description="价格")
    bbi: float = Field(..., description="BBI指标值")


class DashboardOverviewResponse(BaseModel):
    """Dashboard概览响应"""
    market_regime: MarketRegimeResponse
    sentiment: SentimentResponse
    target_position: TargetPositionResponse
    portfolio_nav: PortfolioNAVResponse


class MarketTrendResponse(BaseModel):
    """市场趋势响应"""
    index_code: str = Field(..., description="指数代码")
    index_name: str = Field(..., description="指数名称")
    data: List[MarketTrendDataPoint] = Field(..., description="趋势数据")
