"""
DAAS Alpha v1.3 - Streamlit 入口
Fintech Clean Design System
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
logger.info("DAAS Alpha v1.3 Streamlit 启动")

st.set_page_config(page_title="DAAS Alpha v1.3", layout="wide", page_icon=None)

# Fintech Clean Design System CSS
st.markdown("""
    <style>
    /* Sidebar Dark Background */
    [data-testid="stSidebar"] {
        background-color: #202123;
    }
    
    /* Sidebar Text Colors */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {
        color: #ECECF1 !important;
    }
    
    /* Main Canvas Light Background */
    .main .block-container {
        background-color: #FFFFFF;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Typography - Sans-serif, high line-height */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        line-height: 1.6;
    }
    
    /* Primary Button - Black/Dark */
    .stButton > button[kind="primary"] {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 0.5rem;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: background-color 0.2s;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #333333 !important;
    }
    
    /* Navigation Buttons - Clean Style */
    [data-testid="stSidebar"] .stButton > button {
        background-color: transparent !important;
        color: #ECECF1 !important;
        border: none !important;
        text-align: left !important;
        padding: 0.75rem 1rem !important;
        width: 100% !important;
        box-shadow: none !important;
        border-radius: 0.5rem;
        margin: 0.25rem 0;
    }
    
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(255, 255, 255, 0.1) !important;
    }
    
    /* Active Navigation Item */
    .nav-active {
        background-color: rgba(255, 255, 255, 0.15) !important;
        font-weight: 600 !important;
    }
    
    /* Remove default Streamlit borders */
    .stDataFrame {
        border: none !important;
    }
    
    /* KPI Cards Styling */
    .kpi-card {
        background-color: #FFFFFF;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        border: 1px solid #E5E7EB;
    }
    
    /* Color Utilities */
    .text-profit {
        color: #EF4444 !important;
    }
    
    .text-loss {
        color: #10A37F !important;
    }
    
    .text-warning {
        color: #F59E0B !important;
    }
    
    .bg-warning {
        background-color: #FEF3C7 !important;
    }
    
    /* Hide Deploy button and more options menu (top-right) */
    [data-testid="stToolbar"] {
        display: none !important;
    }
    
    /* Hide the hamburger menu button if present */
    [data-testid="stDecoration"] {
        display: none !important;
    }
    
    /* Ensure main content starts at top */
    .main .block-container {
        padding-top: 1rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

from page_modules import render_dashboard_page, render_hunter_page, render_portfolio_page, render_lab_page

# 初始化 session state
if "current_page" not in st.session_state:
    st.session_state.current_page = "驾驶舱 (Dashboard)"
if "portfolio_positions" not in st.session_state:
    st.session_state.portfolio_positions = []

# ========== 侧边栏 ==========
with st.sidebar:
    st.title("DAAS Alpha")
    st.caption("v1.3 Pro")
    st.markdown("---")
    
    # 主要操作按钮
    if st.button("新建扫描 (New Scan)", type="primary", use_container_width=True):
        st.session_state.current_page = "猎场 (Hunter)"
        st.rerun()
    
    st.markdown("---")
    
    # 导航菜单
    pages = [
        "驾驶舱 (Dashboard)",
        "猎场 (Hunter)",
        "模拟盘 (Portfolio)",
        "实验室 (Lab)"
    ]
    
    current_page = st.session_state.current_page
    
    for page_name in pages:
        is_active = (current_page == page_name)
        
        if is_active:
            st.markdown(f"""
                <div class="nav-active" style="
                    padding: 0.75rem 1rem;
                    margin: 0.25rem 0;
                    border-radius: 0.5rem;
                ">{page_name}</div>
            """, unsafe_allow_html=True)
        else:
            if st.button(page_name, key=f"nav_{page_name}", use_container_width=True):
                st.session_state.current_page = page_name
                st.rerun()
    
    st.markdown("---")
    
    # 系统设置
    with st.expander("系统设置"):
        tushare_token = st.text_input(
            "Tushare Token",
            value=os.getenv("TUSHARE_TOKEN", ""),
            type="password",
            help="输入您的 Tushare Pro Token"
        )
        if tushare_token and tushare_token != os.getenv("TUSHARE_TOKEN"):
            st.info("Token 已更新（需要重启应用生效）")

# ========== 主内容区 ==========
page = st.session_state.current_page

if page == "驾驶舱 (Dashboard)":
    render_dashboard_page()
elif page == "猎场 (Hunter)":
    render_hunter_page()
elif page == "模拟盘 (Portfolio)":
    render_portfolio_page()
elif page == "实验室 (Lab)":
    render_lab_page()
