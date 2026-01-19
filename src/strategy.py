"""
Strategy Module - "价值守门员" (The Anchor)
核心选股逻辑：基于价值和质量因子的多因子筛选
"""

import pandas as pd
import numpy as np
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


def get_trade_date(dt=None):
    """
    获取交易日期。
    若 dt 为 None 则用当前日期；若为周末则向前推到上一交易日。
    若当前时间 < 17:00，则返回上一个交易日（Tushare 当日数据需在收盘后处理，17:00 完成更新）。
    返回 %Y%m%d。
    """
    from datetime import datetime, timedelta
    now = datetime.now()
    
    if dt is None:
        # 如果当前时间 < 17:00，使用上一个交易日
        if now.hour < 17:
            d = now - timedelta(days=1)
        else:
            d = now
    else:
        d = dt if isinstance(dt, datetime) else datetime.strptime(str(dt)[:10], "%Y-%m-%d")
    
    # 向前推到上一交易日（跳过周末）
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    
    return d.strftime("%Y%m%d")


def run_screening(trade_date=None, data_provider=None, risk_budget: float = 10000.0):
    """
    v1.1 筛选逻辑：
    1. 硬过滤：移除ST/退市、亏损股(pe_ttm<0)、高PB股(pb>20)
    2. 杠铃策略：添加strategy_tag（防守/进攻），过滤不匹配标签的股票
    3. ATR仓位计算：计算suggested_shares
    
    返回 df 含 ts_code, name, pe_ttm, pb, roe, mv, dividend_yield, strategy_tag, suggested_shares, trade_date。
    data_provider 需实现 get_daily_basic(trade_date), get_roe(trade_date, ts_codes), 
    filter_new_stocks(df, trade_date), calculate_atr(ts_code, trade_date)。
    """
    if data_provider is None:
        from .data_provider import DataProvider
        data_provider = DataProvider()
    trade_date = trade_date or get_trade_date()
    
    # 1. 获取基础数据
    basic = data_provider.get_daily_basic(trade_date)
    if basic.empty:
        logger.warning("run_screening: get_daily_basic 返回空数据")
        return pd.DataFrame()
    
    # 2. 过滤新股（上市不足6个月）
    basic = data_provider.filter_new_stocks(basic, trade_date)
    if basic.empty:
        logger.warning("run_screening: 过滤新股后无数据")
        return pd.DataFrame()
    
    # 3. 硬过滤规则
    # 3.1 移除ST/退市股票（通过名称判断）
    before_st = len(basic)
    basic = basic[~basic["name"].str.contains("ST|\\*ST|退", regex=True, na=False)]
    logger.debug(f"硬过滤-ST/退市: {before_st} -> {len(basic)}")
    
    # 3.2 移除亏损股 (pe_ttm < 0)
    before_loss = len(basic)
    basic = basic.dropna(subset=["pe_ttm"])
    basic = basic[basic["pe_ttm"] > 0]
    logger.debug(f"硬过滤-亏损股: {before_loss} -> {len(basic)}")
    
    # 3.3 移除高PB股 (pb > 20)
    before_pb = len(basic)
    basic = basic.dropna(subset=["pb"])
    basic = basic[basic["pb"] <= 20]
    logger.debug(f"硬过滤-高PB: {before_pb} -> {len(basic)}")
    
    if basic.empty:
        logger.warning("run_screening: 硬过滤后无数据")
        return pd.DataFrame()
    
    # 4. 获取ROE
    roe_df = data_provider.get_roe(trade_date, basic["ts_code"].tolist())
    if roe_df.empty:
        logger.warning("run_screening: get_roe 返回空数据")
        return pd.DataFrame()
    
    merged = basic.merge(roe_df, on="ts_code", how="inner")
    merged = merged.dropna(subset=["roe"])
    
    # dividend_yield 已从 get_daily_basic 获取
    if "dividend_yield" not in merged.columns:
        merged["dividend_yield"] = 0.0
    
    if merged.empty:
        logger.warning("run_screening: 合并ROE后无数据")
        return pd.DataFrame()
    
    # 5. 杠铃策略标签
    # 🛡️ 防守: dividend_yield > 3 AND pe_ttm < 15
    # 🚀 进攻: roe > 12 AND mv < 50000000000 (50亿，单位：万元)
    merged["strategy_tag"] = ""
    defensive_mask = (merged["dividend_yield"] > 3) & (merged["pe_ttm"] < 15)
    aggressive_mask = (merged["roe"] > 12) & (merged["mv"] < 50000000000)
    
    merged.loc[defensive_mask, "strategy_tag"] = "防守"
    merged.loc[aggressive_mask, "strategy_tag"] = "进攻"
    
    # 过滤：只保留有标签的股票
    before_barbell = len(merged)
    merged = merged[merged["strategy_tag"] != ""]
    logger.debug(f"杠铃策略过滤: {before_barbell} -> {len(merged)}")
    
    if merged.empty:
        logger.warning("run_screening: 杠铃策略过滤后无数据")
        return pd.DataFrame()
    
    # 6. ATR仓位计算
    merged["suggested_shares"] = 0
    for idx, row in merged.iterrows():
        ts_code = row["ts_code"]
        atr = data_provider.calculate_atr(ts_code, trade_date, period=20)
        if atr > 0:
            # suggested_shares = floor(risk_budget / ATR / 100) * 100
            shares = (risk_budget / atr) // 100 * 100
            merged.at[idx, "suggested_shares"] = int(max(0, shares))
        else:
            merged.at[idx, "suggested_shares"] = 0
    
    # 7. 选择输出列
    out = merged[[
        "ts_code", "name", "pe_ttm", "pb", "roe", "mv", 
        "dividend_yield", "strategy_tag", "suggested_shares"
    ]].copy()
    out["trade_date"] = trade_date
    
    logger.info(f"run_screening 完成: {len(out)} 只股票")
    return out.reset_index(drop=True)


class StockStrategy:
    """股票筛选策略类"""
    
    def __init__(self, config_path='config/settings.yaml'):
        """
        初始化策略，加载配置参数
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.pe_ttm_max = self.config['pe_ttm_max']
        self.pb_max = self.config['pb_max']
        self.roe_min = self.config['roe_min']
        self.dividend_yield_min = self.config['dividend_yield_min']
        self.listing_days_min = self.config['listing_days_min']
    
    def _load_config(self, config_path):
        """加载配置文件"""
        config_file = Path(config_path)
        if not config_file.exists():
            logger.error(f"配置文件不存在: {config_path}")
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.debug(f"配置加载成功: {config_path}")
        return config
    
    def filter_stocks(self, stock_basics, daily_indicators, financial_indicators):
        """
        执行多因子筛选，生成白名单股票池
        
        Args:
            stock_basics: 股票基本信息 DataFrame
            daily_indicators: 每日指标 DataFrame
            financial_indicators: 财务指标 DataFrame
            
        Returns:
            pd.DataFrame: 筛选后的股票池，包含所有相关因子数据
        """
        logger.info(f"开始筛选股票: 基础数据 {len(stock_basics)} 只, 每日指标 {len(daily_indicators)} 条, 财务指标 {len(financial_indicators)} 条")
        
        # 合并数据
        df = stock_basics.copy()
        
        # 合并每日指标
        df = df.merge(
            daily_indicators[['ts_code', 'pe_ttm', 'pb', 'dividend_yield', 'total_market_cap']],
            on='ts_code',
            how='inner'
        )
        
        # 合并财务指标
        df = df.merge(
            financial_indicators[['ts_code', 'roe']],
            on='ts_code',
            how='left'  # 使用 left join，因为不是所有股票都有财务数据
        )
        
        # 筛选规则 1: 排除垃圾股
        # 排除 ST/*ST 股票
        before_st = len(df)
        df = df[~df['is_st']]
        logger.debug(f"排除ST股票: {before_st} -> {len(df)}")
        
        # 排除新股（上市时间 < 365 天）
        today = datetime.now()
        df['list_date'] = pd.to_datetime(df['list_date'], format='%Y%m%d', errors='coerce')
        df['listing_days'] = (today - df['list_date']).dt.days
        before_new = len(df)
        df = df[df['listing_days'] >= self.listing_days_min]
        logger.debug(f"排除新股: {before_new} -> {len(df)}")
        
        # 筛选规则 2: 估值安全 (Value)
        # 0 < PE_TTM < threshold 且 PB < threshold
        before_value = len(df)
        df = df[
            (df['pe_ttm'] > 0) & 
            (df['pe_ttm'] < self.pe_ttm_max) & 
            (df['pb'] > 0) & 
            (df['pb'] < self.pb_max)
        ]
        logger.debug(f"估值筛选 (PE<{self.pe_ttm_max}, PB<{self.pb_max}): {before_value} -> {len(df)}")
        
        # 筛选规则 3: 盈利能力 (Quality)
        # ROE > threshold (百分比)
        before_quality = len(df)
        df = df[df['roe'] > self.roe_min]
        logger.debug(f"盈利能力筛选 (ROE>{self.roe_min}%): {before_quality} -> {len(df)}")
        
        # 筛选规则 4: 分红回报 (Yield)
        # 股息率 > threshold (百分比)
        before_yield = len(df)
        df = df[df['dividend_yield'] > self.dividend_yield_min]
        logger.debug(f"分红筛选 (股息率>{self.dividend_yield_min}%): {before_yield} -> {len(df)}")
        
        # 移除 NaN 值
        before_nan = len(df)
        df = df.dropna(subset=['pe_ttm', 'pb', 'roe', 'dividend_yield'])
        logger.debug(f"移除NaN值: {before_nan} -> {len(df)}")
        
        # 选择输出列
        result = df[[
            'ts_code',
            'name',
            'industry',
            'pe_ttm',
            'pb',
            'roe',
            'dividend_yield',
            'total_market_cap',
            'listing_days'
        ]].copy()
        
        # 按 ROE 降序排序
        result = result.sort_values('roe', ascending=False).reset_index(drop=True)
        
        logger.info(f"筛选完成: 最终白名单 {len(result)} 只股票")
        return result
