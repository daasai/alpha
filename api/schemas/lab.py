"""
Lab API Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    """回测请求"""
    start_date: str = Field(..., description="开始日期 (YYYYMMDD)")
    end_date: str = Field(..., description="结束日期 (YYYYMMDD)")
    holding_days: int = Field(5, description="持仓天数", ge=1, le=30)
    stop_loss_pct: float = Field(0.08, description="止损百分比", ge=0, le=1)
    cost_rate: float = Field(0.002, description="交易成本率", ge=0, le=0.01)
    benchmark_code: str = Field("000300.SH", description="基准指数代码")
    index_code: Optional[str] = Field(None, description="股票池指数代码")
    max_positions: Optional[int] = Field(None, description="最大持仓数")
    rps_threshold: Optional[float] = Field(None, description="RPS阈值，默认使用配置值")


class EquityCurvePoint(BaseModel):
    """权益曲线数据点"""
    date: str = Field(..., description="日期 (YYYY-MM-DD)")
    strategy_equity: float = Field(..., description="策略净值")
    benchmark_equity: float = Field(..., description="基准净值")


class TopContributor(BaseModel):
    """Top贡献者"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    total_gain: float = Field(..., description="总收益（元）")
    total_gain_pct: float = Field(..., description="总收益百分比")


class BacktestMetrics(BaseModel):
    """回测指标"""
    total_return: float = Field(..., description="总收益率（百分比）")
    benchmark_return: float = Field(..., description="基准收益率（百分比）")
    max_drawdown: float = Field(..., description="最大回撤（百分比）")
    win_rate: Optional[float] = Field(None, description="胜率（百分比）")
    sharpe_ratio: Optional[float] = Field(None, description="夏普比率")
    total_trades: Optional[int] = Field(None, description="总交易数")


class BacktestResponse(BaseModel):
    """回测响应"""
    success: bool = Field(..., description="是否成功")
    metrics: Optional[BacktestMetrics] = Field(None, description="回测指标")
    equity_curve: List[EquityCurvePoint] = Field(default_factory=list, description="权益曲线")
    top_winners: List[TopContributor] = Field(default_factory=list, description="Top Winners")
    top_losers: List[TopContributor] = Field(default_factory=list, description="Top Losers")
    error: Optional[str] = Field(None, description="错误信息")
