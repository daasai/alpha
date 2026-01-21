"""
Momentum Factors
Relative Price Strength (RPS) Factor
"""

import pandas as pd
import numpy as np
from .base import BaseFactor


class RPSFactor(BaseFactor):
    """
    Relative Price Strength Factor
    
    Logic: Group by trade_date to rank pct_change (percentage change).
    RPS is the percentile rank of pct_change within each trade_date.
    """
    
    def __init__(self, window: int = 60):
        """
        Initialize RPS Factor.
        
        Args:
            window: Lookback window for calculating pct_change (default: 60)
        """
        self.window = window
    
    def name(self) -> str:
        """Return factor name"""
        return f"rps_{self.window}"
    
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute RPS factor.
        
        Requires columns: ts_code, trade_date, close (or pct_chg)
        
        Args:
            df: DataFrame with stock data
            
        Returns:
            DataFrame with 'rps' column added
        """
        if df.empty:
            return df
        
        df = df.copy()
        
        # Ensure trade_date is datetime for sorting
        if 'trade_date' in df.columns:
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        
        # Sort by ts_code and trade_date
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
        
        # Calculate pct_change if not present
        if 'pct_chg' not in df.columns and 'close' in df.columns:
            # 使用 pandas 的 pct_change 方法，更可靠
            # pct_change(periods=60) 计算的是当前价格相对于60个数据点前价格的涨跌幅
            # 注意：这里使用的是 periods（数据点数量），不是交易日数量
            # 如果数据不连续（有停牌等），需要确保有足够的数据点
            
            # 先检查数据情况
            from ..logging_config import get_logger
            logger = get_logger(__name__)
            
            # 检查每个股票有多少条数据
            stock_counts = df.groupby('ts_code').size()
            min_count = stock_counts.min()
            max_count = stock_counts.max()
            mean_count = stock_counts.mean()
            stocks_with_enough = (stock_counts >= self.window).sum()
            
            logger.info(f"RPS计算: 股票数据点统计 - 最小={min_count}, 最大={max_count}, 均值={mean_count:.1f}, ≥{self.window}条数据的股票={stocks_with_enough}/{len(stock_counts)}")
            
            # 使用 pandas 的 pct_change 方法
            # 这会自动处理每个股票组内的计算
            df['pct_chg'] = df.groupby('ts_code')['close'].pct_change(periods=self.window) * 100
            
            # 调试信息：检查有多少股票有有效的 pct_chg
            pct_chg_valid = df['pct_chg'].notna().sum()
            pct_chg_total = len(df)
            
            if pct_chg_valid == 0:
                logger.warning(f"RPS计算: 所有 pct_chg 都是 NaN (总数: {pct_chg_total})")
                logger.warning(f"可能原因: 数据不足{self.window}个数据点，或数据排序有问题")
            else:
                logger.info(f"RPS计算: pct_chg 有效值 {pct_chg_valid}/{pct_chg_total} ({pct_chg_valid/pct_chg_total*100:.1f}%)")
        elif 'pct_chg' not in df.columns:
            raise ValueError("RPSFactor requires either 'pct_chg' or 'close' column")
        
        # Group by trade_date and rank pct_change
        # Using percentile rank (0-100 scale)
        # 注意：只对有效的 pct_chg 值进行排名，NaN 值会被排除
        column_name = f'rps_{self.window}'
        
        # 对每个交易日的 pct_chg 进行排名
        # rank(pct=True) 返回的是百分比排名（0-1），乘以100得到0-100的RPS值
        # method='min' 表示相同值取最小排名
        # na_option='keep' 表示保留 NaN 值
        def rank_pct_chg(group):
            """对每个交易日的 pct_chg 进行百分比排名"""
            if group.notna().sum() == 0:
                # 如果所有值都是 NaN，返回 NaN
                return pd.Series([np.nan] * len(group), index=group.index)
            # 只对非 NaN 值进行排名
            ranked = group.rank(pct=True, method='min', na_option='keep')
            return ranked * 100
        
        # 在排名前按pct_chg和ts_code排序，确保相同值时的稳定性
        df = df.sort_values(['trade_date', 'pct_chg', 'ts_code']).reset_index(drop=True)
        df[column_name] = df.groupby('trade_date')['pct_chg'].transform(rank_pct_chg)
        
        # 确保RPS值在0-100范围内（处理可能的浮点误差）
        df[column_name] = df[column_name].clip(lower=0.0, upper=100.0)
        
        # 对于历史数据不足的股票，pct_chg 和 rps 都会是 NaN，这是正常的
        
        return df
