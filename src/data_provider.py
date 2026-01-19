"""
DataProvider - DAAS Alpha 数据封装
Tushare：get_daily_basic, get_roe, get_daily_pct_chg；
公告 get_notices 降级采用东方财富，不依赖 Tushare anns_d。
"""

import os
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd
import tushare as ts
from dotenv import load_dotenv

from .api.eastmoney_api import EastmoneyAPI
from .logging_config import get_logger

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
        logger.info("DataProvider 初始化完成（Tushare + 东方财富公告）")

    def get_daily_basic(self, trade_date: str) -> pd.DataFrame:
        """
        获取每日基本面：ts_code, name, trade_date, pe_ttm, pb, mv, dividend_yield。
        stock_basic + daily_basic 按 ts_code 内连接；pe 重命名为 pe_ttm，total_mv 重命名为 mv，dv_ttm 重命名为 dividend_yield。
        mv 单位为万元，dividend_yield 单位为百分比。
        """
        try:
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
            daily = daily.rename(columns={"pe": "pe_ttm", "total_mv": "mv", "dv_ttm": "dividend_yield"})
            merged = basic.merge(daily, on="ts_code", how="inner")
            # 填充缺失的dividend_yield为0
            merged["dividend_yield"] = merged["dividend_yield"].fillna(0.0)
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
        """
        from datetime import datetime, timedelta

        if not ts_codes:
            return pd.DataFrame(columns=["ts_code", "roe"])
        end_dt = datetime.strptime(trade_date, "%Y%m%d")
        start_dt = end_dt - timedelta(days=365)
        start_s = start_dt.strftime("%Y%m%d")
        out: List[dict] = []
        for code in ts_codes:
            try:
                df = self._pro.fina_indicator(
                    ts_code=code,
                    fields="ts_code,end_date,roe",
                )
                if df.empty or "end_date" not in df.columns:
                    continue
                df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d", errors="coerce")
                df = df[(df["end_date"] >= start_dt) & (df["end_date"] <= end_dt)]
                if df.empty:
                    continue
                last = df.sort_values("end_date").iloc[-1]
                out.append({"ts_code": code, "roe": float(last["roe"])})
            except Exception as e:
                logger.debug(f"get_roe {code} 失败: {e}")
            time.sleep(0.2)
        if not out:
            return pd.DataFrame(columns=["ts_code", "roe"])
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
