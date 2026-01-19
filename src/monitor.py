"""
Monitor Module - "事件狙击手" (The Shield)
公告异动监控：针对白名单股票进行公告关键词匹配

analyze_sentiment：从 get_notices 取得 title、title_ch、column_names，
prompt 使用「公告类型：{column_names}；标题：{title or title_ch}」。不包含 content；正文须经 art_code 详情页获取。
"""

import json
import os
import re
import pandas as pd
import yaml
from datetime import datetime, timedelta
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


def _load_ai_scoring_config(keywords_path='config/keywords.yaml'):
    """
    加载AI评分配置
    
    Args:
        keywords_path: 配置文件路径
        
    Returns:
        str: 系统提示词，如果配置不存在则返回默认值
    """
    default_prompt = 'Score the announcement impact on stock price from -10 to 10. Reply with only a JSON: {"score": int, "reason": "..."}.'
    
    try:
        config_file = Path(keywords_path)
        if not config_file.exists():
            logger.warning(f"配置文件不存在: {keywords_path}，使用默认提示词")
            return default_prompt
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        ai_scoring = config.get('ai_scoring', {})
        system_prompt = ai_scoring.get('system_prompt', '').strip()
        
        if system_prompt:
            logger.debug("从配置文件加载AI评分系统提示词")
            return system_prompt
        else:
            logger.warning("配置文件中未找到ai_scoring.system_prompt，使用默认提示词")
            return default_prompt
    except Exception as e:
        logger.warning(f"加载AI评分配置失败: {e}，使用默认提示词")
        return default_prompt


def _parse_ai_response(text: str):
    """
    解析AI响应，支持新旧两种格式
    
    Args:
        text: AI返回的JSON文本
        
    Returns:
        tuple: (score: int, reason: str) 或 (None, None) 如果解析失败
    """
    try:
        obj = json.loads(text)
        
        # 新格式：数组格式 [{"id": int, "score": int, "reason": "..."}]
        if isinstance(obj, list):
            if len(obj) == 0:
                logger.warning("AI返回空数组")
                return None, None
            # 取第一个元素
            item = obj[0]
            if not isinstance(item, dict):
                logger.warning(f"数组元素不是对象: {type(item)}")
                return None, None
            score = int(item.get("score", 0))
            reason = str(item.get("reason", ""))[:500]
            # id字段可以忽略，但可以用于验证
            item_id = item.get("id", 0)
            logger.debug(f"解析数组格式响应: id={item_id}, score={score}")
            return score, reason
        
        # 旧格式：单个对象 {"score": int, "reason": "..."}
        elif isinstance(obj, dict):
            score = int(obj.get("score", 0))
            reason = str(obj.get("reason", ""))[:500]
            logger.debug(f"解析对象格式响应: score={score}")
            return score, reason
        
        else:
            logger.warning(f"未知的响应格式: {type(obj)}")
            return None, None
            
    except json.JSONDecodeError as e:
        logger.warning(f"JSON解析失败: {e}")
        return None, None
    except (ValueError, KeyError, TypeError) as e:
        logger.warning(f"解析响应字段失败: {e}")
        return None, None


def analyze_sentiment(df: pd.DataFrame, data_provider=None) -> pd.DataFrame:
    """
    对 run_screening 的 df 逐行：取公告（get_notices），无则用「无最新公告」；
    调用 LLM 打分 -10..10，仅返回 JSON {score, reason}；写回 ai_score, ai_reason。
    prompt 使用「公告类型：{column_names}；标题：{title or title_ch}」。
    
    性能优化：批量获取公告 + 并发AI评分
    """
    if df.empty:
        return df
    if data_provider is None:
        from .data_provider import DataProvider
        data_provider = DataProvider()
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY 未设置，请在 .env 中配置")
    from openai import OpenAI
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from tqdm import tqdm
    
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE") or None,
    )
    # 支持通过环境变量配置模型名称，默认使用 gpt-3.5-turbo
    model_name = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    logger.info(f"使用AI模型: {model_name}, API Base: {os.getenv('OPENAI_API_BASE', '默认(OpenAI官方)')}")
    
    # 从配置文件加载系统提示词
    sys_prompt = _load_ai_scoring_config()
    
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")
    
    # 优化1：批量获取所有股票的公告
    logger.info(f"批量获取 {len(df)} 只股票的公告...")
    try:
        all_notices = data_provider.get_notices(df["ts_code"].tolist(), start_date, end_date)
        # 构建公告查找字典：{ts_code: {title, column_names}}
        notices_dict = {}
        if not all_notices.empty:
            for _, notice_row in all_notices.iterrows():
                ts_code = notice_row.get("ts_code")
                if ts_code:
                    title = str(notice_row.get("title") or notice_row.get("title_ch") or "无最新公告").strip() or "无最新公告"
                    column_names = str(notice_row.get("column_names") or "").strip()
                    notices_dict[ts_code] = {"title": title, "column_names": column_names}
        logger.info(f"成功获取 {len(notices_dict)} 只股票的公告")
    except Exception as e:
        logger.warning(f"批量获取公告失败: {e}，将使用逐个获取方式")
        notices_dict = {}
    
    # 优化2：并发AI评分
    def score_single_stock(args):
        """单个股票的AI评分函数"""
        idx, row, notices_dict, client, model_name, sys_prompt = args
        ts_code = row["ts_code"]
        name = row.get("name", "")
        
        # 从公告字典中获取公告信息
        title, column_names = "无最新公告", ""
        if ts_code in notices_dict:
            notice_info = notices_dict[ts_code]
            title = notice_info.get("title", "无最新公告")
            column_names = notice_info.get("column_names", "")
        
        user = f"Stock: {name}, ts_code: {ts_code}. 公告类型：{column_names}；标题：{title}."
        text = None
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user}],
            )
            text = (resp.choices[0].message.content or "").strip()
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```\s*$", "", text)
            
            # 使用新的解析函数，支持数组和对象两种格式
            score, reason = _parse_ai_response(text)
            
            if score is not None and reason is not None:
                return (idx, score, reason, None)
            else:
                logger.warning(f"AI响应解析失败 {ts_code}，使用默认值")
                return (idx, 0, "响应解析失败", None)
                
        except json.JSONDecodeError as e:
            response_preview = text[:200] if text else "N/A"
            logger.warning(f"LLM {ts_code} JSON解析失败: {e}, 响应内容: {response_preview}")
            return (idx, 0, "JSON解析错误", None)
        except Exception as e:
            error_msg = str(e)
            # 提取更详细的错误信息
            if hasattr(e, 'response') and hasattr(e.response, 'json'):
                try:
                    error_detail = e.response.json()
                    error_msg = f"{error_msg} - {error_detail}"
                except:
                    pass
            logger.error(f"LLM {ts_code} 调用失败: {error_msg}")
            return (idx, 0, f"API错误: {error_msg[:100]}", str(e))
    
    # 准备参数列表
    score_args = [
        (idx, row, notices_dict, client, model_name, sys_prompt)
        for idx, row in df.iterrows()
    ]
    
    # 使用线程池并发执行（5个并发，考虑API限流）
    scores_dict = {}
    reasons_dict = {}
    max_workers = 5
    
    logger.info(f"开始并发AI评分，共 {len(score_args)} 只股票，并发数: {max_workers}")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_idx = {
            executor.submit(score_single_stock, args): args[0]
            for args in score_args
        }
        
        # 使用tqdm显示进度
        with tqdm(total=len(score_args), desc="AI评分进度", unit="只", ncols=80) as pbar:
            for future in as_completed(future_to_idx):
                try:
                    idx, score, reason, error = future.result()
                    scores_dict[idx] = score
                    reasons_dict[idx] = reason
                    if error:
                        logger.debug(f"股票 {df.iloc[idx]['ts_code']} 评分完成（有错误）")
                    else:
                        logger.debug(f"AI评分成功 {df.iloc[idx]['ts_code']}: score={score}")
                except Exception as e:
                    idx = future_to_idx[future]
                    logger.error(f"AI评分任务异常 {df.iloc[idx]['ts_code']}: {e}")
                    scores_dict[idx] = 0
                    reasons_dict[idx] = f"任务异常: {str(e)[:100]}"
                finally:
                    pbar.update(1)
    
    # 按原始索引顺序构建结果
    scores = [scores_dict.get(idx, 0) for idx in range(len(df))]
    reasons = [reasons_dict.get(idx, "评分失败") for idx in range(len(df))]
    
    df = df.copy()
    df["ai_score"] = scores
    df["ai_reason"] = reasons
    logger.info(f"AI评分完成，共 {len(df)} 只股票")
    return df


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
            notices_df: 公告数据 DataFrame，需含 ts_code, ann_date, title；
                若有 title_ch、column_names（东方财富扩展字段）也可传入，title 为空时以 title_ch 作标题
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
            title = str(notice['title']) if pd.notna(notice.get('title')) else ''
            if not title and 'title_ch' in notice.index:
                t = notice.get('title_ch')
                title = str(t) if pd.notna(t) else ''
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
