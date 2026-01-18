"""
Reporter Module - 报告生成器
生成每日分析报告的 Markdown 文件
"""

import pandas as pd
from datetime import datetime
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """报告生成器类"""
    
    def __init__(self, output_dir='data/output'):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"报告输出目录: {self.output_dir}")
    
    def generate_report(self, anchor_pool, notice_results, trade_date):
        """
        生成分析报告
        
        Args:
            anchor_pool: 白名单股票池 DataFrame
            notice_results: 公告监控结果列表
            trade_date: 交易日期（格式：YYYY-MM-DD 或 YYYYMMDD）
            
        Returns:
            str: 生成的报告文件路径
        """
        logger.info(f"开始生成报告: 白名单 {len(anchor_pool)} 只股票, 异动公告 {len(notice_results)} 条")
        
        # 格式化日期
        if len(trade_date) == 8:  # YYYYMMDD
            date_obj = datetime.strptime(trade_date, '%Y%m%d')
            date_str = date_obj.strftime('%Y-%m-%d')
        else:
            date_str = trade_date
            date_obj = datetime.strptime(trade_date, '%Y-%m-%d')
        
        # 生成报告内容
        report_content = []
        
        # Title
        stock_count = len(anchor_pool)
        report_content.append(f"# {date_str} 分析报告 - 白名单股票数量: {stock_count}\n")
        report_content.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_content.append("---\n")
        
        # Section 1: 今日高安全垫白名单
        report_content.append("## 今日高安全垫白名单\n")
        report_content.append("### Top 20 (按 ROE 排序)\n")
        
        if not anchor_pool.empty:
            # 取前20只股票
            top_20 = anchor_pool.head(20).copy()
            
            # 格式化数值
            top_20['pe_ttm'] = top_20['pe_ttm'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            top_20['pb'] = top_20['pb'].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
            top_20['roe'] = top_20['roe'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
            top_20['dividend_yield'] = top_20['dividend_yield'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
            top_20['total_market_cap'] = top_20['total_market_cap'].apply(
                lambda x: f"{x/10000:.2f}亿" if pd.notna(x) else "N/A"
            )
            
            # 生成表格
            report_content.append("| 股票代码 | 股票名称 | 行业 | PE_TTM | PB | ROE | 股息率 | 总市值 |")
            report_content.append("|---------|---------|------|--------|----|-----|--------|--------|")
            
            for _, row in top_20.iterrows():
                report_content.append(
                    f"| {row['ts_code']} | {row['name']} | {row['industry'] if pd.notna(row['industry']) else 'N/A'} | "
                    f"{row['pe_ttm']} | {row['pb']} | {row['roe']} | {row['dividend_yield']} | {row['total_market_cap']} |"
                )
        else:
            report_content.append("暂无符合条件的股票。\n")
        
        report_content.append("\n")
        
        # Section 2: 重要异动公告
        report_content.append("## 重要异动公告\n")
        
        if notice_results:
            # 按情感分类
            positive_notices = [n for n in notice_results if n['sentiment'] == 'Positive']
            negative_notices = [n for n in notice_results if n['sentiment'] == 'Negative']
            
            # 正面公告
            if positive_notices:
                report_content.append("### 利好公告 (Positive)\n")
                for notice in positive_notices:
                    keyword = notice['matched_keyword']
                    title = notice['title'].replace(keyword, f"**{keyword}**")  # 高亮关键词
                    report_content.append(
                        f"- **{notice['ts_code']}** ({notice['notice_date']}): {title}\n"
                    )
                report_content.append("\n")
            
            # 负面公告
            if negative_notices:
                report_content.append("### 利空公告 (Negative)\n")
                for notice in negative_notices:
                    keyword = notice['matched_keyword']
                    title = notice['title'].replace(keyword, f"**{keyword}**")  # 高亮关键词
                    report_content.append(
                        f"- **{notice['ts_code']}** ({notice['notice_date']}): {title}\n"
                    )
                report_content.append("\n")
            
            if not positive_notices and not negative_notices:
                report_content.append("过去3天内未发现重要异动公告。\n")
        else:
            report_content.append("过去3天内未发现重要异动公告。\n")
        
        # 写入文件
        filename = f"{date_obj.strftime('%Y-%m-%d')}_Analysis_Report.md"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_content))
        
        logger.info(f"报告生成成功: {filepath}")
        return str(filepath)
