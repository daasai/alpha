"""
Truth Page - 复盘验证页面
"""

import pandas as pd
import streamlit as st
import os
from src.services import TruthService
from src.logging_config import get_logger

logger = get_logger(__name__)


def render_truth_page():
    """渲染Truth页面"""
    st.header("📈 复盘验证 (Truth)")
    st.markdown("追踪历史预测的实际表现")
    
    truth_service = TruthService()
    
    if st.button("🔄 更新最新价格", use_container_width=True):
        logger.info("Truth 更新开始")
        
        # 检查 Token
        if not os.getenv("TUSHARE_TOKEN"):
            st.error("❌ 请先在侧边栏设置 Tushare Token")
            st.stop()
        
        try:
            with st.status("🔄 更新价格中...", expanded=True) as status:
                result = truth_service.update_prices()
                
                if not result.success:
                    st.error(f"❌ {result.error}")
                    st.stop()
                
                if result.total_count == 0:
                    st.info("ℹ️ 数据库中没有预测记录")
                    st.stop()
                
                st.write(f"找到 {result.total_count} 条预测记录")
                st.write(f"已更新 {result.updated_count} 条记录")
                
                logger.info("Truth 更新完成: 更新 %d 条", result.updated_count)
                status.update(label="✅ 更新完成", state="complete")
                st.success(f"✅ 已更新 {result.updated_count} 条记录")
        
        except Exception as e:
            logger.exception("Truth 更新异常")
            st.error(f"❌ 更新过程出错: {e}")
    
    # 显示验证结果
    st.markdown("---")
    st.subheader("📊 验证结果")
    
    df = truth_service.get_verification_data()
    if not df.empty:
        # 计算胜率
        win_rate_info = truth_service.calculate_win_rate(df)
        if win_rate_info['total_count'] > 0:
            st.metric(
                "历史胜率",
                f"{win_rate_info['win_rate']:.2f}%",
                f"{win_rate_info['win_count']}/{win_rate_info['total_count']}"
            )
        
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
