"""
Tushare API Client
封装所有 Tushare Pro API 调用
"""
import os
from typing import List, Optional
from datetime import datetime, timedelta

import pandas as pd
import tushare as ts
from dotenv import load_dotenv
from tqdm import tqdm

from .base_client import BaseAPIClient
from ...logging_config import get_logger
from ...exceptions import APIError, DataFetchError

logger = get_logger(__name__)
load_dotenv()


class TushareClient(BaseAPIClient):
    """Tushare Pro API 客户端"""
    
    def __init__(self, token: Optional[str] = None, config=None):
        """
        初始化 Tushare 客户端
        
        Args:
            token: Tushare Token，如果为 None 则从环境变量读取
            config: 配置管理器
        """
        super().__init__(config)
        
        if token is None:
            token = os.getenv("TUSHARE_TOKEN")
        
        if not token or not str(token).strip():
            raise ValueError("TUSHARE_TOKEN 未设置，请在 .env 中配置")
        
        ts.set_token(token)
        self._pro = ts.pro_api()
        logger.info("TushareClient 初始化完成")
    
    def get_data(self, **kwargs) -> pd.DataFrame:
        """
        通用数据获取方法（不直接使用，使用具体方法）
        
        Args:
            **kwargs: 参数
            
        Returns:
            DataFrame
        """
        raise NotImplementedError("请使用具体的 API 方法")
    
    def get_stock_basic(
        self,
        exchange: str = "",
        list_status: str = "L",
        fields: str = "ts_code,name,list_date"
    ) -> pd.DataFrame:
        """
        获取股票基本信息
        
        Args:
            exchange: 交易所代码
            list_status: 上市状态
            fields: 字段列表
            
        Returns:
            DataFrame: 股票基本信息
        """
        def _fetch():
            self._rate_limit()
            return self._pro.stock_basic(
                exchange=exchange,
                list_status=list_status,
                fields=fields
            )
        
        try:
            result = self._retry_on_failure(_fetch)
            logger.debug(f"获取股票基本信息: {len(result)} 条")
            return result
        except Exception as e:
            raise DataFetchError(f"获取股票基本信息失败: {str(e)}") from e
    
    def get_daily_basic(
        self,
        trade_date: str,
        fields: str = "ts_code,trade_date,pe,pb,total_mv,dv_ttm"
    ) -> pd.DataFrame:
        """
        获取每日基本面数据
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)
            fields: 字段列表
            
        Returns:
            DataFrame: 每日基本面数据
        """
        def _fetch():
            self._rate_limit()
            return self._pro.daily_basic(
                trade_date=trade_date,
                fields=fields
            )
        
        try:
            result = self._retry_on_failure(_fetch)
            logger.debug(f"获取每日基本面数据 ({trade_date}): {len(result)} 条")
            return result
        except Exception as e:
            raise DataFetchError(f"获取每日基本面数据失败 ({trade_date}): {str(e)}") from e
    
    def get_daily(
        self,
        ts_code: Optional[str] = None,
        trade_date: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        fields: str = "ts_code,trade_date,open,high,low,close,vol"
    ) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            ts_code: 股票代码
            trade_date: 交易日期
            start_date: 开始日期
            end_date: 结束日期
            limit: 限制条数
            fields: 字段列表
            
        Returns:
            DataFrame: 日线数据
        """
        def _fetch():
            self._rate_limit()
            params = {
                "fields": fields
            }
            if ts_code:
                params["ts_code"] = ts_code
            if trade_date:
                params["trade_date"] = trade_date
            if start_date:
                params["start_date"] = start_date
            if end_date:
                params["end_date"] = end_date
            if limit:
                params["limit"] = limit
            
            return self._pro.daily(**params)
        
        try:
            result = self._retry_on_failure(_fetch)
            logger.debug(f"获取日线数据: {len(result)} 条")
            return result
        except Exception as e:
            raise DataFetchError(f"获取日线数据失败: {str(e)}") from e
    
    def get_fina_indicator(
        self,
        ts_code: str,
        fields: str = "ts_code,end_date,roe"
    ) -> pd.DataFrame:
        """
        获取财务指标数据
        
        Args:
            ts_code: 股票代码
            fields: 字段列表
            
        Returns:
            DataFrame: 财务指标数据
        """
        def _fetch():
            self._rate_limit()
            return self._pro.fina_indicator(
                ts_code=ts_code,
                fields=fields
            )
        
        try:
            result = self._retry_on_failure(_fetch)
            logger.debug(f"获取财务指标 ({ts_code}): {len(result)} 条")
            return result
        except Exception as e:
            raise DataFetchError(f"获取财务指标失败 ({ts_code}): {str(e)}") from e
    
    def get_index_weight(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
        fields: str = "index_code,con_code,trade_date,weight"
    ) -> pd.DataFrame:
        """
        获取指数成分股
        
        Args:
            index_code: 指数代码
            start_date: 开始日期
            end_date: 结束日期
            fields: 字段列表
            
        Returns:
            DataFrame: 指数成分股数据
        """
        def _fetch():
            self._rate_limit()
            return self._pro.index_weight(
                index_code=index_code,
                start_date=start_date,
                end_date=end_date,
                fields=fields
            )
        
        try:
            result = self._retry_on_failure(_fetch)
            logger.debug(f"获取指数成分股 ({index_code}): {len(result)} 条")
            return result
        except Exception as e:
            raise DataFetchError(f"获取指数成分股失败 ({index_code}): {str(e)}") from e
    
    def get_roe_batch(
        self,
        ts_codes: List[str],
        trade_date: str,
        max_workers: int = 10
    ) -> pd.DataFrame:
        """
        批量获取 ROE 数据（并发）
        
        Args:
            ts_codes: 股票代码列表
            trade_date: 交易日期
            max_workers: 最大并发数
            
        Returns:
            DataFrame: ROE 数据
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        if not ts_codes:
            return pd.DataFrame(columns=["ts_code", "roe"])
        
        end_dt = datetime.strptime(trade_date, "%Y%m%d")
        start_dt = end_dt - timedelta(days=365)
        
        def get_roe_single(code: str) -> Optional[dict]:
            """获取单个股票的ROE"""
            try:
                df = self.get_fina_indicator(code, fields="ts_code,end_date,roe")
                if df.empty or "end_date" not in df.columns:
                    return None
                
                df["end_date"] = pd.to_datetime(df["end_date"], format="%Y%m%d", errors="coerce")
                df = df[(df["end_date"] >= start_dt) & (df["end_date"] <= end_dt)]
                if df.empty:
                    return None
                
                last = df.sort_values("end_date").iloc[-1]
                return {"ts_code": code, "roe": float(last["roe"])}
            except Exception as e:
                logger.debug(f"get_roe {code} 失败: {e}")
                return None
        
        out: List[dict] = []
        logger.info(f"开始并发获取ROE，共 {len(ts_codes)} 只股票，并发数: {max_workers}")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_code = {
                executor.submit(get_roe_single, code): code
                for code in ts_codes
            }
            
            with tqdm(total=len(ts_codes), desc="ROE获取进度", unit="只", ncols=80) as pbar:
                for future in as_completed(future_to_code):
                    try:
                        result = future.result()
                        if result:
                            out.append(result)
                    except Exception as e:
                        code = future_to_code[future]
                        logger.debug(f"get_roe {code} 任务异常: {e}")
                    finally:
                        pbar.update(1)
                        # 任务完成后短暂延迟
                        task_delay = self.config.get('api_rate_limit.task_delay', 0.02)
                        time.sleep(task_delay)
        
        if not out:
            return pd.DataFrame(columns=["ts_code", "roe"])
        
        logger.info(f"ROE获取完成，成功获取 {len(out)} 只股票的ROE数据")
        return pd.DataFrame(out)
