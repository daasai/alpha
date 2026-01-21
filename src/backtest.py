"""
Vector Backtester - DAAS Alpha v1.2.2
Portfolio Position Sizing with Day-by-Day Simulation
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime, timedelta

from .logging_config import get_logger
from .data_provider import DataProvider
from .factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor, BBIFactor
from .config_manager import ConfigManager

logger = get_logger(__name__)


# 回测结果类型定义（使用Dict[str, Any]作为返回类型，因为TypedDict不支持pd.Series等复杂类型）
# BacktestResultDict = {
#     'total_return': float,
#     'max_drawdown': float,
#     'win_rate': float,
#     'equity_curve': pd.Series,
#     'benchmark_equity_curve': pd.Series,
#     'strategy_metrics': Dict[str, float],
#     'benchmark_metrics': Dict[str, float],
#     'trades': pd.DataFrame,
#     'top_contributors': pd.DataFrame
# }


def _normalize_date(date_value):
    """
    统一日期格式转换，确保返回pd.Timestamp类型
    
    Args:
        date_value: 日期值（可以是str, datetime, pd.Timestamp等）
        
    Returns:
        pd.Timestamp或pd.NaT
    """
    if pd.isna(date_value):
        return pd.NaT
    if isinstance(date_value, pd.Timestamp):
        return date_value
    if isinstance(date_value, str):
        # 尝试多种格式
        return pd.to_datetime(date_value, format='%Y%m%d', errors='coerce')
    return pd.to_datetime(date_value, errors='coerce')


class VectorBacktester:
    """
    Portfolio Backtester for Alpha Trident Strategy (v1.2.2)
    
    Features:
    - Portfolio position sizing (MAX_POSITIONS = 4, 25% per position)
    - Day-by-day simulation with cash and position tracking
    - Risk management: Stop loss logic and holding days
    - Mark-to-market equity calculation
    - Performance metrics: Win Rate, Total Return, Max Drawdown, Equity Curve
    - Top 3 Contributors identification
    - Benchmark comparison (CSI300)
    """
    
    def __init__(self, data_provider: Optional[DataProvider] = None, config: Optional[ConfigManager] = None):
        """
        Initialize Vector Backtester
        
        Args:
            data_provider: DataProvider instance (creates new one if None)
            config: ConfigManager instance (creates new one if None)
        """
        self.data_provider = data_provider or DataProvider()
        self.config = config or ConfigManager()
        
        # 从配置获取因子参数
        rps_window = self.config.get('factors.rps.window', 60)
        ma_window = self.config.get('factors.ma.window', 20)
        volume_ratio_window = self.config.get('factors.volume_ratio.window', 5)
        pe_max = self.config.get('factors.pe.max', 30)
        
        self.factor_pipeline = FactorPipeline()
        self.factor_pipeline.add(RPSFactor(window=rps_window))
        self.factor_pipeline.add(MAFactor(window=ma_window))
        self.factor_pipeline.add(VolumeRatioFactor(window=volume_ratio_window))
        self.factor_pipeline.add(PEProxyFactor(max_pe=pe_max))
        
        logger.info("VectorBacktester 初始化完成")
    
    def _generate_buy_signals(self, df: pd.DataFrame, rps_threshold: Optional[float] = None) -> pd.DataFrame:
        """
        生成买入信号（使用AlphaStrategy逻辑，向量化实现）
        
        Args:
            df: 包含因子列的DataFrame
            rps_threshold: RPS阈值，如果为None则使用默认值85
            
        Returns:
            DataFrame with 'buy_signal' column (1 = buy, 0 = no buy)
        """
        df = df.copy()
        
        # 检查必需的因子列
        required_cols = ['rps_60', 'is_undervalued', 'vol_ratio_5', 'above_ma_20']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需的因子列: {missing_cols}")
        
        # 使用提供的rps_threshold，如果没有提供则使用默认值85
        if rps_threshold is None:
            rps_threshold = 85
        
        # Alpha Trident筛选条件（向量化）
        # 1. rps_60 > rps_threshold (Momentum)
        # 2. is_undervalued == 1 (Value)
        # 3. vol_ratio_5 > 1.5 (Liquidity)
        # 4. above_ma_20 == 1 (Trend)
        
        df['buy_signal'] = (
            (df['rps_60'] > rps_threshold) &
            (df['is_undervalued'] == 1) &
            (df['vol_ratio_5'] > 1.5) &
            (df['above_ma_20'] == 1)
        ).astype(int)
        
        logger.debug(f"生成买入信号: {df['buy_signal'].sum()} 个信号 (RPS阈值: {rps_threshold})")
        return df
    
    def _calculate_returns(
        self, 
        df: pd.DataFrame, 
        holding_days: int = 5,
        stop_loss_pct: float = 0.08,
        cost_rate: float = 0.002
    ) -> pd.DataFrame:
        """
        计算收益率（向量化优化，包含止损和交易成本）
        
        **注意**: 此方法主要用于单元测试，实际回测使用 `_simulate_portfolio` 方法。
        
        两种实现方式的区别：
        - `_calculate_returns`: 向量化实现，假设所有数据完整，适用于快速计算和测试
        - `_simulate_portfolio`: 逐日模拟，处理数据缺失、停牌等实际情况，更接近真实交易
        
        在边界情况下（如数据缺失、停牌等），两种实现可能产生不同结果。
        请确保测试覆盖这些场景，并优先使用 `_simulate_portfolio` 的结果。
        
        逻辑：
        - 买入：T+1 Open (Buy_Price)
        - 检查止损：从T+1到T+1+HoldingDays，如果任何一天的Low < Buy_Price * (1 - stop_loss_pct)，触发止损
        - 正常退出：T+1+HoldingDays Close
        - 收益率：(Exit_Price - Buy_Price) / Buy_Price - cost_rate
        
        Args:
            df: 包含buy_signal和价格数据的DataFrame
            holding_days: 持仓天数，默认5天
            stop_loss_pct: 止损百分比，默认0.08 (8%)
            cost_rate: 交易成本率，默认0.002 (0.2%)
            
        Returns:
            DataFrame with 'return' column
        """
        df = df.copy()
        
        # 确保按ts_code和trade_date排序
        df = df.sort_values(['ts_code', 'trade_date']).reset_index(drop=True)
        
        # 确保trade_date是datetime类型
        if df['trade_date'].dtype == 'object':
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
        
        # 检查必需的列
        required_cols = ['open', 'close', 'low']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需的价格列: {missing_cols}")
        
        df['return'] = np.nan
        
        # 买入价格：T+1 Open
        df['buy_price'] = df.groupby('ts_code')['open'].shift(-1)
        
        # 卖出价格：T+1+HoldingDays Close
        df['sell_price'] = df.groupby('ts_code')['close'].shift(-(1 + holding_days))
        
        # 向量化检查止损：为每个持仓日创建shift列，检查Low价格
        # 创建holding_days个shift列，检查T+1到T+1+HoldingDays的Low价格
        stop_loss_triggered = pd.Series(False, index=df.index)
        
        for day in range(1, holding_days + 1):
            # 获取T+day的Low价格
            low_price = df.groupby('ts_code')['low'].shift(-day)
            # 检查是否触发止损：Low < Buy_Price * (1 - stop_loss_pct)
            stop_loss_mask = (low_price < df['buy_price'] * (1 - stop_loss_pct)) & df['buy_price'].notna()
            stop_loss_triggered = stop_loss_triggered | stop_loss_mask
        
        # 仅对买入信号计算收益率
        buy_mask = df['buy_signal'] == 1
        valid_mask = (
            buy_mask & 
            df['buy_price'].notna() & 
            (df['buy_price'] > 0)
        )
        
        # 计算收益率
        # 如果触发止损：return = -stop_loss_pct - cost_rate
        # 否则：return = (sell_price - buy_price) / buy_price - cost_rate
        stop_loss_mask = valid_mask & stop_loss_triggered
        normal_exit_mask = valid_mask & ~stop_loss_triggered & df['sell_price'].notna()
        
        # 止损情况
        df.loc[stop_loss_mask, 'return'] = (-stop_loss_pct - cost_rate) * 100
        
        # 正常退出情况
        df.loc[normal_exit_mask, 'return'] = (
            (df.loc[normal_exit_mask, 'sell_price'] - df.loc[normal_exit_mask, 'buy_price']) / 
            df.loc[normal_exit_mask, 'buy_price'] - cost_rate
        ) * 100
        
        # 清理临时列
        df = df.drop(columns=['buy_price', 'sell_price'])
        
        return df
    
    def _get_benchmark_data(
        self, 
        start_date: str, 
        end_date: str,
        index_code: str = "000300.SH"
    ) -> pd.DataFrame:
        """
        获取基准指数数据（CSI300）并计算BBI
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            index_code: 指数代码，默认沪深300
            
        Returns:
            DataFrame with trade_date, close, benchmark_return, bbi, bbi_confirmed_signal
        """
        try:
            # 获取指数日线数据
            index_df = self.data_provider._tushare_client._pro.index_daily(
                ts_code=index_code,
                start_date=start_date,
                end_date=end_date,
                fields="trade_date,close"
            )
            
            if index_df.empty:
                logger.warning(f"无法获取基准指数数据: {index_code}")
                return pd.DataFrame()
            
            index_df['trade_date'] = pd.to_datetime(index_df['trade_date'], format='%Y%m%d', errors='coerce')
            index_df = index_df.sort_values('trade_date').reset_index(drop=True)
            
            # 计算基准收益率（每日收益率）
            index_df['benchmark_return'] = index_df['close'].pct_change() * 100
            
            # 应用BBIFactor计算BBI信号（从配置读取参数）
            bbi_ma_windows = self.config.get('factors.bbi.ma_windows', [3, 6, 12, 24])
            bbi_confirmation_days = self.config.get('factors.bbi.confirmation_days', 3)
            bbi_factor = BBIFactor(ma_windows=bbi_ma_windows, confirmation_days=bbi_confirmation_days)
            index_df = bbi_factor.compute(index_df)
            
            logger.info(f"基准指数BBI计算完成: {len(index_df)} 条数据, BBI确认信号范围: {index_df['bbi_confirmed_signal'].min()} 到 {index_df['bbi_confirmed_signal'].max()}")
            
            return index_df
        except Exception as e:
            logger.error(f"获取基准数据失败: {e}")
            return pd.DataFrame()
    
    def _extract_bbi_signals(self, benchmark_df: pd.DataFrame) -> Dict[pd.Timestamp, int]:
        """
        从基准数据中提取BBI确认信号字典
        
        Args:
            benchmark_df: 基准数据DataFrame
            
        Returns:
            Dict: {trade_date: bbi_confirmed_signal}
        """
        bbi_signal_dict = {}
        if not benchmark_df.empty and 'trade_date' in benchmark_df.columns and 'bbi_confirmed_signal' in benchmark_df.columns:
            for _, row in benchmark_df.iterrows():
                trade_date = row['trade_date']
                bbi_confirmed_signal = row['bbi_confirmed_signal']
                if pd.notna(trade_date) and pd.notna(bbi_confirmed_signal):
                    # 确保trade_date是datetime类型
                    if isinstance(trade_date, str):
                        trade_date = pd.to_datetime(trade_date, format='%Y%m%d', errors='coerce')
                    elif not isinstance(trade_date, pd.Timestamp):
                        trade_date = pd.to_datetime(trade_date, errors='coerce')
                    
                    if pd.notna(trade_date):
                        bbi_signal_dict[trade_date] = int(bbi_confirmed_signal)
            logger.info(f"BBI确认信号字典创建完成: {len(bbi_signal_dict)} 个交易日（使用3日确认规则）")
        else:
            logger.warning("无法获取BBI确认信号，将不进行市场状态过滤")
        
        return bbi_signal_dict
    
    def _calculate_benchmark_metrics(self, benchmark_df: pd.DataFrame) -> Dict[str, float]:
        """
        计算基准性能指标
        
        Args:
            benchmark_df: 基准数据DataFrame
            
        Returns:
            Dict包含: total_return, max_drawdown, avg_return
        """
        if benchmark_df.empty or 'benchmark_return' not in benchmark_df.columns:
            return {
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'avg_return': 0.0,
            }
        
        # 计算基准累计收益率
        benchmark_cumulative = (1 + benchmark_df['benchmark_return'] / 100).cumprod()
        benchmark_total_return = (benchmark_cumulative.iloc[-1] - 1) * 100 if len(benchmark_cumulative) > 0 else 0.0
        
        # 计算基准最大回撤
        benchmark_running_max = benchmark_cumulative.expanding().max()
        benchmark_drawdown = (benchmark_cumulative - benchmark_running_max) / benchmark_running_max * 100
        benchmark_max_drawdown = abs(benchmark_drawdown.min()) if not benchmark_drawdown.empty else 0.0
        
        return {
            'total_return': float(benchmark_total_return),
            'max_drawdown': float(benchmark_max_drawdown),
            'avg_return': float(benchmark_df['benchmark_return'].mean()),
        }
    
    def _calculate_benchmark_equity_curve(
        self, 
        benchmark_df: pd.DataFrame, 
        strategy_dates: pd.DatetimeIndex
    ) -> pd.Series:
        """
        基于实际基准收益率序列计算净值曲线
        
        Args:
            benchmark_df: 基准数据DataFrame
            strategy_dates: 策略净值曲线的日期索引
            
        Returns:
            Series: 基准净值曲线（对齐到策略日期）
        """
        if benchmark_df.empty or 'benchmark_return' not in benchmark_df.columns:
            return pd.Series(dtype=float)
        
        # 确保基准数据按日期排序
        benchmark_df = benchmark_df.sort_values('trade_date').reset_index(drop=True)
        
        # 计算累计净值
        benchmark_cumulative = (1 + benchmark_df['benchmark_return'] / 100).cumprod()
        
        # 创建基准净值Series
        benchmark_series = pd.Series(
            index=benchmark_df['trade_date'],
            data=benchmark_cumulative.values
        )
        
        # 对齐到策略日期（前向填充）
        aligned_benchmark = benchmark_series.reindex(
            strategy_dates, 
            method='ffill'
        ).fillna(1.0)
        
        return aligned_benchmark
    
    def _calculate_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """
        计算性能指标
        
        Args:
            returns: 收益率序列
            
        Returns:
            Dict包含: win_rate, total_return, max_drawdown, avg_return, sharpe_ratio
        """
        if returns.empty or returns.isna().all():
            return {
                'win_rate': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'avg_return': 0.0,
                'sharpe_ratio': 0.0,
                'total_trades': 0
            }
        
        # 移除NaN
        valid_returns = returns.dropna()
        
        if len(valid_returns) == 0:
            return {
                'win_rate': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'avg_return': 0.0,
                'sharpe_ratio': 0.0,
                'total_trades': 0
            }
        
        # Win Rate
        win_rate = (valid_returns > 0).sum() / len(valid_returns) * 100
        
        # Total Return (累计收益率)
        total_return = valid_returns.sum()
        
        # Average Return
        avg_return = valid_returns.mean()
        
        # Max Drawdown
        cumulative = (1 + valid_returns / 100).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = abs(drawdown.min()) if not drawdown.empty else 0.0
        
        # Sharpe Ratio (简化版，假设无风险利率为0)
        std_return = valid_returns.std()
        sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0.0
        
        return {
            'win_rate': float(win_rate),
            'total_return': float(total_return),
            'max_drawdown': float(max_drawdown),
            'avg_return': float(avg_return),
            'sharpe_ratio': float(sharpe_ratio),
            'total_trades': len(valid_returns)
        }
    
    def _calculate_portfolio_curve(
        self, 
        returns_df: pd.DataFrame
    ) -> pd.Series:
        """
        计算组合净值曲线（等权重）
        
        逻辑：
        - 对于每个交易日，将所有买入信号的收益率等权重平均
        - 计算累计净值
        
        Args:
            returns_df: 包含buy_signal和return的DataFrame
            
        Returns:
            Series: 净值曲线（按日期索引）
        """
        # 提取所有交易
        trades = returns_df[returns_df['buy_signal'] == 1].copy()
        trades = trades[trades['return'].notna()].copy()
        
        if trades.empty:
            return pd.Series(dtype=float)
        
        # 确保trade_date是datetime类型
        if trades['trade_date'].dtype == 'object':
            trades['trade_date'] = pd.to_datetime(trades['trade_date'], format='%Y%m%d', errors='coerce')
        
        # 按日期分组，计算每日平均收益率（等权重）
        daily_returns = trades.groupby('trade_date')['return'].mean()
        
        # 转换为小数形式（从百分比）
        daily_returns_pct = daily_returns / 100
        
        # 计算累计净值曲线
        equity_curve = (1 + daily_returns_pct).cumprod()
        
        return equity_curve
    
    def _validate_price_data(
        self, 
        price_dict: Dict, 
        trade_date: pd.Timestamp, 
        ts_code: str
    ) -> tuple[Optional[Dict[str, float]], Optional[str]]:
        """
        验证价格数据的完整性和有效性
        
        Args:
            price_dict: 价格字典
            trade_date: 交易日期
            ts_code: 股票代码
            
        Returns:
            (prices_dict, error_message): 如果有效返回价格字典和None，否则返回None和错误信息
        """
        if trade_date not in price_dict or ts_code not in price_dict[trade_date]:
            return None, "数据缺失"
        
        prices = price_dict[trade_date][ts_code]
        
        # 检查价格有效性
        required_keys = ['open', 'close', 'low', 'high']
        for key in required_keys:
            value = prices.get(key, np.nan)
            if np.isnan(value) or value <= 0:
                return None, f"{key}价格无效"
        
        return prices, None
    
    def _count_trading_days(self, start_date: pd.Timestamp, end_date: pd.Timestamp, trade_dates: List[pd.Timestamp]) -> int:
        """
        计算两个日期之间的交易日数量
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            trade_dates: 所有交易日列表
            
        Returns:
            交易日数量
        """
        if start_date >= end_date:
            return 0
        
        # 找到start_date和end_date在trade_dates中的索引
        start_idx = None
        end_idx = None
        
        for i, date in enumerate(trade_dates):
            if start_idx is None and date >= start_date:
                start_idx = i
            if end_idx is None and date > end_date:
                end_idx = i
                break
        
        if start_idx is None:
            return 0
        if end_idx is None:
            end_idx = len(trade_dates)
        
        return max(0, end_idx - start_idx)
    
    def _simulate_portfolio(
        self,
        signal_df: pd.DataFrame,
        initial_capital: float = 1000000.0,
        holding_days: int = 5,
        stop_loss_pct: float = 0.08,
        cost_rate: float = 0.002,
        max_positions: int = 4,
        bbi_signal_dict: Optional[Dict[pd.Timestamp, int]] = None
    ) -> Dict[str, Any]:
        """
        模拟投资组合（逐日模拟）
        
        Args:
            signal_df: 包含buy_signal和价格数据的DataFrame
            initial_capital: 初始资金，默认100万
            holding_days: 持仓天数，默认5天
            stop_loss_pct: 止损百分比，默认0.08 (8%)
            cost_rate: 交易成本率，默认0.002 (0.2%)
            max_positions: 最大持仓数，默认4
            
        Returns:
            Dict包含: equity_curve, trades, stock_contributions
        """
        # 确保trade_date是datetime类型
        if signal_df['trade_date'].dtype == 'object':
            signal_df['trade_date'] = pd.to_datetime(signal_df['trade_date'], format='%Y%m%d', errors='coerce')
        
        # 按日期排序
        signal_df = signal_df.sort_values('trade_date').reset_index(drop=True)
        
        # 获取所有交易日
        trade_dates = sorted(signal_df['trade_date'].unique())
        
        # 初始化
        cash = initial_capital
        positions = {}  # {ts_code: {'buy_date': date, 'buy_price': price, 'shares': shares}}
        equity_curve = []
        trades = []
        stock_contributions = {}  # {ts_code: total_gain}
        
        weight_per_pos = 1.0 / max_positions
        
        # 创建价格查找字典（按日期和股票代码）- 优化：使用groupby替代iterrows
        price_dict = {}
        price_cols = ['open', 'close', 'low', 'high']
        
        # 使用groupby按日期分组，然后按股票代码分组
        for date, date_group in signal_df.groupby('trade_date'):
            price_dict[date] = {}
            for _, row in date_group.iterrows():
                code = row['ts_code']
                price_dict[date][code] = {
                    col: row.get(col, np.nan) for col in price_cols
                }
        
        # 逐日模拟
        for trade_date in trade_dates:
            # 1. 卖出逻辑：检查现有持仓
            positions_to_remove = []
            for ts_code, pos_info in positions.items():
                buy_price = pos_info['buy_price']
                buy_date = pos_info['buy_date']
                
                # 只在买入日之后才检查卖出条件（避免买入当天就卖出）
                if trade_date <= buy_date:
                    continue
                
                # 计算持仓天数：使用交易日计数（更准确）
                trading_days_held = self._count_trading_days(buy_date, trade_date, trade_dates)
                holding_period_reached = trading_days_held >= holding_days
                
                # 验证并获取当日价格数据
                current_prices, price_error = self._validate_price_data(price_dict, trade_date, ts_code)
                
                if price_error:
                    logger.warning(f"股票 {ts_code} 在 {trade_date} 价格数据验证失败: {price_error}")
                    # 如果价格数据无效，尝试使用前一日价格（如果存在）
                    prev_date_idx = None
                    for i, date in enumerate(trade_dates):
                        if date == trade_date:
                            prev_date_idx = i - 1
                            break
                    
                    if prev_date_idx is not None and prev_date_idx >= 0:
                        prev_date = trade_dates[prev_date_idx]
                        current_prices, _ = self._validate_price_data(price_dict, prev_date, ts_code)
                        if current_prices:
                            logger.debug(f"股票 {ts_code} 在 {trade_date} 使用前一日 {prev_date} 的价格数据")
                        else:
                            # 如果前一日也没有数据，使用买入价格作为最后手段
                            current_prices = {'low': buy_price, 'close': buy_price, 'open': buy_price}
                            logger.warning(f"股票 {ts_code} 在 {trade_date} 和前一日都没有价格数据，使用买入价格")
                    else:
                        # 没有前一日数据，使用买入价格
                        current_prices = {'low': buy_price, 'close': buy_price, 'open': buy_price}
                        logger.warning(f"股票 {ts_code} 在 {trade_date} 没有价格数据，使用买入价格")
                
                if current_prices:
                    current_low = current_prices.get('low', np.nan)
                    current_close = current_prices.get('close', np.nan)
                    
                    # 检查止损：Low < Buy_Price * (1 - stop_loss_pct)
                    stop_loss_price = buy_price * (1 - stop_loss_pct)
                    stop_loss_triggered = current_low < stop_loss_price
                    
                    if stop_loss_triggered or holding_period_reached:
                            # 卖出
                            if stop_loss_triggered:
                                # 止损价：如果开盘价低于止损价，使用开盘价（更保守）
                                # 否则使用止损价
                                current_open = current_prices.get('open', np.nan)
                                if not np.isnan(current_open) and current_open < stop_loss_price:
                                    sell_price = current_open
                                else:
                                    sell_price = stop_loss_price
                                return_pct = (-stop_loss_pct - cost_rate) * 100
                                exit_reason = "Stop Loss"
                            else:
                                sell_price = current_close  # 正常退出
                                return_pct = ((sell_price - buy_price) / buy_price - cost_rate) * 100
                                exit_reason = "Holding Period"
                            
                            shares = pos_info['shares']
                            proceeds = sell_price * shares * (1 - cost_rate)  # 扣除卖出成本
                            cash += proceeds
                            
                            # 记录交易
                            gain = proceeds - (buy_price * shares * (1 + cost_rate))  # 扣除买入成本
                            trades.append({
                                'ts_code': ts_code,
                                'buy_date': buy_date,
                                'sell_date': trade_date,
                                'buy_price': buy_price,
                                'sell_price': sell_price,
                                'return': return_pct,
                                'exit_reason': exit_reason,
                                'gain': gain
                            })
                            
                            # 更新股票贡献
                            if ts_code not in stock_contributions:
                                stock_contributions[ts_code] = 0.0
                            stock_contributions[ts_code] += gain
                            
                            positions_to_remove.append(ts_code)
                
            # 移除已卖出的持仓
            for ts_code in positions_to_remove:
                del positions[ts_code]
            
            # 2. 买入逻辑：检查新信号（在T日看到信号，在T+1日买入）
            # **关键修复：BBI确认过滤 - 空头市场不买入（使用3日确认规则）**
            is_bear_market = False
            if bbi_signal_dict is not None:
                bbi_confirmed_signal = bbi_signal_dict.get(trade_date)
                if bbi_confirmed_signal is not None and bbi_confirmed_signal == -1:
                    is_bear_market = True
                    logger.debug(f"交易日 {trade_date}: 基准指数BBI确认信号为-1（未确认多头），跳过所有买入信号")
            
            if len(positions) < max_positions and cash > 0 and not is_bear_market:
                # 获取当日的买入信号
                day_signals = signal_df[
                    (signal_df['trade_date'] == trade_date) & 
                    (signal_df['buy_signal'] == 1)
                ].copy()
                
                # 排除已持有的股票
                day_signals = day_signals[~day_signals['ts_code'].isin(positions.keys())]
                
                # 按信号强度排序（可以使用RPS等指标）
                if 'rps_60' in day_signals.columns:
                    day_signals = day_signals.sort_values('rps_60', ascending=False)
                
                # 买入直到达到最大持仓数 - 优化：使用values替代iterrows
                for idx in day_signals.index:
                    if len(positions) >= max_positions:
                        break
                    
                    row = day_signals.loc[idx]
                    ts_code = row['ts_code']
                    
                    # 获取T+1的买入价格（使用下一个交易日的开盘价）
                    try:
                        current_idx = trade_dates.index(trade_date)
                        next_date_idx = current_idx + 1
                    except ValueError:
                        logger.warning(f"交易日 {trade_date} 不在trade_dates列表中，跳过买入")
                        continue
                    
                    if next_date_idx < len(trade_dates):
                        next_date = trade_dates[next_date_idx]
                        
                        # 验证T+1日价格数据可用性
                        next_prices, price_error = self._validate_price_data(price_dict, next_date, ts_code)
                        
                        if price_error:
                            logger.debug(f"股票 {ts_code} 在 {next_date} (T+1) 价格数据无效: {price_error}，跳过买入")
                            continue
                        
                        buy_price = next_prices.get('open', np.nan)
                        
                        if not np.isnan(buy_price) and buy_price > 0:
                                # 计算买入金额（使用初始资金的固定比例）
                                position_value = initial_capital * weight_per_pos
                                
                                # 检查现金是否足够
                                required_cash = position_value * (1 + cost_rate)
                                if cash >= required_cash:
                                    shares = int(position_value / (buy_price * (1 + cost_rate)))
                                    
                                    if shares > 0:
                                        cost = buy_price * shares * (1 + cost_rate)
                                        cash -= cost
                                        
                                        # 记录持仓（买入日期为T+1）
                                        positions[ts_code] = {
                                            'buy_date': next_date,
                                            'buy_price': buy_price,
                                            'shares': shares
                                        }
                                        logger.debug(f"买入 {ts_code}: {shares}股 @ {buy_price:.2f}, 买入日期: {next_date}")
                                    else:
                                        logger.debug(f"股票 {ts_code} 计算出的股数为0，跳过买入")
                                else:
                                    logger.debug(f"现金不足，无法买入 {ts_code}: 需要 {required_cash:.2f}, 可用 {cash:.2f}")
            
            # 3. 计算当日权益（Mark-to-Market）
            total_position_value = 0.0
            for ts_code, pos_info in positions.items():
                # 验证并获取当前价格（使用当日收盘价）
                current_prices, price_error = self._validate_price_data(price_dict, trade_date, ts_code)
                
                if price_error or not current_prices:
                    # 如果当日价格数据无效，尝试使用前一日价格
                    prev_date_idx = None
                    for i, date in enumerate(trade_dates):
                        if date == trade_date:
                            prev_date_idx = i - 1
                            break
                    
                    if prev_date_idx is not None and prev_date_idx >= 0:
                        prev_date = trade_dates[prev_date_idx]
                        current_prices, _ = self._validate_price_data(price_dict, prev_date, ts_code)
                        if current_prices:
                            logger.debug(f"股票 {ts_code} 在 {trade_date} 使用前一日 {prev_date} 的价格进行盯市")
                    
                    # 如果前一日也没有数据，使用买入价格作为最后手段
                    if not current_prices:
                        current_close = pos_info['buy_price']
                        logger.warning(f"股票 {ts_code} 在 {trade_date} 和前一日都没有价格数据，使用买入价格 {current_close:.2f} 进行盯市")
                    else:
                        current_close = current_prices.get('close', pos_info['buy_price'])
                else:
                    current_close = current_prices.get('close', pos_info['buy_price'])
                
                total_position_value += current_close * pos_info['shares']
            
            equity = cash + total_position_value
            equity_curve.append({
                'trade_date': trade_date,
                'equity': equity,
                'cash': cash,
                'positions_value': total_position_value,
                'num_positions': len(positions)
            })
        
        # 转换为DataFrame
        equity_df = pd.DataFrame(equity_curve)
        if not equity_df.empty:
            equity_curve_series = pd.Series(
                equity_df['equity'].values / initial_capital,
                index=equity_df['trade_date']
            )
        else:
            equity_curve_series = pd.Series(dtype=float)
        
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        return {
            'equity_curve': equity_curve_series,
            'trades': trades_df,
            'stock_contributions': stock_contributions
        }
    
    def run(
        self, 
        df: pd.DataFrame, 
        holding_days: int = 5,
        stop_loss_pct: float = 0.08,
        cost_rate: float = 0.002,
        benchmark_code: str = "000300.SH",
        initial_capital: float = 1000000.0,
        max_positions: int = 4,
        rps_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        运行回测 (v1.2.2 - Portfolio Position Sizing)
        
        Args:
            df: 包含历史数据的DataFrame，必须包含列：
                ts_code, trade_date, open, high, low, close, vol, pe_ttm
            holding_days: 持仓天数，默认5天
            stop_loss_pct: 止损百分比，默认0.08 (8%)
            cost_rate: 交易成本率，默认0.002 (0.2%)
            benchmark_code: 基准指数代码，默认沪深300
            initial_capital: 初始资金，默认100万
            max_positions: 最大持仓数，默认4
            rps_threshold: RPS阈值，默认使用配置值或85
            
        Returns:
            Dict包含回测结果：
            - total_return: 总收益率
            - max_drawdown: 最大回撤
            - win_rate: 胜率
            - equity_curve: 净值曲线 (Series)
            - strategy_metrics: 策略性能指标（完整）
            - benchmark_metrics: 基准性能指标
            - trades: 交易记录
            - top_contributors: Top 3 Contributors (DataFrame)
        """
        if df.empty:
            logger.warning("run: 输入DataFrame为空")
            return {
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'equity_curve': pd.Series(dtype=float),
                'strategy_metrics': {},
                'benchmark_metrics': {},
                'trades': pd.DataFrame(),
                'top_contributors': pd.DataFrame()
            }
        
        # 如果rps_threshold为None，使用默认值85
        if rps_threshold is None:
            rps_threshold = 85
        
        logger.info(
            f"开始回测 v1.2.2: {len(df)} 条数据，持仓天数: {holding_days}, "
            f"止损: {stop_loss_pct*100:.1f}%, 成本: {cost_rate*100:.2f}%, "
            f"最大持仓: {max_positions}, 初始资金: {initial_capital:.0f}, "
            f"RPS阈值: {rps_threshold}, 基准指数: {benchmark_code}"
        )
        
        # 数据完整性验证
        required_cols = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            error_msg = f"输入数据缺少必需的列: {missing_cols}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 检查数据质量
        nan_counts = df[required_cols].isna().sum()
        if nan_counts.any():
            logger.warning(f"输入数据包含NaN值: {nan_counts.to_dict()}")
        
        zero_price_count = ((df['close'] <= 0) | (df['open'] <= 0)).sum()
        if zero_price_count > 0:
            logger.warning(f"发现 {zero_price_count} 条价格数据<=0，将过滤这些记录")
            df = df[(df['close'] > 0) & (df['open'] > 0)].copy()
        
        if df.empty:
            logger.warning("数据验证后DataFrame为空")
            return {
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'equity_curve': pd.Series(dtype=float),
                'strategy_metrics': {},
                'benchmark_metrics': {},
                'trades': pd.DataFrame(),
                'top_contributors': pd.DataFrame()
            }
        
        # 0. 获取基准指数数据（一次获取，用于BBI信号和基准指标计算）
        logger.info(f"获取基准指数数据: {benchmark_code}")
        # 从df中提取日期范围
        if 'trade_date' in df.columns:
            if df['trade_date'].dtype == 'object':
                df_dates = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
            else:
                df_dates = df['trade_date']
            start_date_str = df_dates.min().strftime('%Y%m%d') if hasattr(df_dates.min(), 'strftime') else str(df_dates.min()).replace('-', '')
            end_date_str = df_dates.max().strftime('%Y%m%d') if hasattr(df_dates.max(), 'strftime') else str(df_dates.max()).replace('-', '')
        else:
            # Fallback: 使用默认日期范围
            start_date_str = "20200101"
            end_date_str = "20231231"
            logger.warning("无法从df中提取日期范围，使用默认值")
        
        # 一次获取基准数据
        benchmark_df = self._get_benchmark_data(start_date_str, end_date_str, benchmark_code)
        
        # 提取BBI信号（用于市场状态过滤）
        bbi_signal_dict = self._extract_bbi_signals(benchmark_df)
        
        # 1. 计算因子
        logger.info("计算因子...")
        try:
            enriched_df = self.factor_pipeline.run(df.copy())
            if enriched_df.empty:
                logger.warning("因子计算后DataFrame为空")
                raise ValueError("因子计算失败：结果为空")
            logger.info(f"因子计算完成: {len(enriched_df)} 条数据")
        except Exception as e:
            logger.error(f"因子计算失败: {e}")
            raise
        
        # 2. 生成买入信号
        logger.info("生成买入信号...")
        try:
            signal_df = self._generate_buy_signals(enriched_df, rps_threshold=rps_threshold)
            buy_signal_count = signal_df['buy_signal'].sum() if 'buy_signal' in signal_df.columns else 0
            logger.info(f"买入信号生成完成: {buy_signal_count} 个买入信号")
        except Exception as e:
            logger.error(f"买入信号生成失败: {e}")
            raise
        
        # 3. 运行组合模拟（逐日模拟）
        logger.info("运行组合模拟（逐日模拟，应用BBI过滤）...")
        try:
            portfolio_result = self._simulate_portfolio(
                signal_df,
                initial_capital=initial_capital,
                holding_days=holding_days,
                stop_loss_pct=stop_loss_pct,
                cost_rate=cost_rate,
                max_positions=max_positions,
                bbi_signal_dict=bbi_signal_dict
            )
            trade_count = len(portfolio_result.get('trades', pd.DataFrame()))
            logger.info(f"组合模拟完成: {trade_count} 笔交易")
        except Exception as e:
            logger.error(f"组合模拟失败: {e}")
            raise
        
        equity_curve = portfolio_result['equity_curve']
        trades_df = portfolio_result['trades']
        stock_contributions = portfolio_result['stock_contributions']
        
        # 4. 计算策略指标
        if not trades_df.empty:
            strategy_returns = trades_df['return']
            strategy_metrics = self._calculate_metrics(strategy_returns)
        else:
            strategy_metrics = {
                'win_rate': 0.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'avg_return': 0.0,
                'sharpe_ratio': 0.0,
                'total_trades': 0
            }
        
        # 5. 从净值曲线计算总收益率和最大回撤
        if not equity_curve.empty:
            total_return = (equity_curve.iloc[-1] - 1) * 100 if len(equity_curve) > 0 else 0.0
            running_max = equity_curve.expanding().max()
            drawdown = (equity_curve - running_max) / running_max * 100
            max_drawdown = abs(drawdown.min()) if not drawdown.empty else 0.0
        else:
            total_return = strategy_metrics.get('total_return', 0.0)
            max_drawdown = strategy_metrics.get('max_drawdown', 0.0)
        
        win_rate = strategy_metrics.get('win_rate', 0.0)
        
        # 6. 计算Top Contributors (返回所有，由lab_service选择winners和losers)
        if stock_contributions:
            contributors_list = [
                {'ts_code': code, 'total_gain': gain}
                for code, gain in stock_contributions.items()
            ]
            contributors_df = pd.DataFrame(contributors_list)
            # 计算百分比后再排序，但不限制数量，让lab_service来选择winners/losers
            contributors_df['total_gain_pct'] = (contributors_df['total_gain'] / initial_capital * 100).round(2)
            contributors_df = contributors_df.sort_values('total_gain', ascending=False)
        else:
            contributors_df = pd.DataFrame(columns=['ts_code', 'total_gain', 'total_gain_pct'])
        
        # 7. 计算基准指标（使用已获取的benchmark_df，避免重复获取）
        benchmark_metrics = self._calculate_benchmark_metrics(benchmark_df)
        
        # 8. 计算基准净值曲线（用于前端展示）
        benchmark_equity_curve = pd.Series(dtype=float)
        if not benchmark_df.empty and not equity_curve.empty:
            benchmark_equity_curve = self._calculate_benchmark_equity_curve(
                benchmark_df, 
                equity_curve.index
            )
        
        # 9. 汇总结果
        result = {
            'total_return': float(total_return),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'equity_curve': equity_curve,
            'benchmark_equity_curve': benchmark_equity_curve,
            'strategy_metrics': strategy_metrics,
            'benchmark_metrics': benchmark_metrics,
            'trades': trades_df,
            'top_contributors': contributors_df
        }
        
        logger.info(
            f"回测完成: 总交易数 {strategy_metrics.get('total_trades', 0)}, "
            f"胜率 {win_rate:.2f}%, "
            f"总收益率 {total_return:.2f}%, "
            f"最大回撤 {max_drawdown:.2f}%, "
            f"基准收益率 {benchmark_metrics.get('total_return', 0.0):.2f}%"
        )
        
        return result
