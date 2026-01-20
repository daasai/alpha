"""
Backtest Page - 回测页面
"""

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import os
from datetime import datetime, timedelta
from src.services import BacktestService
from src.logging_config import get_logger

logger = get_logger(__name__)


def render_backtest_page():
    """渲染Backtest页面"""
    st.header("⏳ 时光机 (Backtest)")
    st.markdown("策略回测与验证")
    
    # 控制面板
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
    
    col3, col4 = st.columns(2)
    
    with col3:
        holding_days = st.slider("持仓天数", min_value=1, max_value=20, value=5, step=1)
    
    with col4:
        stop_loss_pct = st.slider(
            "止损比例 (%)",
            min_value=0,
            max_value=20,
            value=8,
            step=1,
            help="止损百分比，范围 0-20%，默认 8%"
        ) / 100.0  # 转换为小数
    
    transaction_cost = st.number_input(
        "交易成本率",
        min_value=0.0,
        max_value=0.01,
        value=0.002,
        step=0.0001,
        format="%.4f",
        help="交易成本率，默认 0.002 (0.2%)"
    )
    
    if st.button("🚀 开始回测", use_container_width=True):
        logger.info("Backtest 开始")
        
        # 检查 Token
        if not os.getenv("TUSHARE_TOKEN"):
            st.error("❌ 请先在侧边栏设置 Tushare Token")
            st.stop()
        
        try:
            with st.status("🔄 回测中...", expanded=True) as status:
                st.write("初始化服务...")
                backtest_service = BacktestService()
                
                st.write("运行回测引擎（含止损和交易成本）...")
                start_str = start_date.strftime("%Y%m%d")
                end_str = end_date.strftime("%Y%m%d")
                
                result = backtest_service.run_backtest(
                    start_date=start_str,
                    end_date=end_str,
                    holding_days=holding_days,
                    stop_loss_pct=stop_loss_pct,
                    cost_rate=transaction_cost
                )
                
                if not result.success:
                    st.error(f"❌ {result.error}")
                    st.stop()
                
                st.write("✅ 回测完成")
                status.update(label="✅ 回测完成", state="complete")
            
            # 显示结果
            _display_backtest_results(result.results)
        
        except Exception as e:
            logger.exception("Backtest 异常")
            st.error(f"❌ 回测过程出错: {e}")


def _display_backtest_results(results: dict):
    """显示回测结果"""
    st.markdown("---")
    st.subheader("📊 回测结果")
    
    total_return = results.get("total_return", 0.0)
    max_drawdown = results.get("max_drawdown", 0.0)
    win_rate = results.get("win_rate", 0.0)
    equity_curve = results.get("equity_curve", pd.Series(dtype=float))
    strategy_metrics = results.get("strategy_metrics", {})
    benchmark_metrics = results.get("benchmark_metrics", {})
    
    # 检查最大回撤警告
    if max_drawdown > 30:
        st.error("⚠️ 回撤过大，策略需优化！")
    
    # 指标显示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        benchmark_return = benchmark_metrics.get("total_return", 0.0)
        diff = total_return - benchmark_return
        st.metric(
            "总收益率",
            f"{total_return:.2f}%",
            delta=f"{diff:.2f}% vs 基准"
        )
    
    with col2:
        # 最大回撤：如果 > 20% 显示为红色警告
        if max_drawdown > 20:
            st.markdown(f'<p style="color: red; font-size: 0.9em; margin-bottom: 0;">最大回撤</p>', unsafe_allow_html=True)
            st.markdown(f'<h3 style="color: red; margin-top: 0;">{max_drawdown:.2f}%</h3>', unsafe_allow_html=True)
            st.caption("⚠️ 风险较高")
        else:
            st.metric("最大回撤", f"{max_drawdown:.2f}%")
    
    with col3:
        st.metric("胜率", f"{win_rate:.2f}%")
    
    with col4:
        st.metric("最大持仓数", "4", help="固定为4个持仓，每个持仓25%资金")
    
    # 绘制权益曲线对比图
    st.markdown("---")
    st.subheader("📈 策略 vs 基准权益曲线")
    
    if not equity_curve.empty:
        # 创建策略权益曲线图表
        fig = go.Figure()
        
        # 策略权益曲线
        fig.add_trace(go.Scatter(
            x=equity_curve.index,
            y=equity_curve.values,
            mode="lines",
            name="策略净值",
            line=dict(color="#1f77b4", width=2)
        ))
        
        # 基准权益曲线（如果有）
        benchmark_total_return = benchmark_metrics.get("total_return", 0) / 100.0
        if benchmark_total_return != 0 and len(equity_curve) > 1:
            # 计算基准权益曲线（使用复利计算，假设每日均匀分布）
            num_days = len(equity_curve)
            daily_return = (1 + benchmark_total_return) ** (1.0 / num_days) - 1
            benchmark_values = [(1 + daily_return) ** i for i in range(num_days)]
            benchmark_curve = pd.Series(
                index=equity_curve.index,
                data=benchmark_values
            )
            fig.add_trace(go.Scatter(
                x=benchmark_curve.index,
                y=benchmark_curve.values,
                mode="lines",
                name="基准净值",
                line=dict(color="#ff7f0e", width=2, dash="dash")
            ))
        
        fig.update_layout(
            title="策略 vs 基准权益曲线对比",
            xaxis_title="日期",
            yaxis_title="净值",
            hovermode="x unified",
            height=500,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无权益曲线数据")
    
    # 显示交易统计
    trades_df = results.get("trades", pd.DataFrame())
    if not trades_df.empty:
        st.markdown("---")
        st.subheader("📋 交易统计")
        total_trades = strategy_metrics.get("total_trades", len(trades_df))
        st.metric("总交易数", total_trades)
    
    # 显示Top 3 Contributors
    top_contributors = results.get("top_contributors", pd.DataFrame())
    if not top_contributors.empty:
        st.markdown("---")
        st.subheader("🏆 Top 3 Contributors (Lucky Stocks)")
        st.markdown("识别贡献最大的股票")
        
        # 格式化显示
        display_contributors = pd.DataFrame()
        display_contributors["股票代码"] = top_contributors["ts_code"]
        display_contributors["股票名称"] = top_contributors.get("name", "未知")
        display_contributors["总收益 (元)"] = top_contributors["total_gain"].round(2)
        display_contributors["总收益 (%)"] = top_contributors["total_gain_pct"]
        
        st.dataframe(
            display_contributors,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.markdown("---")
        st.info("ℹ️ 暂无贡献者数据（可能没有完成交易）")
