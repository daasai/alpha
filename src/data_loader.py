"""
Data Loader Module - 支持多种数据源的统一数据加载
负责从 Tushare Pro 和东方财富获取股票数据
"""

import os
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time
from tqdm import tqdm
import requests
import json
from typing import Optional, List

from .logging_config import get_logger

logger = get_logger(__name__)


class DataLoader:
    """统一数据加载器，支持多种数据源"""
    
    def __init__(self, use_free_api: bool = False, use_api_abstraction: bool = False):
        """
        初始化数据加载器
        
        Args:
            use_free_api: 是否使用免费 API（默认 False，使用 Tushare）
            use_api_abstraction: 是否使用API抽象层（默认 False，保持向后兼容）
        """
        # 加载 .env 文件
        load_dotenv()
        token = os.getenv('TUSHARE_TOKEN')
        
        self.use_free_api = use_free_api
        self.use_api_abstraction = use_api_abstraction
        
        # 如果使用API抽象层
        if use_api_abstraction:
            if use_free_api:
                logger.info("使用API抽象层 - 东方财富免费API")
                from .api.eastmoney_api import EastmoneyAPI
                self.eastmoney_api = EastmoneyAPI()
            else:
                logger.info("使用API抽象层 - Tushare Pro API")
                if not token:
                    raise ValueError("TUSHARE_TOKEN not found in .env file. Please set your Tushare Pro token.")
                from .api.tushare_api import TushareAPI
                self.tushare_api = TushareAPI(token)
        else:
            # 原有实现（向后兼容）
            if use_free_api:
                logger.info("使用东方财富免费 API（仅公告）")
                from .api.eastmoney_api import EastmoneyAPI
                self.eastmoney_api = EastmoneyAPI()
            else:
                logger.info("使用 Tushare Pro API（直接调用）")
            
            # Tushare 用于基础数据（股票列表、指标等）
            if not token:
                if not use_free_api:
                    raise ValueError("TUSHARE_TOKEN not found in .env file. Please set your Tushare Pro token.")
                else:
                    logger.warning("未找到TUSHARE_TOKEN，部分功能可能受限")
            else:
                ts.set_token(token)
                self.pro = ts.pro_api()
                logger.info("Tushare Pro API 初始化成功")
            
            # 东方财富公告接口 (免费API) - 保留用于向后兼容
            self.eastmoney_api_url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        
    def get_stock_basics(self):
        """
        获取全市场股票列表（包含上市状态、ST状态）
        
        Returns:
            pd.DataFrame: 包含股票代码、名称、上市日期、ST状态等信息
        """
        # 如果使用API抽象层
        if self.use_api_abstraction and not self.use_free_api:
            return self.tushare_api.get_stock_basics()
        
        try:
            # 获取股票基本信息
            stock_basic = self.pro.stock_basic(
                exchange='',
                list_status='L',  # L-上市
                fields='ts_code,symbol,name,area,industry,list_date,is_hs'
            )
            
            # 判断是否为ST股票（通过名称）
            stock_basic['is_st'] = stock_basic['name'].str.contains('ST|\\*ST', regex=True, na=False)
            
            logger.info(f"成功获取 {len(stock_basic)} 只股票")
            return stock_basic
            
        except Exception as e:
            logger.error(f"获取股票基本信息失败: {e}")
            raise
    
    def get_daily_indicators(self, trade_date):
        """
        获取每日基本面指标（PE_TTM, PB, 股息率, 总市值）
        
        Args:
            trade_date: 交易日期，格式 'YYYYMMDD'
            
        Returns:
            pd.DataFrame: 包含股票代码、PE_TTM、PB、股息率、总市值等指标
        """
        # 如果使用API抽象层
        if self.use_api_abstraction and not self.use_free_api:
            return self.tushare_api.get_daily_indicators(trade_date)
        
        try:
            # 获取每日指标
            daily_basic = self.pro.daily_basic(
                trade_date=trade_date,
                fields='ts_code,trade_date,pe,pb,dv_ttm,total_mv'
            )
            
            # 重命名列以匹配需求
            daily_basic = daily_basic.rename(columns={
                'pe': 'pe_ttm',
                'dv_ttm': 'dividend_yield',  # 股息率
                'total_mv': 'total_market_cap'  # 总市值（万元）
            })
            
            logger.info(f"成功获取 {len(daily_basic)} 条每日指标")
            return daily_basic
            
        except Exception as e:
            logger.error(f"获取每日指标失败: {e}")
            raise
    
    def get_financial_indicators(self, trade_date, stock_list=None):
        """
        获取财务指标（ROE, 净利润增长率）
        
        Args:
            trade_date: 交易日期，格式 'YYYYMMDD'
            stock_list: 可选的股票代码列表，如果为None则从stock_basic获取
            
        Returns:
            pd.DataFrame: 包含股票代码、ROE、净利润增长率等财务指标
        """
        # 如果使用API抽象层
        if self.use_api_abstraction and not self.use_free_api:
            return self.tushare_api.get_financial_indicators(trade_date, stock_list)
        
        try:
            # 如果没有提供股票列表，先获取股票列表
            if stock_list is None:
                stock_basics = self.get_stock_basics()
                stock_list = stock_basics['ts_code'].tolist()
            
            # 计算日期范围（获取过去一年的数据，然后取最新）
            end_date = trade_date
            start_date = (datetime.strptime(trade_date, '%Y%m%d') - timedelta(days=365)).strftime('%Y%m%d')
            start_dt = datetime.strptime(start_date, '%Y%m%d')
            end_dt = datetime.strptime(end_date, '%Y%m%d')
            
            all_indicators = []
            total_stocks = len(stock_list)
            error_count = 0
            
            # 批量获取财务指标（Tushare API 需要逐个股票代码获取）
            batch_size = 100  # 每批处理100只股票
            
            # 使用 tqdm 显示进度
            logger.info(f"开始获取财务指标，共 {total_stocks} 只股票...")
            with tqdm(total=total_stocks, desc="  财务指标进度", unit="只", ncols=80) as pbar:
                for i in range(0, len(stock_list), batch_size):
                    batch = stock_list[i:i+batch_size]
                    
                    for ts_code in batch:
                        try:
                            # 获取单个股票的财务指标
                            fina_indicator = self.pro.fina_indicator(
                                ts_code=ts_code,
                                fields='ts_code,end_date,roe,netprofit_yoy'
                            )
                            
                            if not fina_indicator.empty and 'end_date' in fina_indicator.columns:
                                # 过滤日期范围
                                fina_indicator['end_date'] = pd.to_datetime(fina_indicator['end_date'], format='%Y%m%d', errors='coerce')
                                fina_indicator = fina_indicator[
                                    (fina_indicator['end_date'] >= start_dt) & 
                                    (fina_indicator['end_date'] <= end_dt)
                                ]
                                
                                if not fina_indicator.empty:
                                    # 获取该股票的最新财务指标（按end_date排序，取最新的）
                                    latest = fina_indicator.sort_values('end_date').iloc[-1:].copy()
                                    all_indicators.append(latest)
                            
                            # 避免请求过快（Tushare API有频率限制）
                            time.sleep(0.2)
                            
                        except Exception as e:
                            # 单个股票失败不影响整体流程
                            error_count += 1
                        
                        # 更新进度条
                        pbar.update(1)
                    
                    # 每批之间稍作延迟
                    if i + batch_size < len(stock_list):
                        time.sleep(0.5)
            
            # 显示错误统计
            if error_count > 0:
                logger.warning(f"{error_count} 只股票获取财务指标失败（已跳过）")
            
            # 合并所有结果
            if all_indicators:
                result = pd.concat(all_indicators, ignore_index=True)
                # 转换日期回字符串格式
                result['end_date'] = result['end_date'].dt.strftime('%Y%m%d')
                # 重命名列
                result = result.rename(columns={
                    'netprofit_yoy': 'net_profit_growth_rate'  # 净利润增长率
                })
                logger.info(f"成功获取 {len(result)} 条财务指标")
                return result
            else:
                # 返回空 DataFrame，保持列结构
                logger.warning("未获取到任何财务指标")
                return pd.DataFrame(columns=['ts_code', 'end_date', 'roe', 'net_profit_growth_rate'])
            
        except Exception as e:
            logger.error(f"获取财务指标失败: {e}")
            # 返回空 DataFrame 而不是抛出异常，允许程序继续运行
            return pd.DataFrame(columns=['ts_code', 'end_date', 'roe', 'net_profit_growth_rate'])
    
    def get_notices(self, stock_list, start_date):
        """
        获取指定股票池的公告信息
        
        Args:
            stock_list: 股票代码列表
            start_date: 开始日期，格式 'YYYYMMDD'
            
        Returns:
            pd.DataFrame: 包含股票代码、公告日期、公告标题等信息
        """
        try:
            all_notices = []
            total_stocks = len(stock_list)
            error_count = 0
            error_samples = []  # 保存前几个错误示例
            
            # 计算结束日期（今天）
            end_date = datetime.now().strftime('%Y%m%d')
            
            # 检查日期范围
            logger.debug(f"公告查询日期范围: {start_date} 至 {end_date}")
            if start_date > end_date:
                logger.warning(f"开始日期 {start_date} 晚于结束日期 {end_date}，将使用当前日期作为开始日期")
                start_date = end_date
            
            # 如果使用免费API，调用免费API方法
            if self.use_free_api and hasattr(self, 'eastmoney_api'):
                logger.info("使用东方财富免费API获取公告")
                return self.eastmoney_api.get_notices(stock_list, start_date)
            
            # 批量获取公告（Tushare API 可能需要分批处理）
            batch_size = 50  # 每批处理50只股票
            
            # 使用 tqdm 显示进度
            logger.info(f"开始获取公告信息，共 {total_stocks} 只股票...")
            with tqdm(total=total_stocks, desc="  公告获取进度", unit="只", ncols=80) as pbar:
                for i in range(0, len(stock_list), batch_size):
                    batch = stock_list[i:i+batch_size]
                    
                    for ts_code in batch:
                        try:
                            # 获取公告数据
                            # 使用 anns_d 接口（上市公司公告接口）
                            # 注意：anns_d 接口参数为 ann_date, start_date, end_date
                            notices = self.pro.anns_d(
                                ts_code=ts_code,
                                start_date=start_date,
                                end_date=end_date
                            )
                            
                            # 注意：API可能返回空DataFrame，这不一定是错误
                            # 只有当API抛出异常才算错误
                            if not notices.empty:
                                # anns_d 接口返回的字段：ann_date, ts_code, name, title, url, rec_time
                                # 确保包含我们需要的字段
                                if 'ts_code' in notices.columns and 'ann_date' in notices.columns:
                                    all_notices.append(notices)
                            
                            # 避免请求过快
                            time.sleep(0.2)
                            
                        except Exception as e:
                            # 单个股票失败不影响整体流程
                            error_count += 1
                            error_msg = str(e)
                            
                            # 保存前3个错误示例用于诊断
                            if len(error_samples) < 3:
                                error_samples.append({
                                    'ts_code': ts_code,
                                    'error': error_msg[:150]  # 限制长度
                                })
                            
                            # 只在第一批或错误较多时打印示例错误，避免输出过多
                            if error_count <= 3 or (error_count % 50 == 0):
                                pbar.write(f"    错误示例 ({ts_code}): {error_msg[:100]}")
                        
                        # 更新进度条
                        pbar.update(1)
            
            # 显示错误统计和成功统计
            success_count = total_stocks - error_count
            if error_count > 0:
                logger.warning(f"{error_count} 只股票获取公告失败（已跳过）")
                if error_samples:
                    logger.debug(f"错误示例（前{len(error_samples)}个）:")
                    for sample in error_samples:
                        logger.debug(f"  - {sample['ts_code']}: {sample['error']}")
            
            if success_count > 0 and len(all_notices) == 0:
                logger.info(f"{success_count} 只股票API调用成功，但无公告数据（可能该时间段内确实无公告）")
            
            # 诊断提示
            if error_count == total_stocks:
                logger.error("所有股票都失败，可能是API权限问题或日期格式问题")
                logger.info("请检查Tushare Pro账户是否有anns_d接口权限（可能需要独立申请）")
                logger.info(f"日期范围: {start_date} 至 {end_date}")
                logger.info("建议: 检查Tushare Pro积分和接口权限")
                logger.info("参考文档: https://tushare.pro/document/2?doc_id=176")
            
            if all_notices:
                result = pd.concat(all_notices, ignore_index=True)
                # anns_d 接口返回的字段：ann_date, ts_code, name, title, url, rec_time
                # 我们需要：ts_code, ann_date, title
                # 确保返回的DataFrame包含所需字段
                required_cols = ['ts_code', 'ann_date', 'title']
                
                # 检查并选择需要的列
                available_cols = result.columns.tolist()
                cols_to_select = [col for col in required_cols if col in available_cols]
                
                if len(cols_to_select) == len(required_cols):
                    # 所有需要的列都存在，直接返回
                    logger.info(f"成功获取 {len(result)} 条公告")
                    return result[required_cols].copy()
                else:
                    # 某些列缺失，创建包含所有列的DataFrame
                    output_df = pd.DataFrame()
                    for col in required_cols:
                        if col in available_cols:
                            output_df[col] = result[col]
                        else:
                            output_df[col] = ''  # 填充空值
                    logger.info(f"成功获取 {len(output_df)} 条公告（部分字段缺失）")
                    return output_df
            else:
                # 返回空 DataFrame，保持列结构
                logger.info("未获取到任何公告")
                return pd.DataFrame(columns=['ts_code', 'ann_date', 'title'])
                
        except Exception as e:
            logger.error(f"获取公告失败: {e}")
            raise
    
    def get_notices_free(self, stock_list, start_date):
        """
        [免费版] 获取公告，使用东方财富免费API替代Tushare接口
        
        Args:
            stock_list: 股票代码列表，格式如 ['600519.SH', '000001.SZ']
            start_date: 开始日期，格式 'YYYYMMDD'（会自动转换为 'YYYY-MM-DD'）
            
        Returns:
            pd.DataFrame: 包含 ts_code, ann_date, title, title_ch, art_code, column_names 列
            （不包含 content；正文须经 art_code 详情页二次获取，见 README）
        """
        try:
            # 如果已经初始化了eastmoney_api，直接使用（返回 ts_code, ann_date, title, title_ch, art_code, column_names）
            if hasattr(self, 'eastmoney_api'):
                logger.info("使用已初始化的东方财富API")
                return self.eastmoney_api.get_notices(stock_list, start_date)
            
            all_notices = []
            total_stocks = len(stock_list)
            error_count = 0
            error_samples = []
            
            # 将 start_date 从 'YYYYMMDD' 转换为 'YYYY-MM-DD'
            try:
                start_dt = datetime.strptime(start_date, '%Y%m%d')
                start_date_formatted = start_dt.strftime('%Y-%m-%d')
            except ValueError:
                start_date_formatted = start_date
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            
            # 使用 tqdm 显示进度
            logger.info(f"正在从东方财富获取公告信息，共 {total_stocks} 只股票...")
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
                        response = requests.get(
                            self.eastmoney_api_url, 
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
                                            columns_arr = item.get('columns') or []
                                            column_names = '|'.join(
                                                str(c.get('column_name', '')).strip()
                                                for c in columns_arr
                                                if c and isinstance(c, dict)
                                            )
                                            all_notices.append({
                                                'ts_code': stock_code,
                                                'ann_date': notice_date_str.replace('-', ''),
                                                'title': item.get('title', ''),
                                                'title_ch': item.get('title_ch', ''),
                                                'art_code': item.get('art_code', ''),
                                                'column_names': column_names,
                                            })
                                    except ValueError:
                                        # 日期格式解析失败，跳过这条
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
                return pd.DataFrame(columns=['ts_code', 'ann_date', 'title', 'title_ch', 'art_code', 'column_names'])
            
            result_df = pd.DataFrame(all_notices)
            logger.info(f"成功获取 {len(result_df)} 条公告")
            return result_df
            
        except Exception as e:
            logger.error(f"从东方财富获取公告失败: {e}")
            return pd.DataFrame(columns=['ts_code', 'ann_date', 'title', 'title_ch', 'art_code', 'column_names'])
