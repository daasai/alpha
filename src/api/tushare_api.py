"""
Tushare API 封装
"""

from typing import Optional, List
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
import time
from tqdm import tqdm

import sys
from pathlib import Path

# 修复导入路径
api_dir = Path(__file__).parent
src_dir = api_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from src.logging_config import get_logger

logger = get_logger(__name__)


class TushareAPI:
    """Tushare Pro API 统一封装"""
    
    def __init__(self, token: str):
        """初始化 API 客户端"""
        ts.set_token(token)
        self.pro = ts.pro_api()
        logger.info("Tushare Pro API 初始化成功")
    
    def get_stock_basics(self) -> pd.DataFrame:
        """获取股票基本信息"""
        logger.debug("获取股票基本信息...")
        try:
            result = self.pro.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,area,industry,list_date,is_hs'
            )
            # 判断是否为ST股票（通过名称）
            result['is_st'] = result['name'].str.contains('ST|\\*ST', regex=True, na=False)
            logger.info(f"成功获取 {len(result)} 只股票")
            return result
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {e}")
            raise
    
    def get_daily_indicators(self, trade_date: str) -> pd.DataFrame:
        """获取每日指标"""
        logger.debug(f"获取 {trade_date} 的每日指标...")
        try:
            result = self.pro.daily_basic(
                trade_date=trade_date,
                fields='ts_code,trade_date,pe,pb,dv_ttm,total_mv'
            )
            # 重命名列
            result = result.rename(columns={
                'pe': 'pe_ttm',
                'dv_ttm': 'dividend_yield',
                'total_mv': 'total_market_cap'
            })
            logger.info(f"成功获取 {len(result)} 条每日指标")
            return result
        except Exception as e:
            logger.error(f"获取每日指标失败: {e}")
            raise
    
    def get_financial_indicators(self, trade_date: str, stock_list: Optional[List[str]] = None) -> pd.DataFrame:
        """获取财务指标"""
        if stock_list is None:
            logger.warning("未提供股票列表，将跳过财务指标获取")
            return pd.DataFrame(columns=['ts_code', 'end_date', 'roe', 'net_profit_growth_rate'])
        
        logger.debug(f"获取 {len(stock_list)} 只股票的财务指标...")
        
        # 计算日期范围
        end_date = trade_date
        start_date = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=365)).strftime('%Y%m%d')
        start_dt = datetime.strptime(start_date, '%Y%m%d')
        end_dt = datetime.strptime(end_date, '%Y%m%d')
        
        all_indicators = []
        batch_size = 100
        
        logger.info(f"开始获取财务指标，共 {len(stock_list)} 只股票...")
        with tqdm(total=len(stock_list), desc="  财务指标进度", unit="只", ncols=80) as pbar:
            for i in range(0, len(stock_list), batch_size):
                batch = stock_list[i:i+batch_size]
                
                for ts_code in batch:
                    try:
                        fina_indicator = self.pro.fina_indicator(
                            ts_code=ts_code,
                            fields='ts_code,end_date,roe,netprofit_yoy'
                        )
                        
                        if not fina_indicator.empty and 'end_date' in fina_indicator.columns:
                            fina_indicator['end_date'] = pd.to_datetime(fina_indicator['end_date'], format='%Y%m%d', errors='coerce')
                            fina_indicator = fina_indicator[
                                (fina_indicator['end_date'] >= start_dt) & 
                                (fina_indicator['end_date'] <= end_dt)
                            ]
                            
                            if not fina_indicator.empty:
                                latest = fina_indicator.sort_values('end_date').iloc[-1:].copy()
                                all_indicators.append(latest)
                        
                        time.sleep(0.2)
                        
                    except Exception as e:
                        logger.debug(f"获取 {ts_code} 财务指标失败: {e}")
                    
                    pbar.update(1)
                
                if i + batch_size < len(stock_list):
                    time.sleep(0.5)
        
        if all_indicators:
            result = pd.concat(all_indicators, ignore_index=True)
            result['end_date'] = result['end_date'].dt.strftime('%Y%m%d')
            result = result.rename(columns={
                'netprofit_yoy': 'net_profit_growth_rate'
            })
            logger.info(f"成功获取 {len(result)} 条财务指标")
            return result
        else:
            logger.warning("未获取到任何财务指标")
            return pd.DataFrame(columns=['ts_code', 'end_date', 'roe', 'net_profit_growth_rate'])
    
    def get_notices(self, stock_list: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """获取公告信息（使用Tushare anns_d接口）"""
        logger.info(f"从Tushare获取 {len(stock_list)} 只股票的公告")
        logger.debug(f"查询日期范围: {start_date} 至 {end_date}")
        
        all_notices = []
        error_count = 0
        
        with tqdm(total=len(stock_list), desc="  公告获取进度", unit="只", ncols=80) as pbar:
            for ts_code in stock_list:
                try:
                    notices = self.pro.anns_d(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date
                    )
                    
                    if not notices.empty:
                        all_notices.append(notices)
                    
                    time.sleep(0.2)
                    
                except Exception as e:
                    error_count += 1
                    logger.debug(f"获取 {ts_code} 公告失败: {e}")
                
                pbar.update(1)
        
        if error_count > 0:
            logger.warning(f"{error_count} 只股票获取公告失败")
        
        if all_notices:
            result = pd.concat(all_notices, ignore_index=True)
            required_cols = ['ts_code', 'ann_date', 'title']
            if all(col in result.columns for col in required_cols):
                return result[required_cols].copy()
            else:
                output_df = pd.DataFrame()
                for col in required_cols:
                    if col in result.columns:
                        output_df[col] = result[col]
                    else:
                        output_df[col] = ''
                return output_df
        else:
            return pd.DataFrame(columns=['ts_code', 'ann_date', 'title'])
