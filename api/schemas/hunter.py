"""
Hunter API Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class HunterScanRequest(BaseModel):
    """Hunter扫描请求"""
    trade_date: Optional[str] = Field(None, description="交易日期 (YYYYMMDD)，默认最新交易日")
    rps_threshold: Optional[float] = Field(None, description="RPS阈值，默认使用配置值")
    volume_ratio_threshold: Optional[float] = Field(None, description="量比阈值，默认使用配置值")


class StockSignal(BaseModel):
    """股票信号模型 - 符合需求规范的完整模型"""
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    rps: float = Field(..., ge=0, le=100, description="RPS强度 (0-100)")
    volume_ratio: float = Field(..., description="量比")
    pe: Optional[float] = Field(None, description="PE比率")
    industry: Optional[str] = Field(None, description="行业")
    reason: Optional[str] = Field(None, description="选择原因")


class HunterStockResult(BaseModel):
    """Hunter扫描结果中的股票（向后兼容）"""
    id: str = Field(..., description="唯一标识")
    code: str = Field(..., description="股票代码")
    name: str = Field(..., description="股票名称")
    price: float = Field(..., description="当前价格")
    change_percent: float = Field(..., description="涨跌幅百分比")
    rps: float = Field(..., description="RPS强度")
    volume_ratio: float = Field(..., description="量比")
    pe: Optional[float] = Field(None, description="PE比率")
    industry: Optional[str] = Field(None, description="行业")
    reason: Optional[str] = Field(None, description="选择原因")
    ai_analysis: Optional[str] = Field(None, description="AI分析")


class HunterScanDiagnostics(BaseModel):
    """Hunter扫描诊断信息"""
    total_stocks: int = Field(..., description="总股票数")
    stocks_with_enough_data: int = Field(..., description="有足够历史数据的股票数")
    history_records: int = Field(..., description="历史记录数")
    enriched_records: int = Field(..., description="增强记录数")
    result_count: int = Field(..., description="结果数量")
    rps_stats: Optional[dict] = Field(None, description="RPS统计信息")


class HunterScanResponse(BaseModel):
    """Hunter扫描响应"""
    success: bool = Field(..., description="是否成功")
    trade_date: Optional[str] = Field(None, description="交易日期")
    results: List[StockSignal] = Field(default_factory=list, description="扫描结果")
    diagnostics: Optional[HunterScanDiagnostics] = Field(None, description="诊断信息")
    error: Optional[str] = Field(None, description="错误信息")


class TradeDateOption(BaseModel):
    """交易日期选项"""
    value: str = Field(..., description="日期值 (YYYYMMDD)")
    label: str = Field(..., description="显示标签 (YYYY-MM-DD)")


class HunterFiltersResponse(BaseModel):
    """Hunter筛选条件响应"""
    rps_threshold: dict = Field(..., description="RPS阈值配置")
    volume_ratio_threshold: dict = Field(..., description="量比阈值配置")
    pe_max: dict = Field(..., description="最大PE配置")
    available_dates: List[TradeDateOption] = Field(default_factory=list, description="可用交易日期列表")
