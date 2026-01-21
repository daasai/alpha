"""
DataProvider - DAAS Alpha 数据封装 (Facade Pattern)
统一数据接口，协调 APIClient 和 CacheManager
"""
import os
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv

from .api.clients import TushareClient, EastmoneyClient
from .cache import CacheManager
from .config_manager import ConfigManager
from .logging_config import get_logger
from .exceptions import DataFetchError

logger = get_logger(__name__)

load_dotenv()


class DataProvider:
    """
    Tushare 行情/财务 + 东方财富公告
    Facade 模式：统一数据接口，协调 APIClient 和 CacheManager
    """

    def __init__(
        self,
        tushare_client: Optional[TushareClient] = None,
        eastmoney_client: Optional[EastmoneyClient] = None,
        cache_manager: Optional[CacheManager] = None,
        config: Optional[ConfigManager] = None
    ) -> None:
        """
        初始化 DataProvider
        
        Args:
            tushare_client: Tushare 客户端，如果为 None 则创建新实例
            eastmoney_client: 东方财富客户端，如果为 None 则创建新实例
            cache_manager: 缓存管理器，如果为 None 则创建新实例
            config: 配置管理器，如果为 None 则创建新实例
        """
        # 初始化配置
        if config is None:
            self.config = ConfigManager()
        else:
            self.config = config
        
        # 初始化 API 客户端
        if tushare_client is None:
            self._tushare_client = TushareClient(config=self.config)
        else:
            self._tushare_client = tushare_client
        
        if eastmoney_client is None:
            self._eastmoney_client = EastmoneyClient(config=self.config)
        else:
            self._eastmoney_client = eastmoney_client
        
        # 初始化缓存管理器
        if cache_manager is None:
            self._cache_manager = CacheManager(config=self.config)
        else:
            self._cache_manager = cache_manager
        
        # 加载配置
        self._index_filter_enabled = self.config.get("index_filter.enabled", True)
        self._index_code = self.config.get("index_filter.index_code", "000852.SH")
        self._fallback_to_all = self.config.get("index_filter.fallback_to_all", False)
        
        logger.info(f"DataProvider 初始化完成（Tushare + 东方财富公告，指数过滤: {'启用' if self._index_filter_enabled else '禁用'}）")

    def get_daily_basic(self, trade_date: str, index_code: str = None) -> pd.DataFrame:
        """
        获取每日基本面：ts_code, name, trade_date, pe_ttm, pb, mv, dividend_yield。
        stock_basic + daily_basic 按 ts_code 内连接；pe 重命名为 pe_ttm，total_mv 重命名为 mv，dv_ttm 重命名为 dividend_yield。
        mv 单位为万元，dividend_yield 单位为百分比。
        
        性能优化：仅获取指定指数（默认中证1000）的成分股。
        """
        try:
            # 获取指数代码（使用配置或参数）
            if index_code is None:
                index_code = self._index_code
            
            # 获取指数成分股列表（从缓存或API）
            constituents = []
            if self._index_filter_enabled:
                constituents = self.get_index_constituents(trade_date, index_code)
            
            if not constituents:
                logger.warning(f"get_daily_basic: 未获取到成分股列表（{index_code}）")
                # 根据配置决定是否降级
                fallback_to_all = getattr(self, '_fallback_to_all', False)
                
                if fallback_to_all:
                    logger.info("get_daily_basic: 降级到全市场数据")
                    use_constituents_filter = False
                else:
                    logger.warning("get_daily_basic: 成分股获取失败且未启用降级，返回空数据")
                    return pd.DataFrame()
            else:
                logger.info(f"get_daily_basic: 使用成分股过滤，数量: {len(constituents)}")
                use_constituents_filter = True
            
            # 获取基础数据（使用 TushareClient）
            basic = self._tushare_client.get_stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,list_date",
            )
            daily = self._tushare_client.get_daily_basic(
                trade_date=trade_date,
                fields="ts_code,trade_date,pe,pb,total_mv,dv_ttm",
            )
            
            if basic.empty or daily.empty:
                logger.warning("get_daily_basic: stock_basic 或 daily_basic 为空")
                return pd.DataFrame()
            
            # 应用成分股过滤（在daily_basic后过滤更高效）
            if use_constituents_filter:
                constituents_set = set(constituents)
                daily = daily[daily["ts_code"].isin(constituents_set)]
                if daily.empty:
                    logger.warning(f"get_daily_basic: 成分股过滤后 daily_basic 为空")
                    return pd.DataFrame()
            
            daily = daily.rename(columns={"pe": "pe_ttm", "total_mv": "mv", "dv_ttm": "dividend_yield"})
            merged = basic.merge(daily, on="ts_code", how="inner")
            
            # 填充缺失的dividend_yield为0
            merged["dividend_yield"] = merged["dividend_yield"].fillna(0.0)
            
            logger.info(f"get_daily_basic 完成: 获取 {len(merged)} 只股票（{'成分股过滤' if use_constituents_filter else '全市场'}）")
            return merged[["ts_code", "name", "list_date", "trade_date", "pe_ttm", "pb", "mv", "dividend_yield"]]
        except Exception as e:
            logger.error(f"get_daily_basic 失败: {e}")
            return pd.DataFrame()

    def get_stock_basic(self) -> pd.DataFrame:
        """
        获取股票基本信息：ts_code, name, list_date。
        返回所有上市股票的基本信息。
        """
        try:
            return self._tushare_client.get_stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,list_date",
            )
        except Exception as e:
            logger.error(f"get_stock_basic 失败: {e}")
            return pd.DataFrame()

    def filter_new_stocks(self, df: pd.DataFrame, trade_date: str) -> pd.DataFrame:
        """
        过滤上市不足6个月（180天）的股票。
        
        Args:
            df: 包含 list_date 列的 DataFrame
            trade_date: 交易日期，格式 YYYYMMDD
            
        Returns:
            过滤后的 DataFrame
        """
        from datetime import datetime, timedelta
        
        if df.empty or "list_date" not in df.columns:
            return df
        
        try:
            trade_dt = datetime.strptime(trade_date, "%Y%m%d")
            cutoff_date = trade_dt - timedelta(days=180)  # 6个月 = 180天
            
            df = df.copy()
            df["list_date_dt"] = pd.to_datetime(df["list_date"], format="%Y%m%d", errors="coerce")
            df = df[df["list_date_dt"] <= cutoff_date]
            df = df.drop(columns=["list_date_dt"])
            
            logger.info(f"过滤新股后剩余 {len(df)} 只股票")
            return df
        except Exception as e:
            logger.error(f"filter_new_stocks 失败: {e}")
            return df

    def get_daily_history(self, ts_code: str, end_date: str, days: int = 20) -> pd.DataFrame:
        """
        获取指定股票的历史日线数据，用于计算ATR。
        
        Args:
            ts_code: 股票代码
            end_date: 结束日期，格式 YYYYMMDD
            days: 获取天数，默认20天
            
        Returns:
            包含 ts_code, trade_date, open, high, low, close 的 DataFrame
        """
        from datetime import datetime, timedelta
        
        try:
            end_dt = datetime.strptime(end_date, "%Y%m%d")
            start_dt = end_dt - timedelta(days=days + 10)  # 多取几天以确保有足够交易日
            start_date = start_dt.strftime("%Y%m%d")
            
            df = self._tushare_client.get_daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
                fields="ts_code,trade_date,open,high,low,close",
            )
            
            if df.empty:
                return pd.DataFrame()
            
            # 按日期排序，取最近days天的数据
            df = df.sort_values("trade_date", ascending=False).head(days)
            return df.reset_index(drop=True)
        except Exception as e:
            logger.debug(f"get_daily_history {ts_code} 失败: {e}")
            return pd.DataFrame()

    def calculate_atr(self, ts_code: str, trade_date: str, period: int = 20) -> float:
        """
        计算ATR (Average True Range)。
        
        Args:
            ts_code: 股票代码
            trade_date: 交易日期，格式 YYYYMMDD
            period: ATR计算周期，默认20天
            
        Returns:
            ATR值，如果计算失败返回0.0
        """
        try:
            history = self.get_daily_history(ts_code, trade_date, days=period)
            if history.empty or len(history) < 2:
                logger.debug(f"calculate_atr {ts_code}: 历史数据不足")
                return 0.0
            
            # 计算True Range
            history = history.sort_values("trade_date", ascending=True).reset_index(drop=True)
            history["prev_close"] = history["close"].shift(1)
            
            # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
            history["tr1"] = history["high"] - history["low"]
            history["tr2"] = abs(history["high"] - history["prev_close"])
            history["tr3"] = abs(history["low"] - history["prev_close"])
            history["tr"] = history[["tr1", "tr2", "tr3"]].max(axis=1)
            
            # ATR = TR的简单移动平均
            atr = history["tr"].tail(period).mean()
            
            return float(atr) if pd.notna(atr) else 0.0
        except Exception as e:
            logger.debug(f"calculate_atr {ts_code} 失败: {e}")
            return 0.0

    def get_roe(self, trade_date: str, ts_codes: List[str]) -> pd.DataFrame:
        """
        获取 ROE：对每个 ts_code 调 fina_indicator，取 end_date 在近 365 天内的最新 roe。
        返回 ts_code, roe。
        
        性能优化：并发调用 + 重试机制
        """
        from datetime import datetime, timedelta
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from tqdm import tqdm

        if not ts_codes:
            return pd.DataFrame(columns=["ts_code", "roe"])
        
        end_dt = datetime.strptime(trade_date, "%Y%m%d")
        start_dt = end_dt - timedelta(days=365)
        
        # 使用 TushareClient 的批量获取方法
        max_workers = self.config.get('concurrency.roe_workers', 10)
        return self._tushare_client.get_roe_batch(ts_codes, trade_date, max_workers=max_workers)

    def get_daily_pct_chg(self, trade_date: str, ts_codes: List[str]) -> pd.DataFrame:
        """
        pro.daily(trade_date) 取 ts_code, pct_chg；再按 ts_codes 过滤。
        返回 ts_code, pct_chg。
        """
        try:
            df = self._tushare_client.get_daily(trade_date=trade_date, fields="ts_code,pct_chg")
            if df.empty:
                return pd.DataFrame(columns=["ts_code", "pct_chg"])
            codes_set = set(ts_codes)
            df = df[df["ts_code"].isin(codes_set)][["ts_code", "pct_chg"]]
            return df
        except Exception as e:
            logger.error(f"get_daily_pct_chg 失败: {e}")
            return pd.DataFrame(columns=["ts_code", "pct_chg"])

    def get_notices(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        公告来源：东方财富。调用 EastmoneyAPI.get_notices(stock_list=ts_codes, start_date=start_date)。
        end_date 可忽略；若调用方未传 start_date，可由 end_date 往前推 3 天（本期调用方需保证传入 start_date）。
        返回列含 ts_code, ann_date, title, title_ch, art_code, column_names（无 content）。
        失败或空时返回空 DataFrame；analyze_sentiment 在无公告时用「无最新公告」。
        """
        from datetime import datetime, timedelta
        if not start_date or not str(start_date).strip():
            if end_date and str(end_date).strip():
                try:
                    end_dt = datetime.strptime(str(end_date).strip()[:8], "%Y%m%d")
                    start_date = (end_dt - timedelta(days=3)).strftime("%Y%m%d")
                except Exception:
                    start_date = datetime.now().strftime("%Y%m%d")
            else:
                start_date = datetime.now().strftime("%Y%m%d")
        try:
            return self._eastmoney_client.get_notices(stock_list=ts_codes, start_date=start_date)
        except Exception as e:
            logger.error(f"get_notices 失败: {e}")
            return pd.DataFrame(columns=["ts_code", "ann_date", "title", "title_ch", "art_code", "column_names"])

    def get_index_constituents(self, trade_date: str, index_code: str = "000852.SH") -> List[str]:
        """
        获取指数成分股列表（优先从缓存获取，如无则从Tushare获取并缓存）。
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
            index_code: 指数代码，默认 '000852.SH'（中证1000）
            
        Returns:
            成分股代码列表，如果获取失败返回空列表
        """
        from datetime import datetime, timedelta
        import calendar
        
        try:
            # 1. 先尝试从缓存获取（使用 CacheManager）
            cached = self._cache_manager.get_constituents(index_code, trade_date)
            if cached:
                logger.info(f"从缓存获取成分股: {index_code}, 数量: {len(cached)}")
                return cached
            
            # 2. 缓存不存在，从Tushare API获取
            logger.info(f"缓存中无成分股数据，从Tushare API获取: {index_code}")
            
            # 计算交易日期所在月份的第一天和最后一天
            trade_dt = datetime.strptime(trade_date, "%Y%m%d")
            month_start = trade_dt.replace(day=1).strftime("%Y%m%d")
            last_day = calendar.monthrange(trade_dt.year, trade_dt.month)[1]
            month_end = trade_dt.replace(day=last_day).strftime("%Y%m%d")
            
            # 调用Tushare API获取成分股（使用 TushareClient）
            df = self._tushare_client.get_index_weight(
                index_code=index_code,
                start_date=month_start,
                end_date=month_end,
                fields="index_code,con_code,trade_date,weight"
            )
            
            if df.empty:
                logger.warning(f"Tushare API返回空数据: {index_code}, 日期范围: {month_start}-{month_end}")
                # 尝试获取最近一个月的数据
                prev_month_end = (trade_dt.replace(day=1) - timedelta(days=1))
                prev_month_start = prev_month_end.replace(day=1)
                df = self._tushare_client.get_index_weight(
                    index_code=index_code,
                    start_date=prev_month_start.strftime("%Y%m%d"),
                    end_date=prev_month_end.strftime("%Y%m%d"),
                    fields="index_code,con_code,trade_date,weight"
                )
                if df.empty:
                    logger.warning(f"获取历史月份数据也失败: {index_code}")
                    return []
            
            # 3. 处理数据并保存到缓存（使用 CacheManager）
            # 取最新的trade_date对应的成分股
            if "trade_date" in df.columns:
                df["trade_date"] = pd.to_datetime(df["trade_date"], format="%Y%m%d", errors="coerce")
                latest_date = df["trade_date"].max()
                df_latest = df[df["trade_date"] == latest_date].copy()
            else:
                df_latest = df.copy()
                latest_date = datetime.strptime(month_end, "%Y%m%d")
            
            # 构建保存数据
            constituents_data = []
            weights_data = []
            for _, row in df_latest.iterrows():
                constituents_data.append(str(row.get("con_code", "")))
                weight = row.get("weight")
                weights_data.append(float(weight) if pd.notna(weight) else None)
            
            # 保存到缓存（使用 CacheManager）
            latest_date_str = latest_date.strftime("%Y%m%d") if isinstance(latest_date, datetime) else str(latest_date).replace("-", "")
            self._cache_manager.set_constituents(
                index_code,
                latest_date_str,
                constituents_data,
                weights=weights_data if any(w is not None for w in weights_data) else None
            )
            
            logger.info(f"从Tushare获取并缓存成分股: {index_code}, 日期: {latest_date_str}, 数量: {len(constituents_data)}")
            return constituents_data
            
        except Exception as e:
            error_msg = str(e)
            # 检查是否是权限问题
            if "权限" in error_msg or "积分" in error_msg or "2000" in error_msg:
                logger.warning(f"获取成分股失败（可能是积分不足）: {error_msg}")
            else:
                logger.error(f"get_index_constituents 失败: {error_msg}")
            return []
    
    def fetch_history_for_hunter(
        self,
        trade_date: str,
        start_date: str = None,
        index_code: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        为 Hunter 页面获取历史日线数据。
        获取指定日期范围的历史数据，支持数据库缓存。
        
        Args:
            trade_date: 目标交易日期（YYYYMMDD）
            start_date: 开始日期（YYYYMMDD），如果为None则自动计算（60天前）
            index_code: 指数代码，如果为None则使用配置的指数
            use_cache: 是否使用缓存，默认True
            
        Returns:
            DataFrame包含列: ts_code, trade_date, open, high, low, close, vol
        """
        from datetime import datetime, timedelta
        
        # 如果没有指定开始日期，自动计算
        # 考虑到节假日、停牌等因素，70个自然日可能只有约40-50个交易日
        # 为了确保有60个交易日，需要获取约120个自然日的数据（约3-4个月）
        if start_date is None:
            trade_dt = datetime.strptime(trade_date, "%Y%m%d")
            start_dt = trade_dt - timedelta(days=120)  # 60个交易日约需要120个自然日
            start_date = start_dt.strftime("%Y%m%d")
        
        # 使用配置的指数代码
        if index_code is None:
            index_code = self._index_code if self._index_filter_enabled else None
        
        # 获取股票列表
        if index_code:
            constituents = self.get_index_constituents(trade_date, index_code)
            if not constituents:
                logger.warning(f"无法获取成分股，降级到全市场数据")
                stock_list = None
            else:
                stock_list = constituents
                logger.info(f"成分股数量: {len(stock_list)}")
        else:
            stock_list = None
            logger.info("获取全市场数据")
        
        # 获取基础股票列表（如果需要）
        if stock_list is None:
            basic = self.get_stock_basic()
            stock_list = basic['ts_code'].tolist() if not basic.empty else []
            logger.info(f"全市场股票数量: {len(stock_list)}")
        
        if not stock_list:
            logger.error("无法获取股票列表")
            return pd.DataFrame()
        
        # 优先从数据库缓存读取（使用 CacheManager）
        if use_cache:
            cached_df = self._cache_manager.get_daily_history(stock_list, start_date, trade_date)
            if cached_df is not None and not cached_df.empty:
                # 检查缓存覆盖率
                cached_stocks = set(cached_df['ts_code'].unique())
                required_stocks = set(stock_list)
                missing_stocks = required_stocks - cached_stocks
                
                # 检查每个股票的数据是否足够（至少60条）
                if not missing_stocks:
                    # 检查数据完整性：每个股票是否有足够的数据点
                    stock_counts = cached_df.groupby('ts_code').size()
                    stocks_with_enough_data = (stock_counts >= 60).sum()
                    total_stocks = len(stock_counts)
                    
                    if stocks_with_enough_data == total_stocks:
                        logger.info(f"从数据库缓存获取完整历史数据: {len(cached_df)} 条记录，所有股票数据充足")
                        return cached_df
                    else:
                        logger.info(f"数据库缓存数据不足: {stocks_with_enough_data}/{total_stocks} 只股票有≥60条数据，需要重新获取")
                        # 数据不足，需要重新获取所有股票的数据
                        stock_list = list(required_stocks)
                else:
                    logger.info(f"数据库缓存部分命中: {len(cached_stocks)}/{len(required_stocks)} 只股票，缺失 {len(missing_stocks)} 只")
                    # 继续获取缺失股票的数据
                    stock_list = list(missing_stocks)
        
        # 从API获取数据（缺失的股票或缓存未命中，使用 TushareClient）
        logger.info(f"从API获取历史数据: {len(stock_list)} 只股票 ({start_date} 到 {trade_date})")
        all_data = []
        
        from tqdm import tqdm
        for ts_code in tqdm(stock_list, desc="获取历史数据", ncols=80):
            try:
                daily_df = self._tushare_client.get_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=trade_date,
                    fields="ts_code,trade_date,open,high,low,close,vol"
                )
                
                if not daily_df.empty:
                    all_data.append(daily_df)
                
            except Exception as e:
                logger.debug(f"获取 {ts_code} 数据失败: {e}")
                continue
        
        if not all_data:
            # 如果API获取失败，返回缓存数据（如果有）
            if use_cache and 'cached_df' in locals() and not cached_df.empty:
                logger.warning("API获取失败，返回缓存数据")
                return cached_df
            logger.warning("未获取到任何数据")
            return pd.DataFrame()
        
        # 合并API获取的数据
        api_df = pd.concat(all_data, ignore_index=True)
        
        # 合并缓存数据和API数据
        if use_cache and 'cached_df' in locals() and not cached_df.empty:
            result_df = pd.concat([cached_df, api_df], ignore_index=True)
            # 先排序确保稳定性，然后去重（统一使用keep='first'）
            result_df = result_df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
            result_df = result_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='first')
        else:
            result_df = api_df
        
        # 保存到数据库缓存（使用 CacheManager）
        if use_cache and not result_df.empty:
            try:
                self._cache_manager.set_daily_history(result_df)
            except Exception as e:
                logger.warning(f"保存到数据库缓存失败: {e}")
        
        # 确保trade_date格式一致
        if 'trade_date' in result_df.columns:
            result_df['trade_date'] = pd.to_datetime(result_df['trade_date'], format='%Y%m%d', errors='coerce')
            result_df = result_df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
            result_df['trade_date'] = result_df['trade_date'].dt.strftime('%Y%m%d')
        
        logger.info(f"fetch_history_for_hunter 完成: {len(result_df)} 条记录")
        return result_df
    
    def fetch_history_batch(
        self, 
        start_date: str, 
        end_date: str, 
        index_code: str = "000300.SH",
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        批量获取历史日线数据，用于回测。
        获取指定日期范围内所有股票（或指数成分股）的日线数据。
        
        Args:
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            index_code: 指数代码，默认 '000300.SH' (沪深300)。如果为None，则获取全市场数据
            use_cache: 是否使用缓存，默认True
            
        Returns:
            DataFrame包含列: ts_code, trade_date, open, high, low, close, vol, pe_ttm
        """
        from datetime import datetime
        import os
        
        # 优先从数据库缓存读取（使用 CacheManager）
        if use_cache:
            # 先获取股票列表（用于查询缓存）
            if index_code:
                logger.info(f"获取指数成分股: {index_code}")
                constituents = self.get_index_constituents(end_date, index_code)
                if not constituents:
                    logger.warning(f"无法获取成分股，降级到全市场数据")
                    stock_list_for_cache = None
                else:
                    stock_list_for_cache = constituents
            else:
                stock_list_for_cache = None
            
            if stock_list_for_cache is None:
                basic = self.get_stock_basic()
                stock_list_for_cache = basic['ts_code'].tolist() if not basic.empty else []
            
            if stock_list_for_cache:
                cached_df = self._cache_manager.get_daily_history(stock_list_for_cache, start_date, end_date)
                if cached_df is not None and not cached_df.empty:
                    # 检查缓存覆盖率
                    cached_stocks = set(cached_df['ts_code'].unique())
                    required_stocks = set(stock_list_for_cache)
                    missing_stocks = required_stocks - cached_stocks
                    
                    # 检查日期范围和数据完整性
                    date_covered = False
                    date_completeness = 0.0
                    if 'trade_date' in cached_df.columns:
                        # 确保trade_date是字符串格式（用于比较和过滤）
                        if pd.api.types.is_datetime64_any_dtype(cached_df['trade_date']):
                            cached_df['trade_date_str'] = cached_df['trade_date'].dt.strftime('%Y%m%d')
                        elif cached_df['trade_date'].dtype == 'object':
                            cached_df['trade_date_str'] = cached_df['trade_date'].astype(str)
                        else:
                            cached_df['trade_date_str'] = cached_df['trade_date'].astype(str)
                        
                        # 检查日期范围覆盖
                        req_start = pd.to_datetime(start_date, format='%Y%m%d')
                        req_end = pd.to_datetime(end_date, format='%Y%m%d')
                        
                        # 将trade_date_str转换为datetime用于范围检查
                        cached_df['trade_date_dt'] = pd.to_datetime(cached_df['trade_date_str'], format='%Y%m%d', errors='coerce')
                        valid_dates = cached_df['trade_date_dt'].dropna()
                        
                        if not valid_dates.empty:
                            cache_start = valid_dates.min()
                            cache_end = valid_dates.max()
                            
                            # 检查日期范围覆盖
                            # 注意：get_cached_daily_history已经按日期范围过滤（start_date 到 end_date）
                            # 所以返回的数据应该都在请求范围内，但可能缺少某些交易日的数据
                            # 关键：如果cache_start > req_start 或 cache_end < req_end，说明缺少开始或结束日期的数据
                            # 这种情况下，不应该使用缓存，因为会影响回测准确性
                            date_covered = cache_start <= req_start and cache_end >= req_end
                            
                            # 额外检查：即使日期范围覆盖，也要检查是否有足够的交易日数据
                            # 如果缺少太多交易日，也不应该使用缓存
                            if date_covered:
                                # 估算应该有多少个交易日（粗略估算）
                                total_days = (req_end - req_start).days
                                estimated_trading_days = int(total_days * 0.7)  # 假设70%是交易日
                                actual_trading_days = unique_dates_count
                                
                                # 如果实际交易日数少于估算的80%，认为数据不完整
                                if estimated_trading_days > 0 and actual_trading_days < estimated_trading_days * 0.8:
                                    logger.warning(
                                        f"⚠️ 缓存数据交易日数不足: 实际 {actual_trading_days} 个交易日, "
                                        f"估算 {estimated_trading_days} 个交易日, 可能缺少部分交易日数据"
                                    )
                                    date_covered = False  # 标记为不覆盖，强制重新获取
                            
                            # 如果日期覆盖为False，说明缓存数据缺少某些日期的数据
                            # 这种情况下，即使股票覆盖率100%，也不应该使用缓存，因为数据不完整
                            if not date_covered:
                                logger.warning(
                                    f"⚠️ 缓存数据日期范围不完整: "
                                    f"缓存范围[{cache_start.date()} 到 {cache_end.date()}] "
                                    f"请求范围[{req_start.date()} 到 {req_end.date()}]，"
                                    f"缺少部分日期数据，需要重新获取"
                                )
                            
                            # 检查数据完整性：计算每个股票在每个交易日是否有数据
                            # 注意：get_cached_daily_history已经按日期范围过滤，所以返回的数据应该在请求范围内
                            # 但我们需要检查数据是否完整（是否有所有股票在所有交易日的数据）
                            unique_dates = sorted(valid_dates.unique())
                            unique_dates_count = len(unique_dates)
                            
                            # 计算每个股票的数据条数
                            stock_date_counts = cached_df.groupby('ts_code')['trade_date_str'].nunique()
                            avg_dates_per_stock = stock_date_counts.mean() if len(stock_date_counts) > 0 else 0
                            
                            # 数据完整性 = 平均每个股票的数据条数 / 交易日数
                            # 如果完整性 > 0.90，认为数据足够完整（允许10%的缺失，比如停牌）
                            date_completeness = avg_dates_per_stock / unique_dates_count if unique_dates_count > 0 else 0.0
                            
                            # 额外检查：是否有足够的股票有完整的数据
                            # 至少90%的交易日有数据，认为该股票数据完整
                            stocks_with_full_data = (stock_date_counts >= unique_dates_count * 0.90).sum()
                            stock_completeness = stocks_with_full_data / len(required_stocks) if required_stocks else 0.0
                            
                            # 计算期望的记录数（考虑停牌等因素，期望值应该略小于理论值）
                            # 理论值：len(required_stocks) * unique_dates_count
                            # 实际值：len(cached_df)
                            expected_records = len(required_stocks) * unique_dates_count
                            actual_records = len(cached_df)
                            record_completeness = actual_records / expected_records if expected_records > 0 else 0.0
                            
                            logger.info(
                                f"缓存日期范围检查: 缓存[{cache_start.date()} 到 {cache_end.date()}] "
                                f"请求[{req_start.date()} 到 {req_end.date()}], "
                                f"覆盖: {date_covered}, 日期完整性: {date_completeness*100:.1f}%, "
                                f"股票完整性: {stock_completeness*100:.1f}%, 记录完整性: {record_completeness*100:.1f}% "
                                f"({actual_records}/{expected_records} 条记录, {unique_dates_count} 个交易日)"
                            )
                        else:
                            logger.warning("缓存数据中没有有效的日期")
                    
                    # 详细日志输出，帮助诊断问题
                    stock_completeness = stock_completeness if 'stock_completeness' in locals() else 0.0
                    record_completeness = record_completeness if 'record_completeness' in locals() else 0.0
                    
                    logger.info(
                        f"缓存检查结果: 缓存股票数={len(cached_stocks)}, 需要股票数={len(required_stocks)}, "
                        f"缺失股票数={len(missing_stocks)}, 日期覆盖={date_covered}, "
                        f"日期完整性={date_completeness*100:.1f}%, 股票完整性={stock_completeness*100:.1f}%, "
                        f"记录完整性={record_completeness*100:.1f}%"
                    )
                    
                    # 检查缓存数据的实际日期范围
                    cache_coverage_ratio = len(cached_stocks) / len(required_stocks) if required_stocks else 0
                    
                    # 关键修复：只有当数据完整性足够高时才使用缓存
                    # 数据完整性阈值：至少85%（允许15%的缺失，比如停牌股票）
                    min_completeness = 0.85
                    min_stock_completeness = 0.85  # 至少85%的股票有完整数据
                    min_record_completeness = 0.85  # 至少85%的记录存在
                    
                    # 计算综合完整性（加权平均，记录完整性权重最高）
                    overall_completeness = (
                        date_completeness * 0.3 + 
                        stock_completeness * 0.3 + 
                        record_completeness * 0.4
                    )
                    
                    # 关键修复：只有当日期完全覆盖且数据完整性足够时才使用缓存
                    # 如果日期覆盖为False，说明缓存数据缺少某些日期的数据，不应该使用缓存
                    if not missing_stocks and date_covered and overall_completeness >= min_completeness:
                        logger.info(
                            f"✅ 从数据库缓存获取完整历史数据: {len(cached_df)} 条记录 "
                            f"({start_date} 到 {end_date}), 数据完整性: {overall_completeness*100:.1f}%"
                        )
                        # 确保trade_date是字符串格式（用于后续处理）
                        if 'trade_date_str' not in cached_df.columns:
                            if pd.api.types.is_datetime64_any_dtype(cached_df['trade_date']):
                                cached_df['trade_date_str'] = cached_df['trade_date'].dt.strftime('%Y%m%d')
                            elif cached_df['trade_date'].dtype == 'object':
                                cached_df['trade_date_str'] = cached_df['trade_date'].astype(str)
                            else:
                                cached_df['trade_date_str'] = cached_df['trade_date'].astype(str)
                        
                        # 过滤到请求的日期范围（确保数据在请求范围内）
                        # 注意：get_cached_daily_history已经过滤了，但为了安全起见，再次过滤
                        mask = (cached_df['trade_date_str'] >= start_date) & (cached_df['trade_date_str'] <= end_date)
                        cached_df = cached_df[mask].drop(columns=['trade_date_str', 'trade_date_dt'], errors='ignore')
                        
                        # 如果指定了指数，过滤成分股
                        if index_code and constituents:
                            cached_df = cached_df[cached_df['ts_code'].isin(constituents)]
                        
                        logger.info(f"✅ 缓存数据过滤后: {len(cached_df)} 条记录")
                        return cached_df
                    elif not missing_stocks and date_covered and overall_completeness < min_completeness:
                        logger.warning(
                            f"⚠️ 缓存数据完整性不足 (综合完整性: {overall_completeness*100:.1f}% < {min_completeness*100:.0f}%)，"
                            f"日期完整性: {date_completeness*100:.1f}%, 股票完整性: {stock_completeness*100:.1f}%，"
                            f"可能缺少部分交易日数据，重新获取以确保准确性"
                        )
                        stock_list = stock_list_for_cache
                        cached_df_partial = None
                    elif date_covered:
                        logger.info(f"⚠️ 数据库缓存部分命中: {len(cached_stocks)}/{len(required_stocks)} 只股票，缺失 {len(missing_stocks)} 只")
                        # 继续获取缺失股票的数据
                        stock_list = list(missing_stocks) if missing_stocks else None
                        cached_df_partial = cached_df.copy()
                    # 关键修复：如果日期覆盖为False，说明缓存数据缺少某些日期的数据
                    # 这种情况下，不应该使用缓存，因为会影响回测准确性
                    elif not date_covered:
                        logger.warning(
                            f"❌ 缓存数据日期范围不完整，日期覆盖={date_covered}，"
                            f"缓存范围可能缺少部分日期数据，重新获取以确保回测准确性"
                        )
                        stock_list = stock_list_for_cache
                        cached_df_partial = None
                    else:
                        if missing_stocks:
                            logger.warning(f"❌ 数据库缓存不完整: 缺失 {len(missing_stocks)} 只股票 (覆盖率: {cache_coverage_ratio*100:.1f}%)")
                        if not date_covered:
                            logger.warning(
                                f"❌ 数据库缓存日期范围不足: "
                                f"缓存范围可能不覆盖请求范围 [{start_date} 到 {end_date}]"
                            )
                        stock_list = stock_list_for_cache
                        cached_df_partial = None
                else:
                    stock_list = stock_list_for_cache
                    cached_df_partial = None
            else:
                stock_list = None
                cached_df_partial = None
        else:
            stock_list = None
            cached_df_partial = None
        
        # CSV 缓存已移除，统一使用数据库缓存
        
        # 如果已经使用完整缓存且不需要API获取，检查是否需要PE数据
        cache_fully_hit = False
        if use_cache and 'cached_df_partial' in locals() and cached_df_partial is not None:
            if stock_list is None:
                # 缓存完全命中，不需要API获取历史数据
                cache_fully_hit = True
                logger.info(f"✅ 使用完整缓存数据，跳过API获取历史数据: {len(cached_df_partial)} 条记录")
                result_df = cached_df_partial.copy()
                
                # 确保trade_date格式正确（字符串格式）
                if 'trade_date' in result_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(result_df['trade_date']):
                        result_df['trade_date'] = result_df['trade_date'].dt.strftime('%Y%m%d')
                    elif result_df['trade_date'].dtype == 'object':
                        # 已经是字符串格式，确保格式正确
                        pass
                
                # 检查是否需要获取PE数据
                if 'pe_ttm' not in result_df.columns or result_df['pe_ttm'].isna().all():
                    logger.info("缓存数据缺少PE数据，获取PE数据...")
                    # 继续执行PE数据获取逻辑（见下方代码）
                else:
                    # 已经有PE数据，直接返回
                    logger.info(f"✅ 缓存数据完整（包含PE数据），直接返回: {len(result_df)} 条记录")
                    return result_df
        
        # 如果缓存完全命中，跳过股票列表获取和API数据获取
        if cache_fully_hit:
            # 只获取PE数据（如果需要）
            # 获取所有交易日（确保trade_date是字符串格式）
            if 'trade_date' in result_df.columns:
                if pd.api.types.is_datetime64_any_dtype(result_df['trade_date']):
                    trade_dates = sorted(result_df['trade_date'].dt.strftime('%Y%m%d').unique())
                else:
                    trade_dates = sorted(result_df['trade_date'].astype(str).unique())
            else:
                trade_dates = []
            
            # 获取PE数据
            pe_data_list = []
            from tqdm import tqdm
            for trade_date in tqdm(trade_dates, desc="获取PE数据", ncols=80):
                try:
                    daily_basic = self._tushare_client.get_daily_basic(
                        trade_date=trade_date,
                        fields="ts_code,trade_date,pe"
                    )
                    if not daily_basic.empty:
                        daily_basic = daily_basic.rename(columns={'pe': 'pe_ttm'})
                        pe_data_list.append(daily_basic)
                except Exception as e:
                    logger.debug(f"获取 {trade_date} 的PE数据失败: {e}")
                    continue
            
            # 合并PE数据
            if pe_data_list:
                pe_df = pd.concat(pe_data_list, ignore_index=True)
                result_df = result_df.merge(
                    pe_df[['ts_code', 'trade_date', 'pe_ttm']],
                    on=['ts_code', 'trade_date'],
                    how='left'
                )
            else:
                result_df['pe_ttm'] = None
            
            # 确保trade_date格式一致（字符串格式）
            if 'trade_date' in result_df.columns:
                if pd.api.types.is_datetime64_any_dtype(result_df['trade_date']):
                    result_df['trade_date'] = result_df['trade_date'].dt.strftime('%Y%m%d')
            
            logger.info(f"✅ 缓存数据（已补充PE数据）: {len(result_df)} 条记录")
            return result_df
        
        # 获取股票列表（如果还没有从缓存逻辑中获取，且需要API获取）
        if 'stock_list' not in locals() or stock_list is None:
            if index_code:
                logger.info(f"获取指数成分股: {index_code}")
                constituents = self.get_index_constituents(end_date, index_code)
                if not constituents:
                    logger.warning(f"无法获取成分股，降级到全市场数据")
                    stock_list = None
                else:
                    stock_list = constituents
                    logger.info(f"成分股数量: {len(stock_list)}")
            else:
                stock_list = None
                logger.info("获取全市场数据")
            
            # 获取基础股票列表（如果需要）
            if stock_list is None:
                basic = self.get_stock_basic()
                stock_list = basic['ts_code'].tolist() if not basic.empty else []
                logger.info(f"全市场股票数量: {len(stock_list)}")
        
        # 如果stock_list为空且没有缓存数据，返回空DataFrame
        if not stock_list:
            if use_cache and 'cached_df_partial' in locals() and cached_df_partial is not None:
                logger.info("股票列表为空，但存在缓存数据，使用缓存数据")
                return cached_df_partial
            logger.error("无法获取股票列表且无缓存数据")
            return pd.DataFrame()
        
        # 分批获取数据（避免API限制）
        all_data = []
        batch_size = 50  # 每次获取50只股票
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        
        logger.info(f"开始批量获取历史数据: {len(stock_list)} 只股票，{total_batches} 个批次")
        
        from tqdm import tqdm
        for i in tqdm(range(0, len(stock_list), batch_size), desc="获取历史数据", ncols=80):
            batch_codes = stock_list[i:i + batch_size]
            
            # 逐个获取股票数据（使用 TushareClient，自动处理限流）
            for ts_code in batch_codes:
                try:
                    daily_df = self._tushare_client.get_daily(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date,
                        fields="ts_code,trade_date,open,high,low,close,vol"
                    )
                    
                    if not daily_df.empty:
                        all_data.append(daily_df)
                    
                except Exception as e:
                    logger.debug(f"获取 {ts_code} 数据失败: {e}")
                    continue
        
        if not all_data:
            # 如果API获取失败，返回缓存数据（如果有）
            if use_cache and 'cached_df_partial' in locals() and cached_df_partial is not None:
                logger.warning("API获取失败，返回部分缓存数据")
                return cached_df_partial
            logger.warning("未获取到任何数据")
            return pd.DataFrame()
        
        api_df = pd.concat(all_data, ignore_index=True)
        
        # 合并缓存数据和API数据
        if use_cache and 'cached_df_partial' in locals() and cached_df_partial is not None and not cached_df_partial.empty:
            # 确保两个DataFrame的列一致
            if not api_df.empty:
                # 统一列名和格式
                common_cols = set(cached_df_partial.columns) & set(api_df.columns)
                cached_df_partial = cached_df_partial[list(common_cols)]
                api_df = api_df[list(common_cols)]
                
                result_df = pd.concat([cached_df_partial, api_df], ignore_index=True)
                # 先排序确保稳定性，然后去重（统一使用keep='first'）
                result_df = result_df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
                result_df = result_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='first')
                logger.info(f"合并缓存和API数据: 缓存 {len(cached_df_partial)} 条 + API {len(api_df)} 条 = {len(result_df)} 条（去重后）")
            else:
                # 如果API没有获取到新数据，直接使用缓存
                result_df = cached_df_partial.copy()
                logger.info(f"API未获取到新数据，使用缓存数据: {len(result_df)} 条")
        else:
            result_df = api_df
        
        # 获取每日基本面数据（pe_ttm）
        # 检查是否已经有PE数据（从缓存获取的完整数据可能已包含PE）
        if 'pe_ttm' in result_df.columns and not result_df['pe_ttm'].isna().all():
            logger.info(f"数据已包含PE信息，跳过PE数据获取: {result_df['pe_ttm'].notna().sum()}/{len(result_df)} 条有PE数据")
        else:
            logger.info("获取每日基本面数据（pe_ttm）...")
            pe_data_list = []
            
            # 获取所有交易日（确保trade_date是字符串格式）
            if pd.api.types.is_datetime64_any_dtype(result_df['trade_date']):
                trade_dates = sorted(result_df['trade_date'].dt.strftime('%Y%m%d').unique())
            else:
                trade_dates = sorted(result_df['trade_date'].astype(str).unique())
        
        for trade_date in tqdm(trade_dates, desc="获取PE数据", ncols=80):
            try:
                daily_basic = self._tushare_client.get_daily_basic(
                    trade_date=trade_date,
                    fields="ts_code,trade_date,pe"
                )
                if not daily_basic.empty:
                    daily_basic = daily_basic.rename(columns={'pe': 'pe_ttm'})
                    pe_data_list.append(daily_basic)
            except Exception as e:
                logger.debug(f"获取 {trade_date} 的PE数据失败: {e}")
                continue
        
        # 合并PE数据
        if pe_data_list:
            pe_df = pd.concat(pe_data_list, ignore_index=True)
            result_df = result_df.merge(
                pe_df[['ts_code', 'trade_date', 'pe_ttm']],
                on=['ts_code', 'trade_date'],
                how='left'
            )
        else:
            result_df['pe_ttm'] = None
        
        # 确保trade_date格式一致
        result_df['trade_date'] = pd.to_datetime(result_df['trade_date'], format='%Y%m%d', errors='coerce')
        
        # 排序
        result_df = result_df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
        
        # 保存到数据库缓存（使用 CacheManager，CSV 缓存已移除）
        if use_cache and not result_df.empty:
            try:
                # 准备数据（确保trade_date是字符串格式）
                cache_df = result_df.copy()
                if 'trade_date' in cache_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(cache_df['trade_date']):
                        cache_df['trade_date'] = cache_df['trade_date'].dt.strftime('%Y%m%d')
                    # 只保存历史数据列（移除 pe_ttm，因为它不在缓存表中）
                    if 'pe_ttm' in cache_df.columns:
                        cache_df = cache_df.drop(columns=['pe_ttm'])
                
                self._cache_manager.set_daily_history(cache_df)
            except Exception as e:
                logger.warning(f"保存到数据库缓存失败: {e}")
        
        # 转换trade_date回字符串格式（保持一致性）
        # 检查trade_date的类型，只有在datetime类型时才使用.dt访问器
        if pd.api.types.is_datetime64_any_dtype(result_df['trade_date']):
            result_df['trade_date'] = result_df['trade_date'].dt.strftime('%Y%m%d')
        elif result_df['trade_date'].dtype == 'object':
            # 如果已经是字符串类型，确保格式正确
            # 尝试转换为datetime再转回字符串，以确保格式一致
            try:
                result_df['trade_date'] = pd.to_datetime(result_df['trade_date'], format='%Y%m%d', errors='coerce').dt.strftime('%Y%m%d')
            except Exception:
                # 如果转换失败，保持原样
                pass
        
        logger.info(f"fetch_history_batch 完成: {len(result_df)} 条记录")
        return result_df