"""
Mock Data Generator for UI Prototype
生成模拟数据用于UI布局和样式确认
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def generate_market_regime():
    """生成市场状态模拟数据"""
    regimes = ["多头 (进攻)", "空头 (防守)"]
    return np.random.choice(regimes)


def generate_sentiment():
    """生成赚钱效应百分比"""
    return round(np.random.uniform(30, 70), 1)


def generate_target_position(regime):
    """根据市场状态生成建议仓位"""
    if "多头" in regime:
        return 100
    else:
        return 25


def generate_portfolio_nav():
    """生成模拟组合净值"""
    base_nav = 1000000
    variation = np.random.uniform(-0.1, 0.25)  # -10% to +25%
    return round(base_nav * (1 + variation), 2)


def generate_index_and_bbi_data(days=60):
    """生成指数和BBI数据（60天）"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 生成模拟指数价格（从3000开始，有趋势和波动）
    base_price = 3000
    trend = np.linspace(0, 200, days)  # 上升趋势
    noise = np.random.normal(0, 50, days)
    prices = base_price + trend + noise
    
    # 计算BBI（3, 6, 12, 24日均线的平均值）
    df = pd.DataFrame({
        'trade_date': dates,
        'close': prices
    })
    
    ma3 = df['close'].rolling(window=3, min_periods=1).mean()
    ma6 = df['close'].rolling(window=6, min_periods=1).mean()
    ma12 = df['close'].rolling(window=12, min_periods=1).mean()
    ma24 = df['close'].rolling(window=24, min_periods=1).mean()
    
    bbi = (ma3 + ma6 + ma12 + ma24) / 4
    
    return pd.DataFrame({
        'trade_date': dates,
        'close': prices,
        'bbi': bbi
    })


def generate_stock_results(count=12):
    """生成股票筛选结果"""
    stock_names = [
        "平安银行", "万科A", "国农科技", "国药一致", "深振业A",
        "中国平安", "招商银行", "贵州茅台", "五粮液", "宁德时代",
        "比亚迪", "隆基绿能", "药明康德", "恒瑞医药", "海康威视"
    ]
    
    results = []
    for i in range(count):
        name = stock_names[i % len(stock_names)]
        code = f"{600000 + i}.SH" if i % 2 == 0 else f"{1 + i:06d}.SZ"
        
        results.append({
            'ts_code': code,
            'name': name,
            'close': round(np.random.uniform(10, 200), 2),
            'rps_60': round(np.random.uniform(80, 100), 1),
            'vol_ratio_5': round(np.random.uniform(1.0, 5.0), 2),
            'pe_ttm': round(np.random.uniform(10, 40), 2),
            'ai_analysis': generate_ai_analysis()
        })
    
    return pd.DataFrame(results)


def generate_ai_analysis():
    """生成AI分析文本"""
    analyses = [
        "公司基本面稳健，近期业绩超预期，技术面突破关键阻力位，建议关注。",
        "行业景气度提升，公司估值合理，资金流入明显，短期有望继续上涨。",
        "技术指标显示强势，成交量放大，主力资金介入明显，建议逢低布局。",
        "公司业绩增长确定性高，估值处于合理区间，长期投资价值凸显。",
        "短期调整到位，技术面修复完成，有望开启新一轮上涨行情。"
    ]
    return np.random.choice(analyses)


def generate_portfolio_positions(count=4):
    """生成模拟组合持仓"""
    stock_names = ["平安银行", "万科A", "中国平安", "招商银行", "贵州茅台"]
    
    positions = []
    for i in range(count):
        name = stock_names[i % len(stock_names)]
        code = f"{600000 + i}.SH"
        cost = round(np.random.uniform(20, 100), 2)
        current_price = cost * (1 + np.random.uniform(-0.15, 0.20))
        shares = np.random.randint(100, 1000)
        stop_loss = cost * 0.92  # 8%止损
        
        positions.append({
            'ts_code': code,
            'name': name,
            'cost': cost,
            'current_price': round(current_price, 2),
            'shares': shares,
            'stop_loss': round(stop_loss, 2)
        })
    
    return positions


def generate_portfolio_metrics():
    """生成组合指标"""
    return {
        'total_return': round(np.random.uniform(-5, 25), 2),
        'max_drawdown': round(np.random.uniform(5, 20), 2),
        'sharpe_ratio': round(np.random.uniform(0.5, 2.5), 2)
    }


def generate_backtest_equity_curve(days=120):
    """生成回测权益曲线"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # 策略净值曲线（从1.0开始）
    strategy_returns = np.random.normal(0.001, 0.02, days)  # 日均收益
    strategy_curve = np.cumprod(1 + strategy_returns)
    
    # 基准净值曲线（CSI300，略低于策略）
    benchmark_returns = np.random.normal(0.0005, 0.015, days)
    benchmark_curve = np.cumprod(1 + benchmark_returns)
    
    return pd.DataFrame({
        'trade_date': dates,
        'strategy': strategy_curve,
        'benchmark': benchmark_curve
    })


def generate_backtest_attribution():
    """生成回测归因数据（Top Winners/Losers）"""
    stock_names = [
        "平安银行", "万科A", "国农科技", "国药一致", "深振业A",
        "中国平安", "招商银行", "贵州茅台", "五粮液", "宁德时代"
    ]
    
    # Top 3 Winners
    winners = []
    for i in range(3):
        name = stock_names[i]
        code = f"{600000 + i}.SH"
        total_gain = round(np.random.uniform(50000, 150000), 2)
        total_gain_pct = round(np.random.uniform(15, 40), 2)
        winners.append({
            'ts_code': code,
            'name': name,
            'total_gain': total_gain,
            'total_gain_pct': total_gain_pct
        })
    
    # Top 3 Losers
    losers = []
    for i in range(3, 6):
        name = stock_names[i]
        code = f"{600000 + i}.SH"
        total_gain = round(np.random.uniform(-80000, -20000), 2)
        total_gain_pct = round(np.random.uniform(-25, -8), 2)
        losers.append({
            'ts_code': code,
            'name': name,
            'total_gain': total_gain,
            'total_gain_pct': total_gain_pct
        })
    
    return {
        'winners': pd.DataFrame(winners),
        'losers': pd.DataFrame(losers)
    }
