"""
Hunter Page - 猎场
The Feed: High-signal stock selection
"""

import pandas as pd
import streamlit as st
from page_modules.mock_data import generate_stock_results


def render_hunter_page():
    """渲染Hunter页面"""
    st.header("猎场 (Hunter)")
    st.markdown("基于 Alpha Trident 策略的智能选股系统")
    
    # 输入区域（可折叠）
    with st.expander("筛选条件", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            rps_threshold = st.slider(
                "RPS 阈值",
                min_value=80,
                max_value=100,
                value=85,
                step=1,
                help="相对强度百分比阈值"
            )
        
        with col2:
            volume_ratio = st.slider(
                "量比",
                min_value=0.0,
                max_value=10.0,
                value=1.5,
                step=0.1,
                help="成交量比率阈值"
            )
    
    # 生成模拟数据
    if "hunter_results" not in st.session_state:
        st.session_state.hunter_results = generate_stock_results(12)
    
    # 应用筛选（模拟）
    filtered_df = st.session_state.hunter_results[
        (st.session_state.hunter_results['rps_60'] >= rps_threshold) &
        (st.session_state.hunter_results['vol_ratio_5'] >= volume_ratio)
    ].copy()
    
    if filtered_df.empty:
        st.info("暂无符合条件的股票，请调整筛选条件")
        return
    
    st.markdown("---")
    st.subheader(f"筛选结果 ({len(filtered_df)} 只)")
    
    # 准备显示数据
    display_df = pd.DataFrame()
    display_df["代码"] = filtered_df["ts_code"]
    display_df["名称"] = filtered_df["name"]
    display_df["价格"] = filtered_df["close"]
    display_df["RPS"] = filtered_df["rps_60"]
    display_df["量比"] = filtered_df["vol_ratio_5"]
    display_df["AI分析"] = filtered_df["ai_analysis"]
    
    # 使用 column_config 配置表格
    column_config = {
        "代码": st.column_config.TextColumn(
            "代码",
            width="small"
        ),
        "名称": st.column_config.TextColumn(
            "名称",
            width="medium"
        ),
        "价格": st.column_config.NumberColumn(
            "价格",
            format="%.2f",
            width="small"
        ),
        "RPS": st.column_config.ProgressColumn(
            "RPS",
            min_value=0,
            max_value=100,
            format="%d",
            width="medium"
        ),
        "量比": st.column_config.NumberColumn(
            "量比",
            format="%.2f",
            width="small"
        ),
        "AI分析": st.column_config.TextColumn(
            "AI分析",
            width="large"
        )
    }
    
    # 显示表格
    edited_df = st.dataframe(
        display_df,
        column_config=column_config,
        use_container_width=True,
        hide_index=True
    )
    
    # 添加操作列（使用按钮）
    st.markdown("---")
    st.subheader("操作")
    
    if st.button("加入组合", type="primary", use_container_width=True):
        st.info("功能开发中：将选中的股票加入模拟组合")
