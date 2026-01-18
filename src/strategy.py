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
