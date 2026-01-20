"""
Dashboard Page - 驾驶舱
The Morning Briefing: Instant market status check
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from page_modules.mock_data import (
    generate_market_regime,
    generate_sentiment,
    generate_target_position,
    generate_portfolio_nav,
    generate_index_and_bbi_data
)


def render_dashboard_page():
    """渲染Dashboard页面"""
    st.header("驾驶舱 (Dashboard)")
    st.markdown("市场概览与策略状态")
    
    # 生成模拟数据
    regime = generate_market_regime()
    sentiment = generate_sentiment()
    target_position = generate_target_position(regime)
    nav = generate_portfolio_nav()
    index_data = generate_index_and_bbi_data(60)
    
    # KPI Cards (Top Row)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("### 市场状态")
        regime_color = "#EF4444" if "多头" in regime else "#10A37F"
        st.markdown(
            f'<div style="font-size: 1.5rem; color: {regime_color}; font-weight: 600;">{regime}</div>',
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown("### 赚钱效应")
        st.markdown(
            f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{sentiment}%</div>',
            unsafe_allow_html=True
        )
        st.progress(sentiment / 100)
    
    with col3:
        st.markdown("### 建议仓位")
        st.markdown(
            f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{target_position}%</div>',
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown("### 组合净值")
        nav_formatted = f"{nav:,.0f}"
        st.markdown(
            f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{nav_formatted}</div>',
            unsafe_allow_html=True
        )
    
    st.markdown("---")
    
    # Main Chart: BBI Trend
    st.markdown("### BBI趋势图")
    
    # 创建图表
    fig = go.Figure()
    
    # 指数收盘价线
    fig.add_trace(go.Scatter(
        x=index_data['trade_date'],
        y=index_data['close'],
        mode='lines',
        name='指数收盘',
        line=dict(color='#000000', width=2)
    ))
    
    # BBI线
    fig.add_trace(go.Scatter(
        x=index_data['trade_date'],
        y=index_data['bbi'],
        mode='lines',
        name='BBI',
        line=dict(color='#666666', width=2, dash='dash')
    ))
    
    # 填充区域（价格 > BBI 用红色，价格 < BBI 用绿色）
    for i in range(len(index_data) - 1):
        price = index_data.iloc[i]['close']
        bbi = index_data.iloc[i]['bbi']
        next_price = index_data.iloc[i + 1]['close']
        next_bbi = index_data.iloc[i + 1]['bbi']
        
        if price > bbi:
            fill_color = 'rgba(239, 68, 68, 0.2)'  # Red with transparency
        else:
            fill_color = 'rgba(16, 163, 127, 0.2)'  # Green with transparency
        
        fig.add_trace(go.Scatter(
            x=[index_data.iloc[i]['trade_date'], index_data.iloc[i + 1]['trade_date']],
            y=[price, next_price],
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            fill='tonexty' if i > 0 else None,
            fillcolor=fill_color,
            hoverinfo='skip'
        ))
    
    # 更新布局
    fig.update_layout(
        template="plotly_white",
        height=500,
        xaxis=dict(
            showgrid=False,
            title="日期"
        ),
        yaxis=dict(
            showgrid=False,
            title="价格"
        ),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=0, r=0, t=0, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
