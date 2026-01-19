"""
DataProvider - DAAS Alpha 数据封装
Tushare：get_daily_basic, get_roe, get_daily_pct_chg；
公告 get_notices 降级采用东方财富，不依赖 Tushare anns_d。
"""

import os
import time
import yaml
from pathlib import Path
from typing import List, Optional

import pandas as pd
import tushare as ts
from dotenv import load_dotenv

from .api.eastmoney_api import EastmoneyAPI
from .logging_config import get_logger
from .database import (
    get_cached_constituents,
    save_constituents,
    get_latest_constituents_date,
    get_cached_daily_history,
    save_daily_history_batch,
)

logger = get_logger(__name__)

load_dotenv()


class DataProvider:
    """Tushare 行情/财务 + 东方财富公告"""

    def __init__(self) -> None:
        token = os.getenv("TUSHARE_TOKEN")
        if not token or not str(token).strip():
            raise ValueError("TUSHARE_TOKEN 未设置，请在 .env 中配置")
        ts.set_token(token)
        self._pro = ts.pro_api()
        self._em = EastmoneyAPI()
        
        # 加载配置
        config_path = Path("config/settings.yaml")
        self._index_filter_enabled = True
        self._index_code = "000852.SH"
        self._fallback_to_all = False
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                index_filter = config.get("index_filter", {})
                self._index_filter_enabled = index_filter.get("enabled", True)
                self._index_code = index_filter.get("index_code", "000852.SH")
                self._fallback_to_all = index_filter.get("fallback_to_all", False)
            except Exception as e:
                logger.debug(f"加载配置失败: {e}，使用默认值")
        
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
            
            # 获取基础数据
            basic = self._pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,list_date",
            )
            daily = self._pro.daily_basic(
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
            basic = self._pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,list_date",
            )
            return basic
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
            
            df = self._pro.daily(
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
        
        def get_roe_single(code: str, max_retries: int = 3) -> dict:
            """获取单个股票的ROE，带重试机制"""
            for attempt in range(max_retries):
                try:
                    df = self._pro.fina_indicator(
                        ts_code=code,
                        fields="ts_code,end_date,roe",
                    )
                    if df.empty or "end_date" not in df.columns:
                        return None
                    df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d", errors="coerce")
                    df = df[(df["end_date"] >= start_dt) & (df["end_date"] <= end_dt)]
                    if df.empty:
                        return None
                    last = df.sort_values("end_date").iloc[-1]
                    return {"ts_code": code, "roe": float(last["roe"])}
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.debug(f"get_roe {code} 失败 (尝试 {attempt + 1}/{max_retries}): {e}，重试中...")
                        time.sleep(0.5 * (attempt + 1))  # 递增延迟
                    else:
                        logger.debug(f"get_roe {code} 失败 (已重试 {max_retries} 次): {e}")
                        return None
            return None
        
        # 并发获取ROE（10个并发，考虑Tushare API限流）
        out: List[dict] = []
        max_workers = 10
        
        logger.info(f"开始并发获取ROE，共 {len(ts_codes)} 只股票，并发数: {max_workers}")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_code = {
                executor.submit(get_roe_single, code): code
                for code in ts_codes
            }
            
            # 使用tqdm显示进度
            with tqdm(total=len(ts_codes), desc="ROE获取进度", unit="只", ncols=80) as pbar:
                for future in as_completed(future_to_code):
                    code = future_to_code[future]
                    try:
                        result = future.result()
                        if result:
                            out.append(result)
                    except Exception as e:
                        logger.debug(f"get_roe {code} 任务异常: {e}")
                    finally:
                        pbar.update(1)
                        # 保持0.2秒延迟（在并发中通过控制并发数实现限流）
                        time.sleep(0.02)  # 每个任务完成后短暂延迟
        
        if not out:
            return pd.DataFrame(columns=["ts_code", "roe"])
        logger.info(f"ROE获取完成，成功获取 {len(out)} 只股票的ROE数据")
        return pd.DataFrame(out)

    def get_daily_pct_chg(self, trade_date: str, ts_codes: List[str]) -> pd.DataFrame:
        """
        pro.daily(trade_date) 取 ts_code, pct_chg；再按 ts_codes 过滤。
        返回 ts_code, pct_chg。
        """
        try:
            df = self._pro.daily(trade_date=trade_date, fields="ts_code,pct_chg")
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
            return self._em.get_notices(stock_list=ts_codes, start_date=start_date)
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
            # 1. 先尝试从缓存获取
            cached = get_cached_constituents(index_code, trade_date)
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
            
            # 调用Tushare API获取成分股
            df = self._pro.index_weight(
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
                df = self._pro.index_weight(
                    index_code=index_code,
                    start_date=prev_month_start.strftime("%Y%m%d"),
                    end_date=prev_month_end.strftime("%Y%m%d"),
                    fields="index_code,con_code,trade_date,weight"
                )
                if df.empty:
                    logger.warning(f"获取历史月份数据也失败: {index_code}")
                    return []
            
            # 3. 处理数据并保存到缓存
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
            for _, row in df_latest.iterrows():
                constituents_data.append({
                    "ts_code": str(row.get("con_code", "")),
                    "weight": float(row.get("weight", 0)) if pd.notna(row.get("weight")) else None
                })
            
            # 保存到缓存
            latest_date_str = latest_date.strftime("%Y%m%d") if isinstance(latest_date, datetime) else str(latest_date).replace("-", "")
            save_constituents(index_code, latest_date_str, constituents_data)
            
            # 返回股票代码列表
            ts_codes = [item["ts_code"] for item in constituents_data]
            logger.info(f"从Tushare获取并缓存成分股: {index_code}, 日期: {latest_date_str}, 数量: {len(ts_codes)}")
            return ts_codes
            
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
        
        # 优先从数据库缓存读取
        if use_cache:
            cached_df = get_cached_daily_history(stock_list, start_date, trade_date)
            if not cached_df.empty:
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
        
        # 从API获取数据（缺失的股票或缓存未命中）
        logger.info(f"从API获取历史数据: {len(stock_list)} 只股票 ({start_date} 到 {trade_date})")
        all_data = []
        
        from tqdm import tqdm
        for ts_code in tqdm(stock_list, desc="获取历史数据", ncols=80):
            try:
                daily_df = self._pro.daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=trade_date,
                    fields="ts_code,trade_date,open,high,low,close,vol"
                )
                
                if not daily_df.empty:
                    all_data.append(daily_df)
                
                # API限流
                time.sleep(0.1)
                
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
            result_df = result_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        else:
            result_df = api_df
        
        # 保存到数据库缓存
        if use_cache and not result_df.empty:
            try:
                save_daily_history_batch(result_df)
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
        
        # 优先从数据库缓存读取
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
                cached_df = get_cached_daily_history(stock_list_for_cache, start_date, end_date)
                if not cached_df.empty:
                    # 检查缓存覆盖率
                    cached_stocks = set(cached_df['ts_code'].unique())
                    required_stocks = set(stock_list_for_cache)
                    missing_stocks = required_stocks - cached_stocks
                    
                    # 检查日期范围
                    if 'trade_date' in cached_df.columns:
                        cached_df['trade_date'] = pd.to_datetime(cached_df['trade_date'], format='%Y%m%d', errors='coerce')
                        cache_start = cached_df['trade_date'].min()
                        cache_end = cached_df['trade_date'].max()
                        req_start = datetime.strptime(start_date, '%Y%m%d')
                        req_end = datetime.strptime(end_date, '%Y%m%d')
                        
                        date_covered = cache_start <= req_start and cache_end >= req_end
                    else:
                        date_covered = False
                    
                    if not missing_stocks and date_covered:
                        logger.info(f"从数据库缓存获取完整历史数据: {len(cached_df)} 条记录 ({start_date} 到 {end_date})")
                        # 如果指定了指数，过滤成分股
                        if index_code and constituents:
                            cached_df = cached_df[cached_df['ts_code'].isin(constituents)]
                        return cached_df
                    elif date_covered:
                        logger.info(f"数据库缓存部分命中: {len(cached_stocks)}/{len(required_stocks)} 只股票，缺失 {len(missing_stocks)} 只")
                        # 继续获取缺失股票的数据
                        stock_list = list(missing_stocks) if missing_stocks else None
                        cached_df_partial = cached_df.copy()
                    else:
                        logger.info(f"数据库缓存日期范围不足，需要补充数据")
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
        
        # 检查CSV缓存（向后兼容）
        cache_path = Path("data/cache.csv")
        if use_cache and cache_path.exists() and 'cached_df' not in locals():
            try:
                cached_df = pd.read_csv(cache_path, dtype={'trade_date': str})
                cached_df['trade_date'] = pd.to_datetime(cached_df['trade_date'], format='%Y%m%d', errors='coerce')
                
                # 检查缓存是否覆盖所需日期范围
                if not cached_df.empty and 'trade_date' in cached_df.columns:
                    cache_start = cached_df['trade_date'].min()
                    cache_end = cached_df['trade_date'].max()
                    req_start = datetime.strptime(start_date, '%Y%m%d')
                    req_end = datetime.strptime(end_date, '%Y%m%d')
                    
                    if cache_start <= req_start and cache_end >= req_end:
                        # 过滤到所需日期范围
                        mask = (cached_df['trade_date'] >= req_start) & (cached_df['trade_date'] <= req_end)
                        filtered = cached_df[mask].copy()
                        
                        # 如果指定了指数，过滤成分股
                        if index_code:
                            constituents = self.get_index_constituents(end_date, index_code)
                            if constituents:
                                filtered = filtered[filtered['ts_code'].isin(constituents)]
                        
                        logger.info(f"从缓存加载数据: {len(filtered)} 条记录 ({start_date} 到 {end_date})")
                        return filtered
            except Exception as e:
                logger.warning(f"读取缓存失败: {e}，将重新获取数据")
        
        # 获取股票列表（如果还没有从缓存逻辑中获取）
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
        
        if not stock_list:
            logger.error("无法获取股票列表")
            return pd.DataFrame()
        
        # 分批获取数据（避免API限制）
        all_data = []
        batch_size = 50  # 每次获取50只股票
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        
        logger.info(f"开始批量获取历史数据: {len(stock_list)} 只股票，{total_batches} 个批次")
        
        from tqdm import tqdm
        for i in tqdm(range(0, len(stock_list), batch_size), desc="获取历史数据", ncols=80):
            batch_codes = stock_list[i:i + batch_size]
            
            # 逐个获取股票数据（Tushare API限制）
            for ts_code in batch_codes:
                try:
                    daily_df = self._pro.daily(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date,
                        fields="ts_code,trade_date,open,high,low,close,vol"
                    )
                    
                    if not daily_df.empty:
                        all_data.append(daily_df)
                    
                    # API限流：短暂延迟
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.debug(f"获取 {ts_code} 数据失败: {e}")
                    continue
        
        if not all_data:
            logger.warning("未获取到任何数据")
            return pd.DataFrame()
        
        # 合并所有数据
        if not all_data:
            # 如果API获取失败，返回缓存数据（如果有）
            if use_cache and 'cached_df_partial' in locals() and cached_df_partial is not None:
                logger.warning("API获取失败，返回部分缓存数据")
                return cached_df_partial
            logger.warning("未获取到任何数据")
            return pd.DataFrame()
        
        api_df = pd.concat(all_data, ignore_index=True)
        
        # 合并缓存数据和API数据
        if use_cache and 'cached_df_partial' in locals() and cached_df_partial is not None:
            result_df = pd.concat([cached_df_partial, api_df], ignore_index=True)
            result_df = result_df.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
        else:
            result_df = api_df
        
        # 获取每日基本面数据（pe_ttm）
        logger.info("获取每日基本面数据（pe_ttm）...")
        pe_data_list = []
        
        # 获取所有交易日
        trade_dates = sorted(result_df['trade_date'].unique())
        
        for trade_date in tqdm(trade_dates, desc="获取PE数据", ncols=80):
            try:
                daily_basic = self._pro.daily_basic(
                    trade_date=trade_date,
                    fields="ts_code,trade_date,pe"
                )
                if not daily_basic.empty:
                    daily_basic = daily_basic.rename(columns={'pe': 'pe_ttm'})
                    pe_data_list.append(daily_basic)
                time.sleep(0.1)  # API限流
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
        
        # 保存到缓存
        if use_cache:
            # 优先保存到数据库缓存
            try:
                # 准备数据（确保trade_date是字符串格式）
                cache_df = result_df.copy()
                if 'trade_date' in cache_df.columns:
                    if pd.api.types.is_datetime64_any_dtype(cache_df['trade_date']):
                        cache_df['trade_date'] = cache_df['trade_date'].dt.strftime('%Y%m%d')
                
                save_daily_history_batch(cache_df)
            except Exception as e:
                logger.warning(f"保存到数据库缓存失败: {e}")
            
            # 同时保存到CSV缓存（向后兼容）
            try:
                # 读取现有缓存（如果有）
                if cache_path.exists():
                    try:
                        existing_cache = pd.read_csv(cache_path, dtype={'trade_date': str})
                        existing_cache['trade_date'] = pd.to_datetime(existing_cache['trade_date'], format='%Y%m%d', errors='coerce')
                        
                        # 合并并去重
                        combined = pd.concat([existing_cache, result_df], ignore_index=True)
                        combined = combined.drop_duplicates(subset=['ts_code', 'trade_date'], keep='last')
                        combined = combined.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
                        
                        # 保存
                        if pd.api.types.is_datetime64_any_dtype(combined['trade_date']):
                            combined['trade_date'] = combined['trade_date'].dt.strftime('%Y%m%d')
                        combined.to_csv(cache_path, index=False)
                        logger.info(f"更新CSV缓存: {len(combined)} 条记录")
                    except Exception as e:
                        logger.warning(f"合并CSV缓存失败: {e}，直接保存新数据")
                        if pd.api.types.is_datetime64_any_dtype(result_df['trade_date']):
                            result_df['trade_date'] = result_df['trade_date'].dt.strftime('%Y%m%d')
                        result_df.to_csv(cache_path, index=False)
                else:
                    # 创建目录（如果不存在）
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    if pd.api.types.is_datetime64_any_dtype(result_df['trade_date']):
                        result_df['trade_date'] = result_df['trade_date'].dt.strftime('%Y%m%d')
                    result_df.to_csv(cache_path, index=False)
                    logger.info(f"保存CSV缓存: {len(result_df)} 条记录")
            except Exception as e:
                logger.warning(f"保存CSV缓存失败: {e}")
        
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