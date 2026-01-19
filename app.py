"""
DAAS Alpha v1.2.2 - Streamlit 入口
机会挖掘 (Hunter) | 时光机 (Backtest) | 复盘验证 (Truth)
"""

import pandas as pd
import streamlit as st
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

load_dotenv()

# 日志配置
_log_level, _log_file = "INFO", "logs/app.log"
_config = Path("config/settings.yaml")
if _config.exists():
    try:
        with open(_config, "r", encoding="utf-8") as f:
            _c = yaml.safe_load(f) or {}
        _log = _c.get("logging") or {}
        _log_level = str(_log.get("level") or _log_level)
        _log_file = str(_log.get("file") or _log_file)
    except Exception:
        pass
from src.logging_config import setup_logging, get_logger

setup_logging(log_level=_log_level, log_file=_log_file)
logger = get_logger(__name__)
logger.info("DAAS Alpha v1.2.2 Streamlit 启动")

st.set_page_config(page_title="DAAS Alpha v1.2.2", layout="wide", page_icon="🛰️")

# 自定义CSS：将按钮改为浅蓝色，导航链接样式
st.markdown("""
    <style>
    .stButton > button {
        background-color: #87CEEB !important;
        color: #000000 !important;
        border: 1px solid #4682B4 !important;
    }
    .stButton > button:hover {
        background-color: #B0E0E6 !important;
        border: 1px solid #4682B4 !important;
    }
    /* 导航链接样式 */
    div[data-testid="stButton"] > button[kind="secondary"] {
        background-color: transparent !important;
        color: #1f77b4 !important;
        border: 1px solid transparent !important;
        text-align: left !important;
        padding: 0.75rem 1rem !important;
        width: 100% !important;
        box-shadow: none !important;
    }
    div[data-testid="stButton"] > button[kind="secondary"]:hover {
        background-color: #f0f8ff !important;
        border-color: #87CEEB !important;
        color: #1f77b4 !important;
    }
    </style>
    """, unsafe_allow_html=True)

from src.database import (
    save_daily_predictions,
    get_all_predictions,
    update_prediction_price,
)
from src.data_provider import DataProvider
from src.strategy import get_trade_date, AlphaStrategy
from src.factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
from src.backtest import VectorBacktester

# 初始化 session state
if "hunter_df" not in st.session_state:
    st.session_state.hunter_df = None
if "hunter_trade_date" not in st.session_state:
    st.session_state.hunter_trade_date = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "🚀 机会挖掘"

# ========== 侧边栏 ==========
with st.sidebar:
    st.title("🛰️ DAAS Alpha v1.2.2")
    st.markdown("---")
    
    # 导航菜单 - 使用链接样式
    st.subheader("导航")
    
    # 定义页面选项
    pages = ["🚀 机会挖掘", "⏳ 时光机", "⚖️ 复盘验证"]
    current_page = st.session_state.current_page
    
    # 创建导航链接（使用按钮但样式化为链接）
    for page_name in pages:
        is_active = (current_page == page_name)
        
        if is_active:
            # 当前页面显示为激活状态
            st.markdown(f"""
                <div style="
                    padding: 0.75rem 1rem;
                    margin: 0.25rem 0;
                    background-color: #87CEEB;
                    color: #000000;
                    border-radius: 0.5rem;
                    font-weight: bold;
                    border: 1px solid #4682B4;
                ">{page_name}</div>
            """, unsafe_allow_html=True)
        else:
            # 其他页面显示为可点击的链接
            if st.button(page_name, key=f"nav_{page_name}", use_container_width=True, type="secondary"):
                st.session_state.current_page = page_name
                st.rerun()
    
    st.markdown("---")
    st.caption("DAAS Alpha v1.2.2 MVP Pro Edition")

# ========== 主内容区 ==========
page = st.session_state.current_page

if page == "🚀 机会挖掘":
    st.header("🔍 机会挖掘 (Hunter)")
    st.markdown("基于 Alpha Trident 策略的智能选股系统")
    
    if st.button("🚀 启动全流程扫描", use_container_width=True):
        logger.info("Hunter 扫描开始")
        
        # 检查 Token
        if not os.getenv("TUSHARE_TOKEN"):
            st.error("❌ 请先在侧边栏设置 Tushare Token")
            st.stop()
        
        try:
            # 步骤1: 获取数据
            with st.status("📥 获取数据中...", expanded=True) as status:
                st.write("正在连接 Tushare API...")
                try:
                    dp = DataProvider()
                    st.write("✅ Tushare 连接成功")
                except ValueError as e:
                    logger.error("DataProvider 初始化失败: %s", e)
                    st.error(f"❌ 初始化失败: {e}")
                    st.stop()
                
                trade_date = get_trade_date()
                st.write(f"交易日期: {trade_date}")
                st.write("正在获取股票基础数据...")
                
                # 获取基础数据
                basic_df = dp.get_daily_basic(trade_date)
                if basic_df.empty:
                    st.error("❌ 无法获取基础数据")
                    st.stop()
                
                # 获取历史日线数据（因子需要历史数据：RPS 60天，MA 20天，VolumeRatio 5天）
                st.write("正在获取历史日线数据（这可能需要一些时间）...")
                # 考虑到节假日、停牌等因素，70个自然日可能只有约40-50个交易日
                # 为了确保有60个交易日，需要获取约120个自然日的数据（约3-4个月）
                history_days = 120  # 60个交易日约需要120个自然日（考虑节假日和周末）
                start_date = (datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=history_days)).strftime("%Y%m%d")
                
                history_df = dp.fetch_history_for_hunter(
                    trade_date=trade_date,
                    start_date=start_date,
                    index_code=None,  # 使用配置的指数
                    use_cache=True
                )
                
                if history_df.empty:
                    st.error("❌ 无法获取历史日线数据")
                    st.stop()
                
                st.write(f"✅ 获取历史数据完成，共 {len(history_df)} 条记录")
                
                # 过滤到目标交易日的数据
                daily_df = history_df[history_df['trade_date'] == trade_date].copy()
                
                if daily_df.empty:
                    st.error("❌ 目标交易日无数据")
                    st.stop()
                
                # 合并基础数据和日线数据
                merged_df = basic_df.merge(daily_df, on=["ts_code", "trade_date"], how="inner")
                
                if merged_df.empty:
                    st.error("❌ 数据合并失败")
                    st.stop()
                
                # 为了计算因子，需要包含历史数据
                # 将历史数据添加到 merged_df 中（用于因子计算）
                # 但只保留在 basic_df 中的股票
                valid_codes = set(merged_df['ts_code'].unique())
                history_for_factors = history_df[history_df['ts_code'].isin(valid_codes)].copy()
                
                # 诊断：检查每个股票的历史数据数量
                stock_data_counts = history_for_factors.groupby('ts_code').size()
                stocks_with_enough_data = (stock_data_counts >= 60).sum()
                st.write(f"📊 数据完整性: {stocks_with_enough_data}/{len(valid_codes)} 只股票有≥60条历史数据")
                
                # 合并历史数据到 merged_df（用于因子计算）
                # 注意：merged_df 只包含目标交易日的数据，history_for_factors 包含历史数据
                # 因子计算需要完整的历史数据，所以我们将 history_for_factors 用于因子计算
                
                # 先对 basic_df 去重，确保每个股票只有一条记录
                basic_df_unique = basic_df[['ts_code', 'name', 'list_date', 'pe_ttm', 'pb', 'mv', 'dividend_yield']].drop_duplicates(subset=['ts_code'], keep='first')
                
                merged_df = history_for_factors.merge(
                    basic_df_unique,
                    on='ts_code',
                    how='inner'
                )
                
                # 确保 trade_date 列存在且格式正确
                # 注意：因子计算需要 datetime 格式，所以先不转换为字符串
                if 'trade_date' in merged_df.columns:
                    # 确保是 datetime 格式（因子计算需要）
                    if merged_df['trade_date'].dtype == 'object':
                        merged_df['trade_date'] = pd.to_datetime(merged_df['trade_date'], format='%Y%m%d', errors='coerce')
                
                st.write(f"✅ 获取数据完成，共 {len(merged_df)} 条记录（包含历史数据）")
                status.update(label="✅ 数据获取完成", state="complete")
            
            # 步骤2: 计算因子
            with st.status("🔢 计算因子中...", expanded=True) as status:
                st.write("初始化因子管道...")
                pipeline = FactorPipeline()
                pipeline.add(RPSFactor(window=60))
                pipeline.add(MAFactor(window=20))
                pipeline.add(VolumeRatioFactor(window=5))
                pipeline.add(PEProxyFactor(max_pe=30))
                
                st.write("计算 RPS 因子...")
                st.write("计算 MA 因子...")
                st.write("计算量比因子...")
                st.write("计算 PE 因子...")
                
                enriched_df = pipeline.run(merged_df.copy())
                
                # 诊断信息：检查因子计算情况
                if 'rps_60' in enriched_df.columns:
                    rps_valid = enriched_df['rps_60'].notna().sum()
                    rps_total = len(enriched_df)
                    if rps_valid > 0:
                        rps_max = float(enriched_df['rps_60'].max())
                        rps_min = float(enriched_df['rps_60'].min())
                        rps_mean = float(enriched_df['rps_60'].mean())
                        rps_above_85 = int((enriched_df['rps_60'] > 85).sum())
                        st.write(f"📊 RPS因子: 有效值 {rps_valid}/{rps_total}, 范围 [{rps_min:.1f}, {rps_max:.1f}], 均值 {rps_mean:.1f}, >85: {rps_above_85}")
                        
                        # 显示不同阈值下的股票数量
                        thresholds = [80, 75, 70, 65, 60]
                        threshold_counts = {t: int((enriched_df['rps_60'] > t).sum()) for t in thresholds}
                        st.write(f"📈 RPS阈值分布: {', '.join([f'>={t}: {threshold_counts[t]}' for t in thresholds])}")
                    else:
                        st.warning(f"⚠️ RPS因子: 无有效值（可能历史数据不足60天）")
                
                st.write(f"✅ 因子计算完成")
                status.update(label="✅ 因子计算完成", state="complete")
            
            # 步骤3: 应用策略
            with st.status("🎯 应用 Alpha Trident 策略中...", expanded=True) as status:
                st.write("筛选符合条件的股票...")
                
                # 只使用目标交易日的数据进行策略筛选
                # 确保 trade_date 格式一致（可能是 datetime 或字符串）
                if enriched_df['trade_date'].dtype != 'object':
                    # 如果是 datetime，转换为字符串进行比较
                    enriched_df['trade_date_str'] = enriched_df['trade_date'].dt.strftime('%Y%m%d')
                    target_date_df = enriched_df[enriched_df['trade_date_str'] == trade_date].copy()
                    target_date_df = target_date_df.drop(columns=['trade_date_str'])
                else:
                    target_date_df = enriched_df[enriched_df['trade_date'] == trade_date].copy()
                
                # 去重：如果同一个股票在同一天有多条记录，保留第一条（按索引）
                # 这可能是由于数据合并时的问题导致的重复
                before_dedup = len(target_date_df)
                target_date_df = target_date_df.drop_duplicates(subset=['ts_code'], keep='first')
                if len(target_date_df) < before_dedup:
                    logger.warning(f"发现重复股票记录，已去重: {before_dedup} -> {len(target_date_df)}")
                    st.warning(f"⚠️ 发现 {before_dedup - len(target_date_df)} 条重复记录，已自动去重")
                
                if target_date_df.empty:
                    st.warning("⚠️ 目标交易日无数据")
                    status.update(label="⚠️ 筛选完成（无数据）", state="complete")
                    st.session_state.hunter_df = None
                    st.stop()
                
                strategy = AlphaStrategy(target_date_df)
                result_df = strategy.filter_alpha_trident()
                
                if result_df.empty:
                    st.warning("⚠️ 无股票通过 Alpha Trident 筛选条件")
                    status.update(label="⚠️ 筛选完成（无结果）", state="complete")
                    st.session_state.hunter_df = None
                else:
                    st.write(f"✅ 筛选完成，共 {len(result_df)} 只股票")
                    status.update(label="✅ 策略筛选完成", state="complete")
                    
                    # 保存结果到 session state
                    st.session_state.hunter_df = result_df
                    st.session_state.hunter_trade_date = trade_date
                    logger.info(f"Hunter 扫描完成: {len(result_df)} 只股票")
                    st.success(f"✅ 扫描完成！共找到 {len(result_df)} 只符合条件的股票")
        
        except Exception as e:
            logger.exception("Hunter 扫描异常")
            st.error(f"❌ 扫描过程出错: {e}")
    
    # 显示结果
    if st.session_state.hunter_df is not None:
        st.markdown("---")
        st.subheader("📋 筛选结果")
        
        df = st.session_state.hunter_df.copy()
        
        # 格式化显示列
        display_df = pd.DataFrame()
        display_df["代码"] = df["ts_code"]
        display_df["名称"] = df["name"]
        display_df["现价"] = df["close"].round(2)
        display_df["RPS强度"] = df["rps_60"].round(2)
        display_df["量比"] = df["vol_ratio_5"].round(2)
        display_df["PE(TTM)"] = df["pe_ttm"].round(2)
        # 安全获取 strategy_tag，如果不存在则使用默认值
        display_df["建议"] = df.get("strategy_tag", "🚀 强推荐")
        
        # 高亮 RPS > 90 的行
        def highlight_rps(row):
            styles = [''] * len(row)
            if row['RPS强度'] > 90:
                return ['background-color: #ffeb3b'] * len(row)
            return styles
        
        styled_df = display_df.style.apply(highlight_rps, axis=1)
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        # 保存按钮
        if st.button("💾 存入数据库", use_container_width=True):
            if st.session_state.hunter_df is None:
                st.warning("⚠️ 请先执行扫描")
            else:
                df = st.session_state.hunter_df
                td = st.session_state.hunter_trade_date or get_trade_date()
                
                # 准备保存数据（注意：需要包含 price_at_prediction）
                rows = []
                for _, r in df.iterrows():
                    rows.append({
                        "trade_date": td,
                        "ts_code": r["ts_code"],
                        "name": r["name"],
                        "ai_score": 0,  # Alpha Trident 不使用 AI 评分
                        "ai_reason": "Alpha Trident 策略筛选",
                        "strategy_tag": r.get("strategy_tag", "🚀 强推荐"),
                        "suggested_shares": 0,  # 可以后续添加
                        "price_at_prediction": float(r.get("close", 0)),  # 保存预测时的价格
                    })
                
                save_daily_predictions(rows)
                logger.info("保存到数据库完成: trade_date=%s, %d 条", td, len(rows))
                st.success(f"✅ 已保存 {len(rows)} 条记录到数据库")

elif page == "⏳ 时光机":
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
                st.write("初始化数据提供者...")
                dp = DataProvider()
                
                st.write("获取历史数据（这可能需要几分钟）...")
                start_str = start_date.strftime("%Y%m%d")
                end_str = end_date.strftime("%Y%m%d")
                
                # 获取历史数据
                history_df = dp.fetch_history_batch(
                    start_date=start_str,
                    end_date=end_str,
                    index_code="000300.SH",  # 沪深300
                    use_cache=True
                )
                
                if history_df.empty:
                    st.error("❌ 无法获取历史数据")
                    st.stop()
                
                st.write(f"✅ 获取历史数据完成，共 {len(history_df)} 条记录")
                
                st.write("运行回测引擎（含止损和交易成本）...")
                backtester = VectorBacktester(dp)
                results = backtester.run(
                    history_df, 
                    holding_days=holding_days,
                    stop_loss_pct=stop_loss_pct,
                    cost_rate=transaction_cost
                )
                
                st.write("✅ 回测完成")
                status.update(label="✅ 回测完成", state="complete")
            
            # 保存dp到session state以便后续使用
            st.session_state.backtest_dp = dp
            
            # 显示结果
            st.markdown("---")
            st.subheader("📊 回测结果")
            
            # 从新版本结果中获取指标
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
                
                # 获取股票名称
                try:
                    # 使用回测时创建的DataProvider实例（如果存在）
                    dp = st.session_state.get('backtest_dp')
                    if dp is None:
                        dp = DataProvider()
                    stock_basic = dp.get_stock_basic()
                    if not stock_basic.empty:
                        # 合并股票名称
                        top_contributors = top_contributors.merge(
                            stock_basic[['ts_code', 'name']],
                            on='ts_code',
                            how='left'
                        )
                    else:
                        top_contributors['name'] = '未知'
                except Exception as e:
                    logger.warning(f"获取股票名称失败: {e}")
                    top_contributors['name'] = '未知'
                
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
        
        except Exception as e:
            logger.exception("Backtest 异常")
            st.error(f"❌ 回测过程出错: {e}")

elif page == "⚖️ 复盘验证":
    st.header("📈 复盘验证 (Truth)")
    st.markdown("追踪历史预测的实际表现")
    
    if st.button("🔄 更新最新价格", use_container_width=True):
        logger.info("Truth 更新开始")
        
        # 检查 Token
        if not os.getenv("TUSHARE_TOKEN"):
            st.error("❌ 请先在侧边栏设置 Tushare Token")
            st.stop()
        
        try:
            with st.status("🔄 更新价格中...", expanded=True) as status:
                st.write("初始化数据提供者...")
                dp = DataProvider()
                
                st.write("从数据库读取预测记录...")
                all_predictions = get_all_predictions()
                
                if not all_predictions:
                    st.info("ℹ️ 数据库中没有预测记录")
                    st.stop()
                
                st.write(f"找到 {len(all_predictions)} 条预测记录")
                
                # 获取当前交易日期
                current_trade_date = get_trade_date()
                
                updated_count = 0
                for i, pred in enumerate(all_predictions):
                    ts_code = pred["ts_code"]
                    pred_date = pred["trade_date"]
                    
                    try:
                        # 获取预测日期的价格（作为当时价格）
                        pred_daily = dp._pro.daily(
                            ts_code=ts_code,
                            trade_date=pred_date,
                            fields="ts_code,trade_date,close"
                        )
                        
                        # 获取最新价格
                        latest_daily = dp._pro.daily(
                            ts_code=ts_code,
                            trade_date=current_trade_date,
                            fields="ts_code,trade_date,close"
                        )
                        
                        if not pred_daily.empty and not latest_daily.empty:
                            price_at_pred = pred_daily.iloc[0]["close"]
                            current_price = latest_daily.iloc[0]["close"]
                            
                            # 计算收益率
                            if price_at_pred > 0:
                                return_pct = (current_price - price_at_pred) / price_at_pred * 100
                                
                                # 更新数据库（包括价格）
                                from src.database import update_prediction_price_at_prediction
                                # 如果 price_at_prediction 为空，先更新它
                                if pd.isna(pred.get("price_at_prediction")):
                                    update_prediction_price_at_prediction(pred_date, ts_code, price_at_pred)
                                update_prediction_price(pred_date, ts_code, current_price, return_pct)
                                updated_count += 1
                        
                        # API 限流
                        import time
                        time.sleep(0.1)
                        
                        if (i + 1) % 10 == 0:
                            status.update(label=f"🔄 更新中... ({i+1}/{len(all_predictions)})", state="running")
                            st.write(f"已处理 {i+1}/{len(all_predictions)} 条记录...")
                    
                    except Exception as e:
                        logger.debug(f"更新 {ts_code} 失败: {e}")
                        continue
                
                logger.info("Truth 更新完成: 更新 %d 条", updated_count)
                status.update(label="✅ 更新完成", state="complete")
                st.success(f"✅ 已更新 {updated_count} 条记录")
        
        except Exception as e:
            logger.exception("Truth 更新异常")
            st.error(f"❌ 更新过程出错: {e}")
    
    # 显示验证结果
    st.markdown("---")
    st.subheader("📊 验证结果")
    
    all_predictions = get_all_predictions()
    if all_predictions:
        df = pd.DataFrame(all_predictions)
        
        # 计算胜率
        verified_df = df[df["actual_chg"].notna()]
        if not verified_df.empty:
            win_count = len(verified_df[verified_df["actual_chg"] > 0])
            total_count = len(verified_df)
            win_rate = (win_count / total_count * 100) if total_count > 0 else 0
            
            st.metric("历史胜率", f"{win_rate:.2f}%", f"{win_count}/{total_count}")
        
        # 准备显示数据
        display_df = pd.DataFrame()
        display_df["预测日期"] = df["trade_date"]
        display_df["代码"] = df["ts_code"]
        display_df["名称"] = df["name"]
        display_df["当时价格"] = df["price_at_prediction"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "未知"
        )
        display_df["最新价格"] = df["current_price"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "待更新"
        )
        display_df["累计涨跌幅"] = df["actual_chg"].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else "待更新"
        )
        
        # 结果列（使用 emoji）
        def get_result_emoji(chg):
            if pd.isna(chg):
                return "➖"
            elif chg > 0:
                return "✅"
            elif chg < 0:
                return "❌"
            else:
                return "➖"
        
        display_df["结果"] = df["actual_chg"].apply(get_result_emoji)
        
        # 颜色编码
        def color_return(val):
            if isinstance(val, str) and val != "待更新":
                try:
                    chg = float(val.replace("%", ""))
                    if chg > 0:
                        return "color: red; font-weight: bold"
                    elif chg < 0:
                        return "color: green; font-weight: bold"
                except:
                    pass
            return ""
        
        styled_df = display_df.style.applymap(color_return, subset=["累计涨跌幅"])
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("ℹ️ 暂无预测记录")
