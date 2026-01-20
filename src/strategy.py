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
    
    # 6. ATR仓位计算（并发优化）
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm
    
    merged["suggested_shares"] = 0
    
    def calculate_atr_for_stock(args):
        """计算单个股票的ATR和suggested_shares"""
        idx, ts_code, trade_date, risk_budget, data_provider = args
        try:
            atr = data_provider.calculate_atr(ts_code, trade_date, period=20)
            if atr > 0:
                # suggested_shares = floor(risk_budget / ATR / 100) * 100
                shares = (risk_budget / atr) // 100 * 100
                return (idx, int(max(0, shares)))
            else:
                return (idx, 0)
        except Exception as e:
            logger.debug(f"calculate_atr {ts_code} 失败: {e}")
            return (idx, 0)
    
    # 并发计算ATR（从配置读取并发数）
    atr_args = [
        (idx, row["ts_code"], trade_date, risk_budget, data_provider)
        for idx, row in merged.iterrows()
    ]
    
    try:
        from .config_manager import ConfigManager
        config = ConfigManager()
        max_workers = config.get('concurrency.atr_workers', 10)
    except Exception:
        max_workers = 10
    logger.info(f"开始并发计算ATR，共 {len(atr_args)} 只股票，并发数: {max_workers}")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(calculate_atr_for_stock, args): args[0]
            for args in atr_args
        }
        
        with tqdm(total=len(atr_args), desc="ATR计算进度", unit="只", ncols=80) as pbar:
            for future in as_completed(future_to_idx):
                try:
                    idx, shares = future.result()
                    merged.at[idx, "suggested_shares"] = shares
                except Exception as e:
                    idx = future_to_idx[future]
                    logger.debug(f"ATR计算任务异常 {merged.iloc[idx]['ts_code']}: {e}")
                    merged.at[idx, "suggested_shares"] = 0
                finally:
                    pbar.update(1)
    
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


class AlphaStrategy:
    """
    Alpha Trident Strategy - "三叉戟"策略
    基于动量、价值、流动性和趋势四个维度的多因子筛选
    """
    
    def __init__(self, enriched_df: pd.DataFrame, config=None):
        """
        初始化Alpha策略
        
        Args:
            enriched_df: 已包含因子列的DataFrame（通过FactorPipeline计算得到）
            config: 配置管理器，如果为None则创建新实例
        """
        self.enriched_df = enriched_df.copy() if not enriched_df.empty else pd.DataFrame()
        
        # 加载配置
        if config is None:
            from .config_manager import ConfigManager
            self.config = ConfigManager()
        else:
            self.config = config
        
        # 从配置读取阈值
        self.rps_threshold = self.config.get('strategy.alpha_trident.rps_threshold', 85)
        self.vol_ratio_threshold = self.config.get('strategy.alpha_trident.vol_ratio_threshold', 1.5)
        
        logger.debug(f"AlphaStrategy初始化: 输入数据 {len(self.enriched_df)} 行, "
                    f"RPS阈值={self.rps_threshold}, 量比阈值={self.vol_ratio_threshold}")
    
    def filter_alpha_trident(self) -> pd.DataFrame:
        """
        Alpha Trident筛选逻辑：
        1. rps_60 > threshold (从配置读取，默认85)
        2. is_undervalued == True
        3. vol_ratio_5 > threshold (从配置读取，默认1.5)
        4. above_ma_20 == True
        
        Returns:
            DataFrame: 筛选后的股票，按rps_60降序排序
            包含列: ts_code, name, close, pe_ttm, rps_60, vol_ratio_5
        """
        if self.enriched_df.empty:
            logger.warning("filter_alpha_trident: enriched_df为空")
            return pd.DataFrame()
        
        df = self.enriched_df.copy()
        
        # 检查必需的列
        required_columns = ['rps_60', 'is_undervalued', 'vol_ratio_5', 'above_ma_20']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"filter_alpha_trident: 缺少必需的列: {missing_columns}")
            raise ValueError(f"缺少必需的因子列: {missing_columns}")
        
        initial_count = len(df)
        logger.info(f"filter_alpha_trident: 开始筛选，初始股票数: {initial_count}")
        
        # 筛选条件1: rps_60 > threshold
        df = df[df['rps_60'].notna() & (df['rps_60'] > self.rps_threshold)]
        logger.debug(f"动量筛选 (rps_60 > {self.rps_threshold}): {initial_count} -> {len(df)}")
        
        if df.empty:
            logger.warning("filter_alpha_trident: 动量筛选后无数据")
            return pd.DataFrame()
        
        # 筛选条件2: is_undervalued == True
        before_value = len(df)
        df = df[df['is_undervalued'] == True]
        logger.debug(f"价值筛选 (is_undervalued == True): {before_value} -> {len(df)}")
        
        if df.empty:
            logger.warning("filter_alpha_trident: 价值筛选后无数据")
            return pd.DataFrame()
        
        # 筛选条件3: vol_ratio_5 > threshold
        before_liquidity = len(df)
        df = df[df['vol_ratio_5'] > self.vol_ratio_threshold]
        logger.debug(f"流动性筛选 (vol_ratio_5 > {self.vol_ratio_threshold}): {before_liquidity} -> {len(df)}")
        
        if df.empty:
            logger.warning("filter_alpha_trident: 流动性筛选后无数据")
            return pd.DataFrame()
        
        # 筛选条件4: above_ma_20 == True
        before_trend = len(df)
        df = df[df['above_ma_20'] == True]
        logger.debug(f"趋势筛选 (above_ma_20 == True): {before_trend} -> {len(df)}")
        
        if df.empty:
            logger.warning("filter_alpha_trident: 趋势筛选后无数据")
            return pd.DataFrame()
        
        # 按rps_60降序排序
        df = df.sort_values('rps_60', ascending=False).reset_index(drop=True)
        
        # 添加 strategy_tag 列（所有通过 Alpha Trident 筛选的股票都是强推荐）
        df['strategy_tag'] = '🚀 强推荐'
        
        # 选择输出列
        output_columns = ['ts_code', 'name', 'close', 'pe_ttm', 'rps_60', 'vol_ratio_5', 'strategy_tag']
        missing_output_cols = [col for col in output_columns if col not in df.columns]
        if missing_output_cols:
            logger.error(f"filter_alpha_trident: 输出列缺失: {missing_output_cols}")
            raise ValueError(f"缺少必需的输出列: {missing_output_cols}")
        
        result = df[output_columns].copy()
        
        logger.info(f"filter_alpha_trident: 筛选完成，最终股票数: {len(result)} (从 {initial_count} 只股票中筛选)")
        return result
