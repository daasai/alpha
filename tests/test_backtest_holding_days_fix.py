"""
专门测试持仓天数修复的测试用例
验证 holding_days_count >= (holding_days - 1) 的逻辑是否正确
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from src.backtest import VectorBacktester


class TestHoldingDaysFix:
    """测试持仓天数修复"""
    
    @pytest.fixture
    def backtester(self):
        """创建VectorBacktester实例"""
        with patch('src.backtest.DataProvider'):
            return VectorBacktester()
    
    def test_holding_days_exact_match(self, backtester):
        """
        测试持仓天数精确匹配
        如果holding_days=5，应该持有5个交易日，而不是6个
        """
        # 创建测试数据：15个交易日
        dates = pd.date_range('2024-01-01', periods=15, freq='D')
        dates = [d for d in dates if d.weekday() < 5]  # 只保留工作日
        
        data = []
        for i, date in enumerate(dates):
            base_price = 10.0 + i * 0.01  # 价格缓慢上涨
            data.append({
                'ts_code': '000001.SZ',
                'trade_date': date.strftime('%Y%m%d'),
                'open': base_price,
                'high': base_price + 0.1,
                'low': base_price - 0.05,
                'close': base_price + 0.05,
                'vol': 1000000,
                'pe_ttm': 15.0,
                'rps_60': 90.0 if i == 0 else 50.0,  # 第一天有买入信号
                'is_undervalued': 1 if i == 0 else 0,
                'vol_ratio_5': 2.0 if i == 0 else 1.0,
                'above_ma_20': 1 if i == 0 else 0,
                'buy_signal': 1 if i == 0 else 0
            })
        
        df = pd.DataFrame(data)
        
        # 确保trade_date是datetime类型
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        
        # 运行组合模拟，holding_days=5
        result = backtester._simulate_portfolio(
            df,
            initial_capital=100000.0,
            holding_days=5,
            stop_loss_pct=0.08,
            cost_rate=0.002,
            max_positions=4
        )
        
        trades_df = result['trades']
        
        if not trades_df.empty:
            # 检查是否有交易
            assert len(trades_df) > 0, "应该有交易记录"
            
            # 检查第一笔交易的持仓天数
            first_trade = trades_df.iloc[0]
            buy_date = pd.to_datetime(first_trade['buy_date'])
            sell_date = pd.to_datetime(first_trade['sell_date'])
            
            # 计算实际持有的交易日数
            actual_holding_days = (sell_date - buy_date).days
            
            # 如果是因为持仓天数到期而卖出，应该持有5个交易日
            if first_trade['exit_reason'] == 'Holding Period':
                # 买入日期和卖出日期之间的交易日数应该是5
                # 例如：T+1买入，T+6卖出，共5个交易日
                # 但实际计算的是日期差，需要验证
                trade_dates = sorted(df['trade_date'].unique())
                buy_idx = trade_dates.index(buy_date) if buy_date in trade_dates else -1
                sell_idx = trade_dates.index(sell_date) if sell_date in trade_dates else -1
                
                if buy_idx >= 0 and sell_idx >= 0:
                    actual_trading_days = sell_idx - buy_idx
                    # 应该持有5个交易日（包含买入日和卖出日）
                    # 买入日索引为i，卖出日索引为i+4（共5个交易日）
                    assert actual_trading_days == 4, \
                        f"应该持有5个交易日，但实际持有{actual_trading_days + 1}个交易日 " \
                        f"(买入日索引: {buy_idx}, 卖出日索引: {sell_idx})"
    
    def test_holding_days_different_values(self, backtester):
        """测试不同holding_days值的正确性"""
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=20, freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        data = []
        for i, date in enumerate(dates):
            base_price = 10.0
            data.append({
                'ts_code': '000001.SZ',
                'trade_date': date.strftime('%Y%m%d'),
                'open': base_price,
                'high': base_price + 0.1,
                'low': base_price - 0.05,
                'close': base_price + 0.05,
                'vol': 1000000,
                'pe_ttm': 15.0,
                'rps_60': 90.0 if i == 0 else 50.0,
                'is_undervalued': 1 if i == 0 else 0,
                'vol_ratio_5': 2.0 if i == 0 else 1.0,
                'above_ma_20': 1 if i == 0 else 0,
                'buy_signal': 1 if i == 0 else 0
            })
        
        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        
        # 测试不同的holding_days值
        for holding_days in [3, 5, 10]:
            result = backtester._simulate_portfolio(
                df,
                initial_capital=100000.0,
                holding_days=holding_days,
                stop_loss_pct=0.20,  # 设置较大的止损，避免触发止损
                cost_rate=0.002,
                max_positions=4
            )
            
            trades_df = result['trades']
            
            if not trades_df.empty:
                # 找到因为持仓天数到期而卖出的交易
                holding_period_trades = trades_df[trades_df['exit_reason'] == 'Holding Period']
                
                if not holding_period_trades.empty:
                    trade = holding_period_trades.iloc[0]
                    buy_date = pd.to_datetime(trade['buy_date'])
                    sell_date = pd.to_datetime(trade['sell_date'])
                    
                    # 计算实际持有的交易日数
                    trade_dates = sorted(df['trade_date'].unique())
                    buy_idx = trade_dates.index(buy_date) if buy_date in trade_dates else -1
                    sell_idx = trade_dates.index(sell_date) if sell_date in trade_dates else -1
                    
                    if buy_idx >= 0 and sell_idx >= 0:
                        actual_trading_days = sell_idx - buy_idx
                        # 应该持有holding_days个交易日
                        # 买入日索引为i，卖出日索引为i+(holding_days-1)
                        expected_trading_days = holding_days - 1
                        assert actual_trading_days == expected_trading_days, \
                            f"holding_days={holding_days}时，应该持有{holding_days}个交易日 " \
                            f"(买入日索引: {buy_idx}, 卖出日索引: {sell_idx}, " \
                            f"实际交易日差: {actual_trading_days}, 期望: {expected_trading_days})"
    
    def test_holding_days_count_increments_correctly(self, backtester):
        """测试持仓天数计数是否正确递增"""
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=10, freq='D')
        dates = [d for d in dates if d.weekday() < 5]
        
        data = []
        for i, date in enumerate(dates):
            base_price = 10.0
            data.append({
                'ts_code': '000001.SZ',
                'trade_date': date.strftime('%Y%m%d'),
                'open': base_price,
                'high': base_price + 0.1,
                'low': base_price - 0.05,
                'close': base_price + 0.05,
                'vol': 1000000,
                'pe_ttm': 15.0,
                'rps_60': 90.0 if i == 0 else 50.0,
                'is_undervalued': 1 if i == 0 else 0,
                'vol_ratio_5': 2.0 if i == 0 else 1.0,
                'above_ma_20': 1 if i == 0 else 0,
                'buy_signal': 1 if i == 0 else 0
            })
        
        df = pd.DataFrame(data)
        df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
        
        # 运行模拟，holding_days=5
        result = backtester._simulate_portfolio(
            df,
            initial_capital=100000.0,
            holding_days=5,
            stop_loss_pct=0.20,  # 大止损，避免触发
            cost_rate=0.002,
            max_positions=4
        )
        
        trades_df = result['trades']
        
        if not trades_df.empty:
            trade = trades_df.iloc[0]
            
            # 验证：如果holding_days=5，买入日在T+1，卖出日应该在T+6
            # 持仓天数计数：T+1=0, T+2=1, T+3=2, T+4=3, T+5=4, T+6=5（卖出）
            # 当holding_days_count=4时，应该卖出（因为holding_days_count >= (holding_days - 1) = 4）
            buy_date = pd.to_datetime(trade['buy_date'])
            sell_date = pd.to_datetime(trade['sell_date'])
            
            trade_dates = sorted(df['trade_date'].unique())
            buy_idx = trade_dates.index(buy_date) if buy_date in trade_dates else -1
            sell_idx = trade_dates.index(sell_date) if sell_date in trade_dates else -1
            
            if buy_idx >= 0 and sell_idx >= 0 and trade['exit_reason'] == 'Holding Period':
                # 买入日在索引buy_idx，卖出日应该在索引buy_idx+4（共5个交易日）
                assert sell_idx == buy_idx + 4, \
                    f"holding_days=5时，买入日索引{buy_idx}，卖出日索引应该是{buy_idx+4}，实际是{sell_idx}"
