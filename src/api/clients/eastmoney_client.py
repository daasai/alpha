"""
Eastmoney API Client
封装东方财富免费 API 调用
"""
import time
from typing import List
from datetime import datetime

import pandas as pd
import requests
from tqdm import tqdm

from .base_client import BaseAPIClient
from ...logging_config import get_logger
from ...exceptions import APIError, DataFetchError

logger = get_logger(__name__)


class EastmoneyClient(BaseAPIClient):
    """东方财富免费 API 客户端"""
    
    def __init__(self, config=None):
        """
        初始化东方财富客户端
        
        Args:
            config: 配置管理器
        """
        super().__init__(config)
        self.base_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        self.session = requests.Session()
        logger.info("EastmoneyClient 初始化完成")
    
    def get_data(self, **kwargs) -> pd.DataFrame:
        """
        通用数据获取方法（不直接使用，使用具体方法）
        
        Args:
            **kwargs: 参数
            
        Returns:
            DataFrame
        """
        raise NotImplementedError("请使用具体的 API 方法")
    
    def get_notices(self, stock_list: List[str], start_date: str) -> pd.DataFrame:
        """
        获取公告信息
        
        Args:
            stock_list: 股票代码列表，格式如 ['600519.SH', '000001.SZ']
            start_date: 开始日期，格式 'YYYYMMDD'（会自动转换为 'YYYY-MM-DD'）
        
        Returns:
            pd.DataFrame: 包含 ts_code, ann_date, title, title_ch, art_code, column_names 列
        """
        logger.info(f"从东方财富获取 {len(stock_list)} 只股票的公告")
        
        all_notices = []
        total_stocks = len(stock_list)
        error_count = 0
        error_samples = []
        
        # 将 start_date 从 'YYYYMMDD' 转换为 'YYYY-MM-DD'
        try:
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            start_date_formatted = start_dt.strftime('%Y-%m-%d')
        except ValueError:
            # 如果已经是 'YYYY-MM-DD' 格式，直接使用
            start_date_formatted = start_date
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        
        logger.debug(f"查询开始日期: {start_date_formatted}")
        
        def _fetch_notice(stock_code: str) -> List[dict]:
            """获取单个股票的公告"""
            clean_code = stock_code.split('.')[0]
            
            params = {
                "sr": "-1",
                "page_size": "50",
                "page_index": "1",
                "ann_type": "A",
                "client_source": "web",
                "stock_list": clean_code,
                "f_node": "0",
                "s_node": "0"
            }
            
            self._rate_limit(delay=self.config.get('api_rate_limit.eastmoney_delay', 0.2))
            
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=self._request_timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            response.raise_for_status()
            data = response.json()
            
            notices = []
            if data.get('data') and data['data'].get('list'):
                for item in data['data']['list']:
                    notice_date_str = item.get('notice_date', '').split(' ')[0]
                    
                    if notice_date_str:
                        try:
                            notice_dt = datetime.strptime(notice_date_str, "%Y-%m-%d")
                            
                            if notice_dt >= start_dt:
                                columns_arr = item.get('columns') or []
                                column_names = '|'.join(
                                    str(c.get('column_name', '')).strip()
                                    for c in columns_arr
                                    if c and isinstance(c, dict)
                                )
                                notices.append({
                                    'ts_code': stock_code,
                                    'ann_date': notice_date_str.replace('-', ''),
                                    'title': item.get('title', ''),
                                    'title_ch': item.get('title_ch', ''),
                                    'art_code': item.get('art_code', ''),
                                    'column_names': column_names,
                                })
                        except ValueError:
                            logger.debug(f"日期格式解析失败: {notice_date_str}")
                            continue
            
            return notices
        
        logger.info(f"开始获取公告信息，共 {total_stocks} 只股票...")
        with tqdm(total=total_stocks, desc="  公告获取进度", unit="只", ncols=80) as pbar:
            for stock_code in stock_list:
                try:
                    notices = self._retry_on_failure(
                        lambda: _fetch_notice(stock_code),
                        exceptions=(requests.exceptions.RequestException,)
                    )
                    all_notices.extend(notices)
                except Exception as e:
                    error_count += 1
                    error_msg = str(e)
                    
                    if len(error_samples) < 3:
                        error_samples.append({
                            'ts_code': stock_code,
                            'error': error_msg[:150]
                        })
                    
                    if error_count <= 3 or (error_count % 50 == 0):
                        pbar.write(f"    错误示例 ({stock_code}): {error_msg[:100]}")
                    logger.debug(f"获取 {stock_code} 公告失败: {error_msg}")
                
                pbar.update(1)
        
        if error_count > 0:
            logger.warning(f"{error_count} 只股票获取公告失败（已跳过）")
            if error_samples:
                logger.debug(f"错误示例（前{len(error_samples)}个）:")
                for sample in error_samples:
                    logger.debug(f"  - {sample['ts_code']}: {sample['error']}")
        
        if not all_notices:
            logger.info("未获取到任何公告")
            return pd.DataFrame(columns=['ts_code', 'ann_date', 'title', 'title_ch', 'art_code', 'column_names'])
        
        result_df = pd.DataFrame(all_notices)
        logger.info(f"成功获取 {len(result_df)} 条公告")
        return result_df
