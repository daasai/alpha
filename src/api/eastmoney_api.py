"""
东方财富免费 API 封装
"""

import requests
import pandas as pd
from typing import List
from datetime import datetime
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


class EastmoneyAPI:
    """东方财富免费 API 封装"""
    
    def __init__(self):
        """初始化 API 客户端"""
        self.base_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        self.session = requests.Session()
        logger.info("东方财富 API 初始化成功")
    
    def get_notices(self, stock_list: List[str], start_date: str) -> pd.DataFrame:
        """
        获取公告信息
        
        Args:
            stock_list: 股票代码列表，格式如 ['600519.SH', '000001.SZ']
            start_date: 开始日期，格式 'YYYYMMDD'（会自动转换为 'YYYY-MM-DD'）
        
        Returns:
            pd.DataFrame: 包含 ts_code, ann_date, title, content 列
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
        
        # 使用 tqdm 显示进度
        logger.info(f"开始获取公告信息，共 {total_stocks} 只股票...")
        with tqdm(total=total_stocks, desc="  公告获取进度", unit="只", ncols=80) as pbar:
            for stock_code in stock_list:
                # 清洗代码：600519.SH -> 600519
                clean_code = stock_code.split('.')[0]
                
                try:
                    # 构造请求参数
                    params = {
                        "sr": "-1",
                        "page_size": "50",  # 最近50条足够覆盖短期异动
                        "page_index": "1",
                        "ann_type": "A",    # A代表公告
                        "client_source": "web",
                        "stock_list": clean_code, 
                        "f_node": "0",
                        "s_node": "0"
                    }
                    
                    # 发起请求
                    response = self.session.get(
                        self.base_url, 
                        params=params, 
                        timeout=10,
                        headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                        }
                    )
                    response.raise_for_status()  # 检查HTTP错误
                    data = response.json()
                    
                    # 解析返回数据
                    if data.get('data') and data['data'].get('list'):
                        for item in data['data']['list']:
                            # item['notice_date'] 格式通常为 '2023-10-27 00:00:00'
                            notice_date_str = item.get('notice_date', '').split(' ')[0]
                            
                            if notice_date_str:
                                try:
                                    notice_dt = datetime.strptime(notice_date_str, "%Y-%m-%d")
                                    
                                    # 过滤时间：只保留 start_date 之后的公告
                                    if notice_dt >= start_dt:
                                        all_notices.append({
                                            'ts_code': stock_code,
                                            'ann_date': notice_date_str.replace('-', ''),  # 转换为 YYYYMMDD 格式
                                            'title': item.get('title', ''),
                                            'content': item.get('title', '')  # 免费接口通常只能拿标题
                                        })
                                except ValueError:
                                    # 日期格式解析失败，跳过这条
                                    logger.debug(f"日期格式解析失败: {notice_date_str}")
                                    continue
                    
                    # 礼貌爬虫，避免被封IP，稍作延时
                    time.sleep(0.2)
                    
                except requests.exceptions.RequestException as e:
                    # 网络请求错误
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
                        
                except Exception as e:
                    # 其他错误
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
                
                # 更新进度条
                pbar.update(1)
        
        # 显示错误统计
        if error_count > 0:
            logger.warning(f"{error_count} 只股票获取公告失败（已跳过）")
            if error_samples:
                logger.debug(f"错误示例（前{len(error_samples)}个）:")
                for sample in error_samples:
                    logger.debug(f"  - {sample['ts_code']}: {sample['error']}")
        
        if not all_notices:
            logger.info("未获取到任何公告")
            return pd.DataFrame(columns=['ts_code', 'ann_date', 'title', 'content'])
        
        result_df = pd.DataFrame(all_notices)
        logger.info(f"成功获取 {len(result_df)} 条公告")
        return result_df
