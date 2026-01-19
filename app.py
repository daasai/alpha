"""
DAAS Alpha v1.1 - Streamlit 入口
Hunter：筛选 + AI 情感分析 + 入库；Truth：用实际涨跌幅回填并展示。
"""

import pandas as pd
import streamlit as st
import yaml
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# 日志：优先读 config/settings.yaml 的 logging，否则默认 INFO + logs/app.log
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
logger.info("DAAS Alpha v1.1 Streamlit 启动")

st.set_page_config(page_title="DAAS Alpha v1.1", layout="wide", page_icon="📊")

from src.database import (
    get_pending_predictions,
    get_verified_predictions,
    save_daily_predictions,
    update_actual_performance,
    create_analysis_task,
    update_task_status,
    save_task_result,
    get_running_task,
    get_latest_task,
    get_task_by_id,
    load_task_result,
    list_tasks_by_trade_date,
)
from src.data_provider import DataProvider
from src.strategy import get_trade_date, run_screening
from src.monitor import analyze_sentiment

# 初始化 session state
if "hunter_df" not in st.session_state:
    st.session_state.hunter_df = None
if "hunter_trade_date" not in st.session_state:
    st.session_state.hunter_trade_date = None
if "risk_budget" not in st.session_state:
    st.session_state.risk_budget = 10000.0
if "current_task_id" not in st.session_state:
    st.session_state.current_task_id = None

# 页面加载时检查并恢复运行中的任务或最近一次已完成的任务
if "task_recovered" not in st.session_state:
    st.session_state.task_recovered = False
    # 首先检查是否有运行中的任务
    running_task = get_running_task()
    if running_task:
        # 如果任务已完成，加载结果
        if running_task["status"] == "completed":
            df = load_task_result(running_task["task_id"])
            if df is not None:
                st.session_state.hunter_df = df
                st.session_state.hunter_trade_date = running_task["trade_date"]
                st.session_state.current_task_id = running_task["task_id"]
                st.session_state.task_recovered = True
                logger.info(f"恢复已完成的任务: {running_task['task_id']}")
        # 如果任务失败，标记为已恢复（显示错误信息）
        elif running_task["status"] == "failed":
            st.session_state.current_task_id = running_task["task_id"]
            st.session_state.task_recovered = True
            logger.info(f"发现失败的任务: {running_task['task_id']}")
        # 如果任务正在运行，标记为已恢复（显示运行状态）
        elif running_task["status"] == "running":
            st.session_state.current_task_id = running_task["task_id"]
            st.session_state.task_recovered = True
            logger.info(f"发现运行中的任务: {running_task['task_id']}")
    else:
        # 如果没有运行中的任务，尝试恢复最近一次已完成的任务
        latest_task = get_latest_task()
        if latest_task and latest_task["status"] == "completed":
            df = load_task_result(latest_task["task_id"])
            if df is not None:
                st.session_state.hunter_df = df
                st.session_state.hunter_trade_date = latest_task["trade_date"]
                st.session_state.current_task_id = latest_task["task_id"]
                st.session_state.task_recovered = True
                logger.info(f"恢复最近一次已完成的任务: {latest_task['task_id']}")

# ========== 侧边栏 ==========
with st.sidebar:
    st.title("📊 DAAS Alpha v1.1")
    st.markdown("---")
    
    # 导航
    st.subheader("导航")
    page = st.radio(
        "选择页面",
        ["Hunter", "Truth"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 设置
    st.subheader("设置")
    
    # Tushare Token
    current_token = os.getenv("TUSHARE_TOKEN", "")
    tushare_token = st.text_input(
        "Tushare Token",
        value=current_token,
        type="password",
        help="请输入您的 Tushare Pro Token（2200+积分）"
    )
    if tushare_token and tushare_token != current_token:
        # 更新环境变量（仅当前会话有效）
        os.environ["TUSHARE_TOKEN"] = tushare_token
        st.info("Token 已更新（仅当前会话有效）")
    
    # Risk Budget
    risk_budget = st.number_input(
        "风险预算（元）",
        min_value=1000.0,
        max_value=1000000.0,
        value=st.session_state.risk_budget,
        step=1000.0,
        help="用于计算ATR仓位的风险预算"
    )
    st.session_state.risk_budget = risk_budget
    
    st.markdown("---")
    
    # 任务历史
    st.subheader("任务历史")
    trade_date_for_history = get_trade_date()
    recent_tasks = list_tasks_by_trade_date(trade_date_for_history, limit=5)
    if recent_tasks:
        for task in recent_tasks:
            status_emoji = {
                "pending": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(task["status"], "❓")
            
            task_label = f"{status_emoji} {task['task_id']}"
            if task["status"] == "completed":
                if st.button(task_label, key=f"task_{task['task_id']}", use_container_width=True):
                    df = load_task_result(task["task_id"])
                    if df is not None:
                        st.session_state.hunter_df = df
                        st.session_state.hunter_trade_date = task["trade_date"]
                        st.session_state.current_task_id = task["task_id"]
                        st.rerun()
            else:
                st.caption(task_label)
    else:
        st.caption("暂无历史任务")
    
    st.markdown("---")
    st.caption("DAAS Alpha v1.1 MVP Pro Edition")

# ========== 主内容区 ==========
if page == "Hunter":
    st.header("🔍 Hunter - 股票筛选与AI分析")
    
    # 任务状态显示区域
    if st.session_state.current_task_id:
        task = get_task_by_id(st.session_state.current_task_id)
        if task:
            status_info = {
                "pending": ("⏳ 等待中", "secondary"),
                "running": ("🔄 运行中", "primary"),
                "completed": ("✅ 已完成", "success"),
                "failed": ("❌ 失败", "error")
            }.get(task["status"], ("❓ 未知", "secondary"))
            
            status_text, status_color = status_info
            st.info(f"**当前任务**: {task['task_id']} | {status_text}")
            
            if task["status"] == "running" and task["current_step"]:
                step_names = {
                    "fetching": "获取数据",
                    "screening": "筛选",
                    "ai_analysis": "AI分析",
                    "calculating": "计算风险"
                }
                st.caption(f"当前步骤: {step_names.get(task['current_step'], task['current_step'])}")
                if task["progress_message"]:
                    st.caption(f"进度: {task['progress_message']}")
            
            if task["status"] == "failed" and task["error_message"]:
                st.error(f"错误信息: {task['error_message']}")
    
    if st.button("🚀 开始分析", type="primary", use_container_width=True):
        logger.info("Hunter 分析开始")
        
        # 检查 Token
        if not os.getenv("TUSHARE_TOKEN"):
            st.error("❌ 请先在侧边栏设置 Tushare Token")
            st.stop()
        
        try:
            # 创建分析任务
            trade_date = get_trade_date()
            task_id = create_analysis_task(trade_date, st.session_state.risk_budget)
            st.session_state.current_task_id = task_id
            update_task_status(task_id, status='running', current_step='fetching', progress_message='开始分析...')
            logger.info(f"创建任务: {task_id}")
            
            # 步骤1: 获取数据
            with st.status("📥 获取数据中...", expanded=True) as status:
                st.write("正在连接 Tushare API...")
                try:
                    dp = DataProvider()
                    st.write("✅ Tushare 连接成功")
                    update_task_status(task_id, current_step='fetching', progress_message='Tushare 连接成功')
                except ValueError as e:
                    logger.error("DataProvider 初始化失败: %s", e)
                    update_task_status(task_id, status='failed', error_message=f"初始化失败: {e}")
                    st.error(f"❌ 初始化失败: {e}")
                    st.stop()
                
                st.write("正在获取股票基础数据...")
                update_task_status(task_id, current_step='fetching', progress_message='正在获取股票基础数据...')
                status.update(label="📥 获取数据中...", state="running")
            
            # 步骤2: 筛选
            with st.status("🔍 筛选中...", expanded=True) as status:
                st.write("执行硬过滤规则...")
                st.write("应用杠铃策略...")
                update_task_status(task_id, current_step='screening', progress_message='执行硬过滤规则和应用杠铃策略...')
                df = run_screening(
                    trade_date=trade_date,
                    data_provider=dp,
                    risk_budget=st.session_state.risk_budget
                )
                if df.empty:
                    logger.warning("筛选后无股票")
                    update_task_status(task_id, status='failed', error_message='无股票通过筛选条件')
                    status.update(label="⚠️ 筛选完成（无结果）", state="complete")
                    st.warning("⚠️ 无股票通过筛选条件")
                    st.stop()
                else:
                    st.write(f"✅ 筛选完成，共 {len(df)} 只股票")
                    update_task_status(task_id, current_step='screening', progress_message=f'筛选完成，共 {len(df)} 只股票')
                    status.update(label="✅ 筛选完成", state="complete")
            
            # 步骤3: AI分析
            with st.status("🤖 AI 分析中...", expanded=True) as status:
                st.write("正在调用 AI 进行情感分析...")
                update_task_status(task_id, current_step='ai_analysis', progress_message='正在调用 AI 进行情感分析...')
                try:
                    df = analyze_sentiment(df, data_provider=dp)
                    st.write(f"✅ AI 分析完成，共 {len(df)} 只股票")
                    update_task_status(task_id, current_step='ai_analysis', progress_message=f'AI 分析完成，共 {len(df)} 只股票')
                    status.update(label="✅ AI 分析完成", state="complete")
                except ValueError as e:
                    logger.error("analyze_sentiment 失败: %s", e)
                    update_task_status(task_id, status='failed', error_message=f"AI 分析失败: {e}")
                    status.update(label="❌ AI 分析失败", state="error")
                    st.error(f"❌ AI 分析失败: {e}")
                    st.stop()
            
            # 步骤4: 计算风险（ATR已在筛选时计算）
            with st.status("📊 计算风险中...", expanded=True) as status:
                st.write("ATR 仓位计算已完成")
                update_task_status(task_id, current_step='calculating', progress_message='ATR 仓位计算已完成')
                status.update(label="✅ 风险计算完成", state="complete")
            
            # 保存任务结果
            save_task_result(task_id, df)
            update_task_status(task_id, status='completed', current_step='completed', progress_message='分析完成')
            
            # 保存结果到 session state
            st.session_state.hunter_df = df
            st.session_state.hunter_trade_date = str(df["trade_date"].iloc[0]) if len(df) > 0 else trade_date
            logger.info(f"Hunter 分析完成: {task_id}, %d 只股票", len(df))
            st.success(f"✅ 分析完成！任务ID: {task_id}，共找到 {len(df)} 只符合条件的股票")
            
        except Exception as e:
            logger.exception("Hunter 分析异常")
            if st.session_state.current_task_id:
                update_task_status(st.session_state.current_task_id, status='failed', error_message=f"分析过程出错: {str(e)}")
            st.error(f"❌ 分析过程出错: {e}")
    
    # 显示结果
    if st.session_state.hunter_df is not None:
        st.markdown("---")
        st.subheader("📋 筛选结果")
        
        df = st.session_state.hunter_df.copy()
        
        # 颜色编码函数
        def color_ai_score(val):
            if pd.isna(val):
                return ""
            score = float(val)
            if score > 0:
                return "color: red; font-weight: bold"
            elif score < 0:
                return "color: green; font-weight: bold"
            return ""
        
        # 格式化显示
        display_df = df.copy()
        
        # 应用颜色样式
        styled_df = display_df.style.applymap(
            color_ai_score,
            subset=["ai_score"]
        )
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        # 保存按钮
        if st.button("💾 保存到数据库", type="primary", use_container_width=True):
            if st.session_state.hunter_df is None:
                st.warning("⚠️ 请先执行分析")
            else:
                df = st.session_state.hunter_df
                td = st.session_state.hunter_trade_date or (
                    str(df["trade_date"].iloc[0]) if "trade_date" in df.columns and len(df) > 0 else get_trade_date()
                )
                rows = [
                    {
                        "trade_date": td,
                        "ts_code": r["ts_code"],
                        "name": r["name"],
                        "ai_score": int(r["ai_score"]),
                        "ai_reason": str(r.get("ai_reason", "")),
                        "strategy_tag": str(r.get("strategy_tag", "")),
                        "suggested_shares": int(r.get("suggested_shares", 0)),
                    }
                    for r in df.to_dict("records")
                ]
                save_daily_predictions(rows)
                logger.info("保存到数据库完成: trade_date=%s, %d 条", td, len(rows))
                st.success(f"✅ 已保存 {len(rows)} 条记录到数据库")

elif page == "Truth":
    st.header("📈 Truth - 回测验证")
    
    if st.button("🔄 验证表现", type="primary", use_container_width=True):
        logger.info("Truth 验证开始")
        
        # 检查 Token
        if not os.getenv("TUSHARE_TOKEN"):
            st.error("❌ 请先在侧边栏设置 Tushare Token")
            st.stop()
        
        try:
            dp = DataProvider()
        except ValueError as e:
            logger.error("Verify: DataProvider 初始化失败: %s", e)
            st.error(f"❌ 初始化失败: {e}")
            st.stop()
        
        pending = get_pending_predictions()
        if not pending:
            st.info("ℹ️ 无待回填记录")
        else:
            with st.status("🔄 验证中...", expanded=True) as status:
                from collections import defaultdict
                
                st.write(f"找到 {len(pending)} 条待验证记录")
                by_date = defaultdict(list)
                for p in pending:
                    by_date[p["trade_date"]].append(p["ts_code"])
                
                updated = 0
                total = len(pending)
                for i, (trade_date, ts_codes) in enumerate(by_date.items()):
                    st.write(f"处理 {trade_date} 的 {len(ts_codes)} 只股票...")
                    pch = dp.get_daily_pct_chg(trade_date, ts_codes)
                    for _, row in pch.iterrows():
                        if pd.notna(row.get("pct_chg")):
                            update_actual_performance(
                                str(trade_date),
                                str(row["ts_code"]),
                                float(row["pct_chg"]),
                            )
                            updated += 1
                    status.update(label=f"🔄 验证中... ({updated}/{total})", state="running")
                
                logger.info("Truth 验证完成: 更新 %d 条", updated)
                status.update(label="✅ 验证完成", state="complete")
                st.success(f"✅ 已更新 {updated} 条记录")
    
    # 显示验证结果
    verified = get_verified_predictions()
    if verified:
        st.markdown("---")
        st.subheader("📊 验证结果")
        
        df = pd.DataFrame(verified)
        
        # 颜色编码函数
        def color_pct_chg(val):
            if pd.isna(val):
                return ""
            chg = float(val)
            if chg > 0:
                return "color: red; font-weight: bold"
            elif chg < 0:
                return "color: green; font-weight: bold"
            return ""
        
        def color_ai_score(val):
            if pd.isna(val):
                return ""
            score = float(val)
            if score > 0:
                return "color: red; font-weight: bold"
            elif score < 0:
                return "color: green; font-weight: bold"
            return ""
        
        # 应用样式
        styled_df = df.style.applymap(
            color_ai_score,
            subset=["ai_score"]
        ).applymap(
            color_pct_chg,
            subset=["actual_chg"]
        )
        
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
        
        # 统计信息
        if len(df) > 0:
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("总记录数", len(df))
            with col2:
                avg_chg = df["actual_chg"].mean()
                st.metric("平均涨跌幅", f"{avg_chg:.2f}%")
            with col3:
                positive_count = len(df[df["actual_chg"] > 0])
                st.metric("上涨数量", positive_count)
    else:
        st.info("ℹ️ 暂无验证结果")
