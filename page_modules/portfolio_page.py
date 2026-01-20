"""
Portfolio Page - 模拟盘
The Wallet: Position management
"""

import pandas as pd
import streamlit as st
from page_modules.mock_data import generate_portfolio_positions, generate_portfolio_metrics


def calculate_pnl_percentage(cost, current_price):
    """计算盈亏百分比"""
    if cost == 0:
        return 0.0
    return ((current_price - cost) / cost) * 100


def calculate_stop_loss_distance(current_price, stop_loss_price):
    """计算距离止损的百分比"""
    if current_price == 0:
        return 0.0
    return ((current_price - stop_loss_price) / current_price) * 100


def render_portfolio_page():
    """渲染Portfolio页面"""
    st.header("模拟盘 (Portfolio)")
    st.markdown("组合持仓与风险管理")
    
    # 初始化组合数据
    if "portfolio_positions" not in st.session_state or len(st.session_state.portfolio_positions) == 0:
        st.session_state.portfolio_positions = generate_portfolio_positions(4)
    
    if "portfolio_metrics" not in st.session_state:
        st.session_state.portfolio_metrics = generate_portfolio_metrics()
    
    positions = st.session_state.portfolio_positions
    metrics = st.session_state.portfolio_metrics
    
    # 头部指标
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_return = metrics['total_return']
        return_color = "#EF4444" if total_return > 0 else "#10A37F"
        st.markdown("### 总收益率")
        st.markdown(
            f'<div style="font-size: 1.5rem; color: {return_color}; font-weight: 600;">{total_return:.2f}%</div>',
            unsafe_allow_html=True
        )
    
    with col2:
        max_drawdown = metrics['max_drawdown']
        st.markdown("### 最大回撤")
        st.markdown(
            f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{max_drawdown:.2f}%</div>',
            unsafe_allow_html=True
        )
    
    with col3:
        sharpe_ratio = metrics['sharpe_ratio']
        st.markdown("### 夏普比率")
        st.markdown(
            f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{sharpe_ratio:.2f}</div>',
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # 持仓列表
    st.subheader("持仓列表")
    
    if not positions:
        st.info("当前无持仓")
        return
    
    # 准备表格数据
    holdings_data = []
    for pos in positions:
        pnl_pct = calculate_pnl_percentage(pos['cost'], pos['current_price'])
        stop_loss_dist = calculate_stop_loss_distance(pos['current_price'], pos['stop_loss'])
        market_value = pos['current_price'] * pos['shares']
        
        holdings_data.append({
            '名称': pos['name'],
            '成本': pos['cost'],
            '现价': pos['current_price'],
            '盈亏%': round(pnl_pct, 2),
            '距离止损%': round(stop_loss_dist, 2),
            '市值': round(market_value, 2)
        })
    
    holdings_df = pd.DataFrame(holdings_data)
    
    # 应用颜色逻辑
    def style_holdings(row):
        styles = [''] * len(row)
        
        # P&L 颜色
        if row['盈亏%'] > 0:
            styles[3] = 'color: #EF4444; font-weight: bold'  # Red for profit
        elif row['盈亏%'] < 0:
            styles[3] = 'color: #10A37F; font-weight: bold'  # Green for loss
        
        # 止损警告背景
        if row['距离止损%'] < 2:
            return ['background-color: #FEF3C7' if i < len(styles) else '' for i in range(len(styles))]  # Yellow background
        
        return styles
    
    styled_df = holdings_df.style.apply(style_holdings, axis=1)
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )
    
    # 操作按钮
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("刷新价格", use_container_width=True):
            st.info("功能开发中：更新持仓股票的最新价格")
    
    with col2:
        if st.button("清空组合", use_container_width=True):
            st.session_state.portfolio_positions = []
            st.rerun()
