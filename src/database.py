"""
Database Module - DAAS Alpha 预测存储
SQLite + SQLAlchemy：predictions 表及 save/update/get 方法
"""

from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .logging_config import get_logger

logger = get_logger(__name__)

# 项目根目录、data 目录、DB 路径
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_DB_PATH = _DATA_DIR / "daas.db"

# 确保 data 目录存在
_DATA_DIR.mkdir(parents=True, exist_ok=True)

from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime

Base = declarative_base()


class Prediction(Base):
    """预测记录表"""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), nullable=False)
    ts_code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    ai_score = Column(Integer, nullable=False)
    ai_reason = Column(String(500), nullable=False)
    actual_chg = Column(Float, nullable=True)
    strategy_tag = Column(String(20), nullable=True)  # v1.1: 策略标签（防守/进攻）
    suggested_shares = Column(Integer, nullable=True)  # v1.1: 建议持仓数量（基于ATR）


class AnalysisTask(Base):
    """分析任务表"""
    __tablename__ = "analysis_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(20), nullable=False, unique=True)  # 格式：YYYYMMDD-N
    trade_date = Column(String(8), nullable=False)
    task_number = Column(Integer, nullable=False)  # 同一交易日的第N次分析
    status = Column(String(20), nullable=False, default='pending')  # pending/running/completed/failed
    risk_budget = Column(Float, nullable=False)
    current_step = Column(String(20), nullable=True)  # fetching/screening/ai_analysis/calculating/completed
    progress_message = Column(String(500), nullable=True)
    result_data = Column(Text, nullable=True)  # JSON格式存储DataFrame
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime, nullable=True)


_engine = create_engine(
    f"sqlite:///{_DB_PATH}",
    connect_args={"check_same_thread": False},
)
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)

# 首次导入时建表
Base.metadata.create_all(_engine)

# v1.1: 数据库迁移 - 为新字段添加列（如果不存在）
def _migrate_database():
    """迁移数据库，添加v1.1新字段"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(_engine)
        if inspector.has_table('predictions'):
            columns = [col['name'] for col in inspector.get_columns('predictions')]
            
            with _engine.begin() as conn:  # 使用begin()自动提交事务
                if 'strategy_tag' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE predictions ADD COLUMN strategy_tag VARCHAR(20)"))
                        logger.info("数据库迁移: 添加 strategy_tag 字段")
                    except Exception as e:
                        logger.warning(f"数据库迁移 strategy_tag 失败: {e}")
                
                if 'suggested_shares' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE predictions ADD COLUMN suggested_shares INTEGER"))
                        logger.info("数据库迁移: 添加 suggested_shares 字段")
                    except Exception as e:
                        logger.warning(f"数据库迁移 suggested_shares 失败: {e}")
    except Exception as e:
        logger.debug(f"数据库迁移检查: {e}（可能是首次创建，将自动建表）")

# 执行迁移
try:
    _migrate_database()
except Exception as e:
    logger.warning(f"数据库迁移检查失败: {e}，将在首次使用时自动创建")


@contextmanager
def _session_scope():
    s = _SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def save_daily_predictions(list_of_dicts: List[Dict[str, Any]]) -> None:
    """
    批量保存每日预测。每条 dict 需含：trade_date, ts_code, name, ai_score, ai_reason；
    可选：strategy_tag, suggested_shares（v1.1新增）；
    actual_chg 默认为 None。
    """
    if not list_of_dicts:
        logger.warning("save_daily_predictions: 传入列表为空，跳过")
        return
    with _session_scope() as s:
        for d in list_of_dicts:
            r = Prediction(
                trade_date=str(d["trade_date"]),
                ts_code=str(d["ts_code"]),
                name=str(d["name"]),
                ai_score=int(d["ai_score"]),
                ai_reason=str(d.get("ai_reason", "")),
                actual_chg=None,
                strategy_tag=str(d.get("strategy_tag", "")) if d.get("strategy_tag") else None,
                suggested_shares=int(d["suggested_shares"]) if d.get("suggested_shares") is not None else None,
            )
            s.add(r)
    logger.info(f"save_daily_predictions: 已写入 {len(list_of_dicts)} 条")


def update_actual_performance(trade_date: str, ts_code: str, chg: float) -> None:
    """按 trade_date + ts_code 更新 actual_chg。"""
    with _session_scope() as s:
        n = s.query(Prediction).filter(
            Prediction.trade_date == str(trade_date),
            Prediction.ts_code == str(ts_code),
        ).update({"actual_chg": float(chg)})
        if n == 0:
            logger.debug(f"update_actual_performance: 未找到 trade_date={trade_date} ts_code={ts_code}")


def get_pending_predictions() -> List[Dict[str, Any]]:
    """返回 actual_chg 为 NULL 的记录，仅 trade_date、ts_code。"""
    with _session_scope() as s:
        rows = s.query(Prediction.trade_date, Prediction.ts_code).filter(
            Prediction.actual_chg.is_(None)
        ).all()
    return [{"trade_date": r[0], "ts_code": r[1]} for r in rows]


def get_verified_predictions() -> List[Dict[str, Any]]:
    """返回 actual_chg 非 NULL 的记录，含 trade_date, ts_code, name, ai_score, ai_reason, actual_chg, strategy_tag, suggested_shares。"""
    with _session_scope() as s:
        rows = s.query(
            Prediction.trade_date,
            Prediction.ts_code,
            Prediction.name,
            Prediction.ai_score,
            Prediction.ai_reason,
            Prediction.actual_chg,
            Prediction.strategy_tag,
            Prediction.suggested_shares,
        ).filter(Prediction.actual_chg.isnot(None)).all()
    return [
        {
            "trade_date": r[0],
            "ts_code": r[1],
            "name": r[2],
            "ai_score": r[3],
            "ai_reason": r[4],
            "actual_chg": r[5],
            "strategy_tag": r[6],
            "suggested_shares": r[7],
        }
        for r in rows
    ]


# ========== 分析任务管理方法 ==========

def create_analysis_task(trade_date: str, risk_budget: float) -> str:
    """
    创建新的分析任务，生成任务ID（格式：YYYYMMDD-N）。
    
    Args:
        trade_date: 交易日期（YYYYMMDD格式）
        risk_budget: 风险预算
        
    Returns:
        任务ID（格式：YYYYMMDD-N）
    """
    with _session_scope() as s:
        # 查询同一交易日的最大任务编号
        max_task = s.query(AnalysisTask.task_number).filter(
            AnalysisTask.trade_date == trade_date
        ).order_by(AnalysisTask.task_number.desc()).first()
        
        # 计算新的任务编号
        task_number = 1 if max_task is None else max_task[0] + 1
        
        # 生成任务ID
        task_id = f"{trade_date}-{task_number}"
        
        # 创建任务记录
        task = AnalysisTask(
            task_id=task_id,
            trade_date=trade_date,
            task_number=task_number,
            status='pending',
            risk_budget=risk_budget,
            current_step=None,
            progress_message=None,
            result_data=None,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        s.add(task)
        
        logger.info(f"创建分析任务: {task_id}")
        return task_id


def update_task_status(
    task_id: str,
    status: str = None,
    current_step: str = None,
    progress_message: str = None,
    error_message: str = None
) -> None:
    """
    更新任务状态和进度。
    
    Args:
        task_id: 任务ID
        status: 任务状态（pending/running/completed/failed）
        current_step: 当前执行步骤
        progress_message: 进度消息
        error_message: 错误信息
    """
    with _session_scope() as s:
        task = s.query(AnalysisTask).filter(AnalysisTask.task_id == task_id).first()
        if not task:
            logger.warning(f"update_task_status: 未找到任务 {task_id}")
            return
        
        if status is not None:
            task.status = status
        if current_step is not None:
            task.current_step = current_step
        if progress_message is not None:
            task.progress_message = progress_message
        if error_message is not None:
            task.error_message = error_message
        
        task.updated_at = datetime.now()
        
        if status == 'completed':
            task.completed_at = datetime.now()
        elif status == 'failed':
            task.completed_at = datetime.now()
        
        logger.debug(f"更新任务状态: {task_id}, status={status}, step={current_step}")


def save_task_result(task_id: str, df) -> None:
    """
    保存任务结果（DataFrame转JSON）。
    
    Args:
        task_id: 任务ID
        df: 分析结果DataFrame
    """
    import pandas as pd
    import json
    
    try:
        # 将DataFrame转为JSON
        result_json = df.to_json(orient='records', date_format='iso', force_ascii=False)
        
        with _session_scope() as s:
            task = s.query(AnalysisTask).filter(AnalysisTask.task_id == task_id).first()
            if not task:
                logger.warning(f"save_task_result: 未找到任务 {task_id}")
                return
            
            task.result_data = result_json
            task.updated_at = datetime.now()
            
            logger.info(f"保存任务结果: {task_id}, 共 {len(df)} 条记录")
    except Exception as e:
        logger.error(f"save_task_result 失败: {e}")
        raise


def get_task_by_id(task_id: str) -> Dict[str, Any]:
    """
    根据任务ID获取任务信息。
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务信息字典，如果不存在返回None
    """
    with _session_scope() as s:
        task = s.query(AnalysisTask).filter(AnalysisTask.task_id == task_id).first()
        if not task:
            return None
        
        return {
            "id": task.id,
            "task_id": task.task_id,
            "trade_date": task.trade_date,
            "task_number": task.task_number,
            "status": task.status,
            "risk_budget": task.risk_budget,
            "current_step": task.current_step,
            "progress_message": task.progress_message,
            "result_data": task.result_data,
            "error_message": task.error_message,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
        }


def get_latest_task(trade_date: str = None) -> Dict[str, Any]:
    """
    获取最近一次任务（可指定交易日）。
    
    Args:
        trade_date: 交易日期（可选），如果指定则返回该交易日的最新任务
        
    Returns:
        任务信息字典，如果不存在返回None
    """
    with _session_scope() as s:
        query = s.query(AnalysisTask)
        if trade_date:
            query = query.filter(AnalysisTask.trade_date == trade_date)
        
        task = query.order_by(AnalysisTask.created_at.desc()).first()
        if not task:
            return None
        
        return {
            "id": task.id,
            "task_id": task.task_id,
            "trade_date": task.trade_date,
            "task_number": task.task_number,
            "status": task.status,
            "risk_budget": task.risk_budget,
            "current_step": task.current_step,
            "progress_message": task.progress_message,
            "result_data": task.result_data,
            "error_message": task.error_message,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
        }


def get_running_task() -> Dict[str, Any]:
    """
    获取当前运行中的任务（status='running'）。
    
    Returns:
        任务信息字典，如果不存在返回None
    """
    with _session_scope() as s:
        task = s.query(AnalysisTask).filter(
            AnalysisTask.status == 'running'
        ).order_by(AnalysisTask.created_at.desc()).first()
        
        if not task:
            return None
        
        return {
            "id": task.id,
            "task_id": task.task_id,
            "trade_date": task.trade_date,
            "task_number": task.task_number,
            "status": task.status,
            "risk_budget": task.risk_budget,
            "current_step": task.current_step,
            "progress_message": task.progress_message,
            "result_data": task.result_data,
            "error_message": task.error_message,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "completed_at": task.completed_at,
        }


def list_tasks_by_trade_date(trade_date: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    列出指定交易日的所有任务。
    
    Args:
        trade_date: 交易日期
        limit: 返回数量限制
        
    Returns:
        任务信息列表
    """
    with _session_scope() as s:
        tasks = s.query(AnalysisTask).filter(
            AnalysisTask.trade_date == trade_date
        ).order_by(AnalysisTask.task_number.desc()).limit(limit).all()
        
        return [
            {
                "id": task.id,
                "task_id": task.task_id,
                "trade_date": task.trade_date,
                "task_number": task.task_number,
                "status": task.status,
                "risk_budget": task.risk_budget,
                "current_step": task.current_step,
                "progress_message": task.progress_message,
                "result_data": task.result_data,
                "error_message": task.error_message,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "completed_at": task.completed_at,
            }
            for task in tasks
        ]


def load_task_result(task_id: str):
    """
    加载任务结果，将JSON转为DataFrame。
    
    Args:
        task_id: 任务ID
        
    Returns:
        DataFrame，如果任务不存在或没有结果返回None
    """
    import pandas as pd
    import json
    
    task = get_task_by_id(task_id)
    if not task or not task.get("result_data"):
        return None
    
    try:
        result_json = task["result_data"]
        df = pd.read_json(result_json, orient='records')
        logger.info(f"加载任务结果: {task_id}, 共 {len(df)} 条记录")
        return df
    except Exception as e:
        logger.error(f"load_task_result 失败: {e}")
        return None
