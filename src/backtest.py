"""
Vector Backtester - DAAS Alpha v1.2.2
Portfolio Position Sizing with Day-by-Day Simulation
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta

from .logging_config import get_logger
from .data_provider import DataProvider
from .factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor

logger = get_logger(__name__)


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
    
    def __init__(self, data_provider: Optional[DataProvider] = None):
        """
        Initialize Vector Backtester
        
        Args:
            data_provider: DataProvider instance (creates new one if None)
        """
        self.data_provider = data_provider or DataProvider()
        self.factor_pipeline = FactorPipeline()
        self.factor_pipeline.add(RPSFactor(window=60))
        self.factor_pipeline.add(MAFactor(window=20))
        self.factor_pipeline.add(VolumeRatioFactor(window=5))
        self.factor_pipeline.add(PEProxyFactor(max_pe=30))
        
        logger.info("VectorBacktester 初始化完成")
    
    def _generate_buy_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成买入信号（使用AlphaStrategy逻辑，向量化实现）
        
        Args:
            df: 包含因子列的DataFrame
            
        Returns:
            DataFrame with 'buy_signal' column (1 = buy, 0 = no buy)
        """
        df = df.copy()
        
        # 检查必需的因子列
        required_cols = ['rps_60', 'is_undervalued', 'vol_ratio_5', 'above_ma_20']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"缺少必需的因子列: {missing_cols}")
        
        # Alpha Trident筛选条件（向量化）
        # 1. rps_60 > 85 (Momentum)
        # 2. is_undervalued == 1 (Value)
        # 3. vol_ratio_5 > 1.5 (Liquidity)
        # 4. above_ma_20 == 1 (Trend)
        
        df['buy_signal'] = (
            (df['rps_60'] > 85) &
            (df['is_undervalued'] == 1) &
            (df['vol_ratio_5'] > 1.5) &
            (df['above_ma_20'] == 1)
        ).astype(int)
        
        logger.debug(f"生成买入信号: {df['buy_signal'].sum()} 个信号")
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
        获取基准指数数据（CSI300）
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            index_code: 指数代码，默认沪深300
            
        Returns:
            DataFrame with trade_date and close (指数收盘价)
        """
        try:
            # 获取指数日线数据
            index_df = self.data_provider._pro.index_daily(
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
            
            return index_df
        except Exception as e:
            logger.error(f"获取基准数据失败: {e}")
            return pd.DataFrame()
    
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
    
    def _simulate_portfolio(
        self,
        signal_df: pd.DataFrame,
        initial_capital: float = 1000000.0,
        holding_days: int = 5,
        stop_loss_pct: float = 0.08,
        cost_rate: float = 0.002,
        max_positions: int = 4
    ) -> Dict:
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
        positions = {}  # {ts_code: {'buy_date': date, 'buy_price': price, 'shares': shares, 'holding_days': 0}}
        equity_curve = []
        trades = []
        stock_contributions = {}  # {ts_code: total_gain}
        
        weight_per_pos = 1.0 / max_positions
        
        # 创建价格查找字典（按日期和股票代码）
        price_dict = {}
        for _, row in signal_df.iterrows():
            date = row['trade_date']
            code = row['ts_code']
            if date not in price_dict:
                price_dict[date] = {}
            price_dict[date][code] = {
                'open': row.get('open', np.nan),
                'close': row.get('close', np.nan),
                'low': row.get('low', np.nan),
                'high': row.get('high', np.nan)
            }
        
        # 逐日模拟
        for trade_date in trade_dates:
            # 1. 卖出逻辑：检查现有持仓
            positions_to_remove = []
            for ts_code, pos_info in positions.items():
                holding_days_count = pos_info['holding_days']
                buy_price = pos_info['buy_price']
                buy_date = pos_info['buy_date']
                
                # 只在买入日之后才检查卖出条件（避免买入当天就卖出）
                if trade_date <= buy_date:
                    continue
                
                # 获取当日价格
                if trade_date in price_dict and ts_code in price_dict[trade_date]:
                    current_prices = price_dict[trade_date][ts_code]
                    current_low = current_prices.get('low', np.nan)
                    current_close = current_prices.get('close', np.nan)
                    
                    if not (np.isnan(current_low) or np.isnan(current_close)):
                        # 检查止损：Low < Buy_Price * (1 - stop_loss_pct)
                        stop_loss_price = buy_price * (1 - stop_loss_pct)
                        stop_loss_triggered = current_low < stop_loss_price
                        
                        # 检查持仓天数（持仓天数从买入日之后开始计算）
                        holding_period_reached = holding_days_count >= holding_days
                        
                        if stop_loss_triggered or holding_period_reached:
                            # 卖出
                            if stop_loss_triggered:
                                sell_price = stop_loss_price  # 止损价
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
                        else:
                            # 更新持仓天数（只在买入日之后递增）
                            if trade_date > buy_date:
                                positions[ts_code]['holding_days'] += 1
                
            # 移除已卖出的持仓
            for ts_code in positions_to_remove:
                del positions[ts_code]
            
            # 2. 买入逻辑：检查新信号（在T日看到信号，在T+1日买入）
            if len(positions) < max_positions and cash > 0:
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
                
                # 买入直到达到最大持仓数
                for _, row in day_signals.iterrows():
                    if len(positions) >= max_positions:
                        break
                    
                    ts_code = row['ts_code']
                    
                    # 获取T+1的买入价格（使用下一个交易日的开盘价）
                    next_date_idx = trade_dates.index(trade_date) + 1
                    if next_date_idx < len(trade_dates):
                        next_date = trade_dates[next_date_idx]
                        if next_date in price_dict and ts_code in price_dict[next_date]:
                            buy_price = price_dict[next_date][ts_code].get('open', np.nan)
                            
                            if not np.isnan(buy_price) and buy_price > 0:
                                # 计算买入金额（使用初始资金的固定比例）
                                position_value = initial_capital * weight_per_pos
                                
                                # 检查现金是否足够
                                if cash >= position_value * (1 + cost_rate):
                                    shares = int(position_value / (buy_price * (1 + cost_rate)))
                                    
                                    if shares > 0:
                                        cost = buy_price * shares * (1 + cost_rate)
                                        cash -= cost
                                        
                                        # 记录持仓（买入日期为T+1，持仓天数从0开始）
                                        # 注意：持仓天数会在买入日之后的下一个交易日才开始递增
                                        positions[ts_code] = {
                                            'buy_date': next_date,
                                            'buy_price': buy_price,
                                            'shares': shares,
                                            'holding_days': 0
                                        }
            
            # 3. 计算当日权益（Mark-to-Market）
            total_position_value = 0.0
            for ts_code, pos_info in positions.items():
                # 获取当前价格（使用当日收盘价）
                if trade_date in price_dict and ts_code in price_dict[trade_date]:
                    current_close = price_dict[trade_date][ts_code].get('close', np.nan)
                    if not np.isnan(current_close):
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
        max_positions: int = 4
    ) -> Dict:
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
        
        logger.info(f"开始回测 v1.2.2: {len(df)} 条数据，持仓天数: {holding_days}, "
                   f"止损: {stop_loss_pct*100:.1f}%, 成本: {cost_rate*100:.2f}%, "
                   f"最大持仓: {max_positions}, 初始资金: {initial_capital:.0f}")
        
        # 1. 计算因子
        logger.info("计算因子...")
        enriched_df = self.factor_pipeline.run(df.copy())
        
        # 2. 生成买入信号
        logger.info("生成买入信号...")
        signal_df = self._generate_buy_signals(enriched_df)
        
        # 3. 运行组合模拟（逐日模拟）
        logger.info("运行组合模拟（逐日模拟）...")
        portfolio_result = self._simulate_portfolio(
            signal_df,
            initial_capital=initial_capital,
            holding_days=holding_days,
            stop_loss_pct=stop_loss_pct,
            cost_rate=cost_rate,
            max_positions=max_positions
        )
        
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
        
        # 6. 计算Top 3 Contributors
        if stock_contributions:
            contributors_list = [
                {'ts_code': code, 'total_gain': gain}
                for code, gain in stock_contributions.items()
            ]
            contributors_df = pd.DataFrame(contributors_list)
            contributors_df = contributors_df.sort_values('total_gain', ascending=False).head(3)
            contributors_df['total_gain_pct'] = (contributors_df['total_gain'] / initial_capital * 100).round(2)
        else:
            contributors_df = pd.DataFrame(columns=['ts_code', 'total_gain', 'total_gain_pct'])
        
        # 7. 获取基准数据并计算基准指标
        if 'trade_date' in df.columns:
            # 获取日期范围
            if df['trade_date'].dtype == 'object':
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce')
            
            start_date = df['trade_date'].min().strftime('%Y%m%d')
            end_date = df['trade_date'].max().strftime('%Y%m%d')
            
            logger.info(f"获取基准数据: {benchmark_code} ({start_date} 到 {end_date})")
            benchmark_df = self._get_benchmark_data(start_date, end_date, benchmark_code)
            
            if not benchmark_df.empty:
                # 计算基准累计收益率
                benchmark_cumulative = (1 + benchmark_df['benchmark_return'] / 100).cumprod()
                benchmark_total_return = (benchmark_cumulative.iloc[-1] - 1) * 100 if len(benchmark_cumulative) > 0 else 0.0
                
                # 计算基准最大回撤
                benchmark_running_max = benchmark_cumulative.expanding().max()
                benchmark_drawdown = (benchmark_cumulative - benchmark_running_max) / benchmark_running_max * 100
                benchmark_max_drawdown = abs(benchmark_drawdown.min()) if not benchmark_drawdown.empty else 0.0
                
                benchmark_metrics = {
                    'total_return': float(benchmark_total_return),
                    'max_drawdown': float(benchmark_max_drawdown),
                    'avg_return': float(benchmark_df['benchmark_return'].mean()),
                }
            else:
                benchmark_metrics = {
                    'total_return': 0.0,
                    'max_drawdown': 0.0,
                    'avg_return': 0.0,
                }
        else:
            benchmark_metrics = {
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'avg_return': 0.0,
            }
        
        # 8. 汇总结果
        result = {
            'total_return': float(total_return),
            'max_drawdown': float(max_drawdown),
            'win_rate': float(win_rate),
            'equity_curve': equity_curve,
            'strategy_metrics': strategy_metrics,
            'benchmark_metrics': benchmark_metrics,
            'trades': trades_df,
            'top_contributors': contributors_df
        }
        
        logger.info(f"回测完成: 总交易数 {strategy_metrics.get('total_trades', 0)}, "
                   f"胜率 {win_rate:.2f}%, "
                   f"总收益率 {total_return:.2f}%, "
                   f"最大回撤 {max_drawdown:.2f}%")
        
        return result
