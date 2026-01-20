"""
Lab Page - 实验室
Strategy Wind Tunnel: Backtesting & Calibration
"""

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from page_modules.mock_data import generate_backtest_equity_curve, generate_backtest_attribution


def render_lab_page():
    """渲染Lab页面"""
    st.header("实验室 (Lab)")
    st.markdown("策略回测与验证")
    
    # 侧边栏控制面板
    with st.sidebar:
        st.subheader("回测参数")
        
        # 日期范围
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=datetime.now() - timedelta(days=365),
                min_value=datetime(2020, 1, 1),
                max_value=datetime.now()
            )
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=datetime.now(),
                min_value=datetime(2020, 1, 1),
                max_value=datetime.now()
            )
        
        st.markdown("---")
        
        # 策略参数
        st.markdown("#### 策略参数")
        rps_threshold = st.slider(
            "RPS 阈值",
            min_value=80,
            max_value=100,
            value=85,
            step=1
        )
        
        stop_loss_pct = st.slider(
            "止损比例 (%)",
            min_value=0,
            max_value=20,
            value=8,
            step=1
        )
        
        max_positions = st.slider(
            "最大持仓数",
            min_value=1,
            max_value=10,
            value=4,
            step=1
        )
        
        cost_rate = st.number_input(
            "交易成本率",
            min_value=0.0,
            max_value=0.01,
            value=0.002,
            step=0.0001,
            format="%.4f"
        )
        
        st.markdown("---")
        
        # 运行按钮
        if st.button("运行回测", type="primary", use_container_width=True):
            st.session_state.lab_backtest_run = True
            st.rerun()
    
    # 主区域
    if st.session_state.get("lab_backtest_run", False):
        # 生成模拟回测数据
        equity_curve = generate_backtest_equity_curve(120)
        attribution = generate_backtest_attribution()
        
        # 计算指标（模拟）
        total_return = round((equity_curve['strategy'].iloc[-1] - 1) * 100, 2)
        benchmark_return = round((equity_curve['benchmark'].iloc[-1] - 1) * 100, 2)
        max_drawdown = round(abs(equity_curve['strategy'].min() - 1) * 100, 2)
        win_rate = round(np.random.uniform(50, 70), 2)
        
        # 显示指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            diff = total_return - benchmark_return
            diff_color = "#EF4444" if diff > 0 else "#10A37F"
            st.markdown("### 总收益率")
            st.markdown(
                f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{total_return:.2f}%</div>',
                unsafe_allow_html=True
            )
            st.caption(f"vs 基准: {diff:+.2f}%")
        
        with col2:
            st.markdown("### 最大回撤")
            st.markdown(
                f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{max_drawdown:.2f}%</div>',
                unsafe_allow_html=True
            )
        
        with col3:
            st.markdown("### 胜率")
            st.markdown(
                f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{win_rate:.2f}%</div>',
                unsafe_allow_html=True
            )
        
        with col4:
            st.markdown("### 最大持仓数")
            st.markdown(
                f'<div style="font-size: 1.5rem; color: #000000; font-weight: 600;">{max_positions}</div>',
                unsafe_allow_html=True
            )
        
        st.markdown("---")
        
        # 权益曲线图
        st.subheader("策略 vs 基准权益曲线")
        
        fig = go.Figure()
        
        # 策略净值
        fig.add_trace(go.Scatter(
            x=equity_curve['trade_date'],
            y=equity_curve['strategy'],
            mode="lines",
            name="策略净值",
            line=dict(color="#000000", width=2)
        ))
        
        # 基准净值
        fig.add_trace(go.Scatter(
            x=equity_curve['trade_date'],
            y=equity_curve['benchmark'],
            mode="lines",
            name="基准净值",
            line=dict(color="#666666", width=2, dash="dash")
        ))
        
        fig.update_layout(
            template="plotly_white",
            height=500,
            xaxis=dict(
                showgrid=False,
                title="日期"
            ),
            yaxis=dict(
                showgrid=False,
                title="净值"
            ),
            hovermode="x unified",
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
        
        # 归因分析
        st.markdown("---")
        st.subheader("归因分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Top 3 Winners")
            winners_df = attribution['winners']
            display_winners = pd.DataFrame()
            display_winners["股票代码"] = winners_df["ts_code"]
            display_winners["股票名称"] = winners_df["name"]
            display_winners["总收益 (元)"] = winners_df["total_gain"]
            display_winners["总收益 (%)"] = winners_df["total_gain_pct"]
            
            # 应用颜色（盈利用红色）
            def style_winners(row):
                return ['', '', 'color: #EF4444; font-weight: bold', 'color: #EF4444; font-weight: bold']
            
            styled_winners = display_winners.style.apply(style_winners, axis=1)
            st.dataframe(
                styled_winners,
                use_container_width=True,
                hide_index=True
            )
        
        with col2:
            st.markdown("#### Top 3 Losers")
            losers_df = attribution['losers']
            display_losers = pd.DataFrame()
            display_losers["股票代码"] = losers_df["ts_code"]
            display_losers["股票名称"] = losers_df["name"]
            display_losers["总收益 (元)"] = losers_df["total_gain"]
            display_losers["总收益 (%)"] = losers_df["total_gain_pct"]
            
            # 应用颜色（亏损用绿色）
            def style_losers(row):
                return ['', '', 'color: #10A37F; font-weight: bold', 'color: #10A37F; font-weight: bold']
            
            styled_losers = display_losers.style.apply(style_losers, axis=1)
            st.dataframe(
                styled_losers,
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("请在左侧设置回测参数并点击'运行回测'按钮开始回测")
