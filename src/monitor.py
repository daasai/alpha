"""
Monitor Module - "事件狙击手" (The Shield)
公告异动监控：针对白名单股票进行公告关键词匹配
"""

import pandas as pd
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


class AnnouncementMonitor:
    """公告监控类"""
    
    def __init__(self, keywords_path='config/keywords.yaml'):
        """
        初始化监控器，加载关键词配置
        
        Args:
            keywords_path: 关键词配置文件路径
        """
        self.keywords = self._load_keywords(keywords_path)
        self.positive_keywords = self.keywords['positive']
        self.negative_keywords = self.keywords['negative']
    
    def _load_keywords(self, keywords_path):
        """加载关键词配置"""
        keywords_file = Path(keywords_path)
        if not keywords_file.exists():
            logger.error(f"关键词文件不存在: {keywords_path}")
            raise FileNotFoundError(f"Keywords file not found: {keywords_path}")
        
        with open(keywords_file, 'r', encoding='utf-8') as f:
            keywords = yaml.safe_load(f)
        logger.debug(f"关键词加载成功: 正面 {len(keywords.get('positive', []))} 个, 负面 {len(keywords.get('negative', []))} 个")
        return keywords
    
    def analyze_notices(self, notices_df, lookback_days=3):
        """
        分析公告，进行关键词匹配
        
        Args:
            notices_df: 公告数据 DataFrame，包含 ts_code, ann_date, title
            lookback_days: 回溯天数（默认3天）
            
        Returns:
            list: 匹配结果列表，每个元素包含：
                - ts_code: 股票代码
                - notice_date: 公告日期
                - title: 公告标题
                - matched_keyword: 命中的关键词
                - sentiment: 情感标签 (Positive/Negative)
        """
        if notices_df.empty:
            logger.info("公告数据为空，跳过分析")
            return []
        
        logger.info(f"开始分析公告: 共 {len(notices_df)} 条公告，回溯 {lookback_days} 天")
        results = []
        
        # 确保日期格式正确
        notices_df['ann_date'] = pd.to_datetime(notices_df['ann_date'], format='%Y%m%d', errors='coerce')
        
        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # 过滤最近 lookback_days 天的公告
        recent_notices = notices_df[notices_df['ann_date'] >= cutoff_date].copy()
        
        if recent_notices.empty:
            logger.info(f"最近 {lookback_days} 天内无公告")
            return []
        
        logger.debug(f"过滤后公告数: {len(recent_notices)} 条")
        
        # 遍历每条公告进行关键词匹配
        for _, notice in recent_notices.iterrows():
            title = str(notice['title']) if pd.notna(notice['title']) else ''
            ts_code = notice['ts_code']
            notice_date = notice['ann_date']
            
            # 检查正面关键词
            for keyword in self.positive_keywords:
                if keyword in title:
                    results.append({
                        'ts_code': ts_code,
                        'notice_date': notice_date.strftime('%Y-%m-%d'),
                        'title': title,
                        'matched_keyword': keyword,
                        'sentiment': 'Positive'
                    })
                    break  # 每个公告只匹配第一个关键词
            
            # 检查负面关键词（如果还没匹配到正面关键词）
            if not any(r['ts_code'] == ts_code and r['notice_date'] == notice_date.strftime('%Y-%m-%d') 
                      for r in results):
                for keyword in self.negative_keywords:
                    if keyword in title:
                        results.append({
                            'ts_code': ts_code,
                            'notice_date': notice_date.strftime('%Y-%m-%d'),
                            'title': title,
                            'matched_keyword': keyword,
                            'sentiment': 'Negative'
                        })
                        break
        
        positive_count = sum(1 for r in results if r['sentiment'] == 'Positive')
        negative_count = sum(1 for r in results if r['sentiment'] == 'Negative')
        logger.info(f"关键词匹配完成: 正面 {positive_count} 条, 负面 {negative_count} 条, 总计 {len(results)} 条")
        return results
