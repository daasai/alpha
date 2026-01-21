"""
Database Module - DAAS Alpha 预测存储
SQLite + SQLAlchemy：predictions 表及 save/update/get 方法
"""

from pathlib import Path
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

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

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, UniqueConstraint, Boolean
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
    price_at_prediction = Column(Float, nullable=True)  # v1.2: 预测时的价格
    current_price = Column(Float, nullable=True)  # v1.2: 最新价格


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


class IndexConstituent(Base):
    """指数成分股缓存表"""
    __tablename__ = "index_constituents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    index_code = Column(String(20), nullable=False)  # 指数代码，如 '000852.SH'
    ts_code = Column(String(20), nullable=False)  # 成分股代码
    trade_date = Column(String(8), nullable=False)  # 生效日期（YYYYMMDD）
    weight = Column(Float, nullable=True)  # 权重（可选）
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class DailyHistoryCache(Base):
    """历史日线数据缓存表"""
    __tablename__ = "daily_history_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False)  # 股票代码
    trade_date = Column(String(8), nullable=False)  # 交易日期（YYYYMMDD）
    open = Column(Float, nullable=True)  # 开盘价
    high = Column(Float, nullable=True)  # 最高价
    low = Column(Float, nullable=True)  # 最低价
    close = Column(Float, nullable=True)  # 收盘价
    vol = Column(Float, nullable=True)  # 成交量
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class Account(Base):
    """账户表（单例）"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, default=1)  # 单例，固定为1
    total_asset = Column(Float, nullable=False, default=0.0)  # 总资产
    cash = Column(Float, nullable=False, default=0.0)  # 现金
    market_value = Column(Float, nullable=False, default=0.0)  # 市值
    frozen_cash = Column(Float, nullable=False, default=0.0)  # 冻结资金
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('id', name='uq_account_id'),  # 确保单例
    )


class Position(Base):
    """持仓表"""
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, unique=True)  # 股票代码，唯一约束
    name = Column(String(100), nullable=False)  # 股票名称
    total_vol = Column(Integer, nullable=False, default=0)  # 总持仓量
    avail_vol = Column(Integer, nullable=False, default=0)  # 可用持仓量（T+1）
    avg_price = Column(Float, nullable=False, default=0.0)  # 平均成本价
    current_price = Column(Float, nullable=True)  # 最新市价
    profit = Column(Float, nullable=False, default=0.0)  # 浮动盈亏
    profit_pct = Column(Float, nullable=False, default=0.0)  # 盈亏百分比
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class DailyNav(Base):
    """每日净值表"""
    __tablename__ = "daily_nav"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_date = Column(String(8), nullable=False)  # 交易日期（YYYYMMDD）
    total_asset = Column(Float, nullable=False)  # 总资产
    benchmark_val = Column(Float, nullable=True)  # 基准指数收盘价
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        UniqueConstraint('trade_date', name='uq_daily_nav_trade_date'),  # 确保每日只有一条记录
    )


class Order(Base):
    """订单表（不可变账本）"""
    __tablename__ = "orders"

    order_id = Column(String(36), primary_key=True)  # UUID
    trade_date = Column(String(8), nullable=False)  # 交易日期（YYYYMMDD）
    ts_code = Column(String(20), nullable=False)  # 股票代码
    action = Column(String(10), nullable=False)  # BUY/SELL
    price = Column(Float, nullable=False)  # 成交价格
    volume = Column(Integer, nullable=False)  # 成交数量
    fee = Column(Float, nullable=False, default=0.0)  # 手续费
    status = Column(String(20), nullable=False, default='FILLED')  # FILLED/CANCELLED
    strategy_tag = Column(String(20), nullable=True)  # 买入订单的策略标签
    reason = Column(String(200), nullable=True)  # 卖出订单的原因
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class ErrorLog(Base):
    """错误日志表"""
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    error_code = Column(String(50), nullable=False)  # 错误代码
    error_type = Column(String(100), nullable=False)  # 错误类型
    message = Column(Text, nullable=False)  # 错误消息
    context = Column(Text, nullable=True)  # 上下文信息（JSON格式）
    stack_trace = Column(Text, nullable=True)  # 堆栈跟踪
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class DailyTaskExecution(Base):
    """每日任务执行记录表"""
    __tablename__ = "daily_task_executions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(36), nullable=False, unique=True)  # UUID
    trade_date = Column(String(8), nullable=False)  # 交易日期 YYYYMMDD
    trigger_type = Column(String(20), nullable=False)  # SCHEDULED/MANUAL/API
    status = Column(String(20), nullable=False)  # PENDING/RUNNING/SUCCESS/FAILED/RETRYING
    is_duplicate = Column(Boolean, nullable=False, default=False)  # 是否为重复执行（幂等性标记）
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    steps_completed = Column(Text, nullable=True)  # JSON数组
    errors = Column(Text, nullable=True)  # JSON数组
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


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
                
                if 'price_at_prediction' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE predictions ADD COLUMN price_at_prediction FLOAT"))
                        logger.info("数据库迁移: 添加 price_at_prediction 字段")
                    except Exception as e:
                        logger.warning(f"数据库迁移 price_at_prediction 失败: {e}")
                
                if 'current_price' not in columns:
                    try:
                        conn.execute(text("ALTER TABLE predictions ADD COLUMN current_price FLOAT"))
                        logger.info("数据库迁移: 添加 current_price 字段")
                    except Exception as e:
                        logger.warning(f"数据库迁移 current_price 失败: {e}")
    except Exception as e:
        logger.debug(f"数据库迁移检查: {e}（可能是首次创建，将自动建表）")


# v1.3: 数据库迁移 - 组合管理模块（Account, Position, Order）
def _migrate_portfolio_models():
    """迁移数据库，创建组合管理相关表（Account, Position, Order）"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(_engine)
        
        # 移除旧的 portfolio_positions 表（如果存在）
        if inspector.has_table('portfolio_positions'):
            try:
                with _engine.begin() as conn:
                    conn.execute(text("DROP TABLE IF EXISTS portfolio_positions"))
                    logger.info("数据库迁移: 移除旧的 portfolio_positions 表")
            except Exception as e:
                logger.warning(f"移除旧表失败: {e}")
        
        # Account 表将在 Base.metadata.create_all 时自动创建
        # Position 表将在 Base.metadata.create_all 时自动创建
        # Order 表将在 Base.metadata.create_all 时自动创建
        
        logger.info("数据库迁移: 组合管理模型（Account, Position, Order）将在首次使用时自动创建")
    except Exception as e:
        logger.debug(f"数据库迁移检查: {e}（可能是首次创建，将自动建表）")


def _migrate_error_log_table():
    """迁移数据库，创建 ErrorLog 表（如果不存在）"""
    from sqlalchemy import inspect
    try:
        inspector = inspect(_engine)
        if not inspector.has_table('error_logs'):
            # 表不存在，Base.metadata.create_all 会自动创建
            logger.info("数据库迁移: ErrorLog 表将在首次使用时自动创建")
        else:
            logger.debug("数据库迁移: ErrorLog 表已存在")
    except Exception as e:
        logger.debug(f"数据库迁移检查: {e}（可能是首次创建，将自动建表）")


# 执行迁移
try:
    _migrate_database()
    _migrate_portfolio_models()
    _migrate_error_log_table()
except Exception as e:
    logger.warning(f"数据库迁移检查失败: {e}，将在首次使用时自动创建")

# 创建索引（如果表已存在）
def _create_indexes():
    """创建必要的索引"""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(_engine)
        if inspector.has_table('index_constituents'):
            with _engine.begin() as conn:
                # 检查索引是否已存在
                indexes = [idx['name'] for idx in inspector.get_indexes('index_constituents')]
                
                # 创建联合索引（index_code + trade_date）
                if 'idx_index_code_trade_date' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_index_code_trade_date ON index_constituents(index_code, trade_date)"
                        ))
                        logger.info("数据库迁移: 创建 index_constituents 联合索引")
                    except Exception as e:
                        logger.debug(f"创建联合索引失败（可能已存在）: {e}")
                
                # 创建 ts_code 索引
                if 'idx_ts_code' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_ts_code ON index_constituents(ts_code)"
                        ))
                        logger.info("数据库迁移: 创建 index_constituents ts_code 索引")
                    except Exception as e:
                        logger.debug(f"创建 ts_code 索引失败（可能已存在）: {e}")
        
        # 为 daily_history_cache 创建索引
        if inspector.has_table('daily_history_cache'):
            with _engine.begin() as conn:
                indexes = [idx['name'] for idx in inspector.get_indexes('daily_history_cache')]
                
                # 创建联合索引（ts_code + trade_date）- 最重要的查询索引
                if 'idx_daily_history_ts_code_trade_date' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_daily_history_ts_code_trade_date ON daily_history_cache(ts_code, trade_date)"
                        ))
                        logger.info("数据库迁移: 创建 daily_history_cache 联合索引")
                    except Exception as e:
                        logger.debug(f"创建 daily_history_cache 联合索引失败（可能已存在）: {e}")
                
                # 创建 trade_date 索引（用于日期范围查询）
                if 'idx_daily_history_trade_date' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_daily_history_trade_date ON daily_history_cache(trade_date)"
                        ))
                        logger.info("数据库迁移: 创建 daily_history_cache trade_date 索引")
                    except Exception as e:
                        logger.debug(f"创建 daily_history_cache trade_date 索引失败（可能已存在）: {e}")
        
        # 为 positions 创建索引
        if inspector.has_table('positions'):
            with _engine.begin() as conn:
                indexes = [idx['name'] for idx in inspector.get_indexes('positions')]
                
                # 创建 ts_code 索引（用于查询）
                if 'idx_position_ts_code' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_position_ts_code ON positions(ts_code)"
                        ))
                        logger.info("数据库迁移: 创建 positions ts_code 索引")
                    except Exception as e:
                        logger.debug(f"创建 positions ts_code 索引失败（可能已存在）: {e}")
        
        # 为 orders 创建索引
        if inspector.has_table('orders'):
            with _engine.begin() as conn:
                indexes = [idx['name'] for idx in inspector.get_indexes('orders')]
                
                # 创建 trade_date 索引（用于日期查询）
                if 'idx_order_trade_date' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_order_trade_date ON orders(trade_date)"
                        ))
                        logger.info("数据库迁移: 创建 orders trade_date 索引")
                    except Exception as e:
                        logger.debug(f"创建 orders trade_date 索引失败（可能已存在）: {e}")
                
                # 创建 ts_code 索引（用于股票查询）
                if 'idx_order_ts_code' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_order_ts_code ON orders(ts_code)"
                        ))
                        logger.info("数据库迁移: 创建 orders ts_code 索引")
                    except Exception as e:
                        logger.debug(f"创建 orders ts_code 索引失败（可能已存在）: {e}")
        
        # 为 error_logs 创建索引
        if inspector.has_table('error_logs'):
            with _engine.begin() as conn:
                indexes = [idx['name'] for idx in inspector.get_indexes('error_logs')]
                
                # 创建 error_code 索引（用于查询）
                if 'idx_error_code' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_error_code ON error_logs(error_code)"
                        ))
                        logger.info("数据库迁移: 创建 error_logs error_code 索引")
                    except Exception as e:
                        logger.debug(f"创建 error_logs error_code 索引失败（可能已存在）: {e}")
                
                # 创建 created_at 索引（用于时间范围查询）
                if 'idx_error_created_at' not in indexes:
                    try:
                        conn.execute(text(
                            "CREATE INDEX idx_error_created_at ON error_logs(created_at)"
                        ))
                        logger.info("数据库迁移: 创建 error_logs created_at 索引")
                    except Exception as e:
                        logger.debug(f"创建 error_logs created_at 索引失败（可能已存在）: {e}")
    except Exception as e:
        logger.debug(f"索引创建检查: {e}（可能是首次创建，将自动建表）")

# 执行索引创建
try:
    _create_indexes()
except Exception as e:
    logger.debug(f"索引创建检查失败: {e}")


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
    批量保存每日预测（支持幂等性）。
    每条 dict 需含：trade_date, ts_code, name, ai_score, ai_reason；
    可选：strategy_tag, suggested_shares（v1.1新增）；
    actual_chg 默认为 None。
    
    如果已存在相同 (trade_date, ts_code) 的记录，则更新；否则插入。
    """
    if not list_of_dicts:
        logger.warning("save_daily_predictions: 传入列表为空，跳过")
        return
    
    inserted_count = 0
    updated_count = 0
    
    with _session_scope() as s:
        for d in list_of_dicts:
            trade_date = str(d["trade_date"])
            ts_code = str(d["ts_code"])
            
            # 检查是否已存在
            existing = s.query(Prediction).filter(
                Prediction.trade_date == trade_date,
                Prediction.ts_code == ts_code
            ).first()
            
            if existing:
                # 更新现有记录
                existing.name = str(d["name"])
                existing.ai_score = int(d["ai_score"])
                existing.ai_reason = str(d.get("ai_reason", ""))
                existing.strategy_tag = str(d.get("strategy_tag", "")) if d.get("strategy_tag") else None
                existing.suggested_shares = int(d["suggested_shares"]) if d.get("suggested_shares") is not None else None
                existing.price_at_prediction = float(d["price_at_prediction"]) if d.get("price_at_prediction") is not None else None
                # 注意：不更新 actual_chg 和 current_price，这些字段由其他流程更新
                updated_count += 1
            else:
                # 插入新记录
                r = Prediction(
                    trade_date=trade_date,
                    ts_code=ts_code,
                    name=str(d["name"]),
                    ai_score=int(d["ai_score"]),
                    ai_reason=str(d.get("ai_reason", "")),
                    actual_chg=None,
                    strategy_tag=str(d.get("strategy_tag", "")) if d.get("strategy_tag") else None,
                    suggested_shares=int(d["suggested_shares"]) if d.get("suggested_shares") is not None else None,
                    price_at_prediction=float(d["price_at_prediction"]) if d.get("price_at_prediction") is not None else None,
                    current_price=None,
                )
                s.add(r)
                inserted_count += 1
        
        if updated_count > 0:
            logger.debug(f"save_daily_predictions: 更新 {updated_count} 条记录")
        if inserted_count > 0:
            logger.debug(f"save_daily_predictions: 插入 {inserted_count} 条记录")
    
    logger.info(f"save_daily_predictions: 已处理 {len(list_of_dicts)} 条（插入: {inserted_count}, 更新: {updated_count}）")


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


def get_all_predictions() -> List[Dict[str, Any]]:
    """返回所有预测记录，含 trade_date, ts_code, name, ai_score, ai_reason, actual_chg, strategy_tag, suggested_shares, price_at_prediction, current_price。"""
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
            Prediction.price_at_prediction,
            Prediction.current_price,
        ).all()
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
            "price_at_prediction": r[8],
            "current_price": r[9],
        }
        for r in rows
    ]


def update_prediction_price(trade_date: str, ts_code: str, current_price: float, return_pct: float) -> None:
    """更新预测记录的最新价格和收益率"""
    with _session_scope() as s:
        n = s.query(Prediction).filter(
            Prediction.trade_date == str(trade_date),
            Prediction.ts_code == str(ts_code),
        ).update({
            "actual_chg": float(return_pct),
            "current_price": float(current_price)
        })
        if n == 0:
            logger.debug(f"update_prediction_price: 未找到 trade_date={trade_date} ts_code={ts_code}")


def update_prediction_price_at_prediction(trade_date: str, ts_code: str, price: float) -> None:
    """更新预测时的价格"""
    with _session_scope() as s:
        n = s.query(Prediction).filter(
            Prediction.trade_date == str(trade_date),
            Prediction.ts_code == str(ts_code),
        ).update({"price_at_prediction": float(price)})
        if n == 0:
            logger.debug(f"update_prediction_price_at_prediction: 未找到 trade_date={trade_date} ts_code={ts_code}")


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


# ========== 指数成分股缓存管理方法 ==========

def get_cached_constituents(index_code: str, trade_date: str) -> List[str]:
    """
    从缓存表获取指定指数在指定日期的成分股列表。
    
    Args:
        index_code: 指数代码，如 '000852.SH'
        trade_date: 交易日期（YYYYMMDD），会查找该日期所在月份的数据
        
    Returns:
        股票代码列表，如果缓存不存在返回空列表
    """
    from datetime import datetime, timedelta
    import calendar
    
    try:
        # 计算交易日期所在月份的第一天和最后一天
        trade_dt = datetime.strptime(trade_date, "%Y%m%d")
        month_start = trade_dt.replace(day=1).strftime("%Y%m%d")
        # 获取月份最后一天
        last_day = calendar.monthrange(trade_dt.year, trade_dt.month)[1]
        month_end = trade_dt.replace(day=last_day).strftime("%Y%m%d")
        
        with _session_scope() as s:
            # 查找该月份内的成分股数据，取最新的trade_date
            constituents = s.query(IndexConstituent).filter(
                IndexConstituent.index_code == index_code,
                IndexConstituent.trade_date >= month_start,
                IndexConstituent.trade_date <= month_end
            ).order_by(IndexConstituent.trade_date.desc()).all()
            
            if constituents:
                # 取最新的trade_date对应的所有成分股
                latest_date = constituents[0].trade_date
                latest_constituents = [
                    c.ts_code for c in constituents 
                    if c.trade_date == latest_date
                ]
                logger.debug(f"从缓存获取成分股: {index_code}, 日期: {latest_date}, 数量: {len(latest_constituents)}")
                return latest_constituents
            else:
                logger.debug(f"缓存中未找到成分股: {index_code}, 日期范围: {month_start}-{month_end}")
                return []
    except Exception as e:
        logger.warning(f"get_cached_constituents 失败: {e}")
        return []


def save_constituents(index_code: str, trade_date: str, constituents_data: List[Dict[str, Any]]) -> None:
    """
    保存成分股数据到缓存表。
    
    Args:
        index_code: 指数代码，如 '000852.SH'
        trade_date: 生效日期（YYYYMMDD）
        constituents_data: 成分股数据列表，每个元素包含 'ts_code' 和可选的 'weight'
    """
    if not constituents_data:
        logger.warning(f"save_constituents: 成分股数据为空，跳过保存")
        return
    
    try:
        with _session_scope() as s:
            # 先删除该日期已有的数据（避免重复）
            s.query(IndexConstituent).filter(
                IndexConstituent.index_code == index_code,
                IndexConstituent.trade_date == trade_date
            ).delete()
            
            # 插入新数据
            for item in constituents_data:
                constituent = IndexConstituent(
                    index_code=index_code,
                    ts_code=str(item.get("ts_code", "")),
                    trade_date=trade_date,
                    weight=float(item.get("weight")) if item.get("weight") is not None else None,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                s.add(constituent)
            
            logger.info(f"保存成分股到缓存: {index_code}, 日期: {trade_date}, 数量: {len(constituents_data)}")
    except Exception as e:
        logger.error(f"save_constituents 失败: {e}")
        raise


def get_latest_constituents_date(index_code: str) -> str:
    """
    获取缓存中最新一期的生效日期。
    
    Args:
        index_code: 指数代码，如 '000852.SH'
        
    Returns:
        最新生效日期（YYYYMMDD），如果不存在返回空字符串
    """
    try:
        with _session_scope() as s:
            latest = s.query(IndexConstituent.trade_date).filter(
                IndexConstituent.index_code == index_code
            ).order_by(IndexConstituent.trade_date.desc()).first()
            
            if latest:
                return str(latest[0])
            return ""
    except Exception as e:
        logger.warning(f"get_latest_constituents_date 失败: {e}")
        return ""


def clear_old_constituents(index_code: str, before_date: str) -> None:
    """
    清理指定日期之前的旧成分股数据。
    
    Args:
        index_code: 指数代码
        before_date: 清理此日期之前的数据（YYYYMMDD）
    """
    try:
        with _session_scope() as s:
            deleted = s.query(IndexConstituent).filter(
                IndexConstituent.index_code == index_code,
                IndexConstituent.trade_date < before_date
            ).delete()
            if deleted > 0:
                logger.info(f"清理旧成分股数据: {index_code}, 日期 < {before_date}, 删除 {deleted} 条")
    except Exception as e:
        logger.warning(f"clear_old_constituents 失败: {e}")


# ========== 历史日线数据缓存管理方法 ==========

def get_cached_daily_history(
    ts_codes: List[str],
    start_date: str,
    end_date: str
):
    """
    从缓存表获取指定股票在指定日期范围的历史日线数据。
    
    Args:
        ts_codes: 股票代码列表
        start_date: 开始日期（YYYYMMDD）
        end_date: 结束日期（YYYYMMDD）
        
    Returns:
        DataFrame包含列: ts_code, trade_date, open, high, low, close, vol
    """
    import pandas as pd
    
    if not ts_codes:
        return pd.DataFrame()
    
    try:
        with _session_scope() as s:
            rows = s.query(DailyHistoryCache).filter(
                DailyHistoryCache.ts_code.in_(ts_codes),
                DailyHistoryCache.trade_date >= start_date,
                DailyHistoryCache.trade_date <= end_date
            ).all()
            
            if not rows:
                logger.debug(f"缓存中未找到历史数据: {len(ts_codes)} 只股票, {start_date} 到 {end_date}")
                return pd.DataFrame()
            
            # 转换为DataFrame
            data = []
            for row in rows:
                data.append({
                    'ts_code': row.ts_code,
                    'trade_date': row.trade_date,
                    'open': row.open,
                    'high': row.high,
                    'low': row.low,
                    'close': row.close,
                    'vol': row.vol,
                })
            
            df = pd.DataFrame(data)
            logger.info(f"从缓存获取历史数据: {len(df)} 条记录 ({start_date} 到 {end_date})")
            return df
    except Exception as e:
        logger.warning(f"get_cached_daily_history 失败: {e}")
        return pd.DataFrame()


def save_daily_history_batch(df) -> None:
    """
    批量保存历史日线数据到缓存表。
    使用 INSERT OR REPLACE 策略，自动去重。
    
    Args:
        df: DataFrame包含列: ts_code, trade_date, open, high, low, close, vol
    """
    import pandas as pd
    
    if df.empty:
        logger.warning("save_daily_history_batch: DataFrame为空，跳过保存")
        return
    
    required_columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        logger.warning(f"save_daily_history_batch: 缺少必要列: {missing_columns}")
        return
    
    try:
        with _session_scope() as s:
            # 使用 bulk_insert_mappings 提高性能
            records = []
            for _, row in df.iterrows():
                records.append({
                    'ts_code': str(row['ts_code']),
                    'trade_date': str(row['trade_date']),
                    'open': float(row['open']) if pd.notna(row['open']) else None,
                    'high': float(row['high']) if pd.notna(row['high']) else None,
                    'low': float(row['low']) if pd.notna(row['low']) else None,
                    'close': float(row['close']) if pd.notna(row['close']) else None,
                    'vol': float(row['vol']) if pd.notna(row['vol']) else None,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now(),
                })
            
            # 使用 INSERT OR REPLACE（SQLite语法）
            from sqlalchemy import text
            for record in records:
                s.execute(text("""
                    INSERT OR REPLACE INTO daily_history_cache 
                    (ts_code, trade_date, open, high, low, close, vol, created_at, updated_at)
                    VALUES (:ts_code, :trade_date, :open, :high, :low, :close, :vol, :created_at, :updated_at)
                """), record)
            
            logger.info(f"保存历史数据到缓存: {len(records)} 条记录")
    except Exception as e:
        logger.error(f"save_daily_history_batch 失败: {e}")
        raise


def clear_old_daily_history(before_date: str) -> None:
    """
    清理指定日期之前的旧历史数据。
    
    Args:
        before_date: 清理此日期之前的数据（YYYYMMDD）
    """
    try:
        with _session_scope() as s:
            deleted = s.query(DailyHistoryCache).filter(
                DailyHistoryCache.trade_date < before_date
            ).delete()
            if deleted > 0:
                logger.info(f"清理旧历史数据: 日期 < {before_date}, 删除 {deleted} 条")
    except Exception as e:
        logger.warning(f"clear_old_daily_history 失败: {e}")


# ========== 每日净值管理方法 ==========

def save_or_update_daily_nav(trade_date: str, total_asset: float, benchmark_val: Optional[float] = None) -> None:
    """
    保存或更新每日净值记录（幂等性保证）。
    
    Args:
        trade_date: 交易日期（YYYYMMDD格式）
        total_asset: 总资产
        benchmark_val: 基准指数收盘价（可选）
    """
    try:
        with _session_scope() as s:
            # 查询是否已存在
            existing = s.query(DailyNav).filter(DailyNav.trade_date == str(trade_date)).first()
            
            if existing:
                # 更新现有记录
                existing.total_asset = float(total_asset)
                existing.benchmark_val = float(benchmark_val) if benchmark_val is not None else None
                existing.updated_at = datetime.now()
                logger.debug(f"更新每日净值: {trade_date}, 总资产={total_asset:.2f}")
            else:
                # 插入新记录
                nav = DailyNav(
                    trade_date=str(trade_date),
                    total_asset=float(total_asset),
                    benchmark_val=float(benchmark_val) if benchmark_val is not None else None
                )
                s.add(nav)
                logger.debug(f"创建每日净值: {trade_date}, 总资产={total_asset:.2f}")
        
        logger.info(f"每日净值已保存: {trade_date}, 总资产={total_asset:.2f}, 基准={benchmark_val:.2f if benchmark_val else 'N/A'}")
    except Exception as e:
        logger.error(f"save_or_update_daily_nav 失败: {e}")
        raise


# ========== 每日任务执行记录管理方法 ==========

def create_daily_task_execution(
    execution_id: str,
    trade_date: str,
    trigger_type: str,
    max_retries: int = 3
) -> Dict[str, Any]:
    """
    创建每日任务执行记录
    
    Args:
        execution_id: 执行ID（UUID）
        trade_date: 交易日期（YYYYMMDD格式）
        trigger_type: 触发类型（SCHEDULED/MANUAL/API）
        max_retries: 最大重试次数
        
    Returns:
        创建的执行记录字典
    """
    try:
        with _session_scope() as s:
            execution = DailyTaskExecution(
                execution_id=execution_id,
                trade_date=str(trade_date),
                trigger_type=trigger_type,
                status='PENDING',
                is_duplicate=False,
                started_at=datetime.now(),
                max_retries=max_retries,
                retry_count=0
            )
            s.add(execution)
            
            result = {
                'id': execution.id,
                'execution_id': execution.execution_id,
                'trade_date': execution.trade_date,
                'trigger_type': execution.trigger_type,
                'status': execution.status,
                'is_duplicate': execution.is_duplicate,
                'started_at': execution.started_at,
                'max_retries': execution.max_retries,
                'retry_count': execution.retry_count,
                'created_at': execution.created_at
            }
            
            logger.info(f"创建任务执行记录: {execution_id}, 交易日期: {trade_date}")
            return result
    except Exception as e:
        logger.error(f"create_daily_task_execution 失败: {e}")
        raise


def update_daily_task_execution_status(
    execution_id: str,
    status: str,
    steps_completed: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    duration_seconds: Optional[float] = None,
    is_duplicate: Optional[bool] = None
) -> None:
    """
    更新任务执行状态
    
    Args:
        execution_id: 执行ID
        status: 状态（PENDING/RUNNING/SUCCESS/FAILED/RETRYING）
        steps_completed: 已完成的步骤列表（JSON格式）
        errors: 错误列表（JSON格式）
        duration_seconds: 执行时长（秒）
        is_duplicate: 是否为重复执行
    """
    import json
    try:
        with _session_scope() as s:
            execution = s.query(DailyTaskExecution).filter(
                DailyTaskExecution.execution_id == execution_id
            ).first()
            
            if not execution:
                logger.warning(f"update_daily_task_execution_status: 未找到执行记录 {execution_id}")
                return
            
            execution.status = status
            execution.updated_at = datetime.now()
            
            if steps_completed is not None:
                execution.steps_completed = json.dumps(steps_completed, ensure_ascii=False)
            
            if errors is not None:
                execution.errors = json.dumps(errors, ensure_ascii=False)
            
            if duration_seconds is not None:
                execution.duration_seconds = duration_seconds
                execution.completed_at = datetime.now()
            
            if is_duplicate is not None:
                execution.is_duplicate = is_duplicate
            
            if status in ['SUCCESS', 'FAILED']:
                execution.completed_at = datetime.now()
            
            logger.debug(f"更新任务执行状态: {execution_id}, status={status}")
    except Exception as e:
        logger.error(f"update_daily_task_execution_status 失败: {e}")
        raise


def get_daily_task_execution_by_id(execution_id: str) -> Optional[Dict[str, Any]]:
    """
    根据执行ID获取任务执行记录
    
    Args:
        execution_id: 执行ID
        
    Returns:
        执行记录字典，如果不存在返回None
    """
    import json
    try:
        with _session_scope() as s:
            execution = s.query(DailyTaskExecution).filter(
                DailyTaskExecution.execution_id == execution_id
            ).first()
            
            if not execution:
                return None
            
            steps_completed = None
            if execution.steps_completed:
                try:
                    steps_completed = json.loads(execution.steps_completed)
                except:
                    pass
            
            errors = None
            if execution.errors:
                try:
                    errors = json.loads(execution.errors)
                except:
                    pass
            
            return {
                'id': execution.id,
                'execution_id': execution.execution_id,
                'trade_date': execution.trade_date,
                'trigger_type': execution.trigger_type,
                'status': execution.status,
                'is_duplicate': execution.is_duplicate,
                'started_at': execution.started_at,
                'completed_at': execution.completed_at,
                'duration_seconds': execution.duration_seconds,
                'steps_completed': steps_completed,
                'errors': errors,
                'retry_count': execution.retry_count,
                'max_retries': execution.max_retries,
                'next_retry_at': execution.next_retry_at,
                'created_at': execution.created_at,
                'updated_at': execution.updated_at
            }
    except Exception as e:
        logger.error(f"get_daily_task_execution_by_id 失败: {e}")
        return None


def list_daily_task_executions(
    trade_date: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    列出任务执行记录
    
    Args:
        trade_date: 交易日期（可选，用于过滤）
        status: 状态（可选，用于过滤）
        limit: 返回记录数限制
        
    Returns:
        执行记录列表
    """
    import json
    try:
        with _session_scope() as s:
            query = s.query(DailyTaskExecution)
            
            if trade_date:
                query = query.filter(DailyTaskExecution.trade_date == str(trade_date))
            
            if status:
                query = query.filter(DailyTaskExecution.status == status)
            
            executions = query.order_by(DailyTaskExecution.created_at.desc()).limit(limit).all()
            
            results = []
            for execution in executions:
                steps_completed = None
                if execution.steps_completed:
                    try:
                        steps_completed = json.loads(execution.steps_completed)
                    except:
                        pass
                
                errors = None
                if execution.errors:
                    try:
                        errors = json.loads(execution.errors)
                    except:
                        pass
                
                results.append({
                    'id': execution.id,
                    'execution_id': execution.execution_id,
                    'trade_date': execution.trade_date,
                    'trigger_type': execution.trigger_type,
                    'status': execution.status,
                    'is_duplicate': execution.is_duplicate,
                    'started_at': execution.started_at,
                    'completed_at': execution.completed_at,
                    'duration_seconds': execution.duration_seconds,
                    'steps_completed': steps_completed,
                    'errors': errors,
                    'retry_count': execution.retry_count,
                    'max_retries': execution.max_retries,
                    'next_retry_at': execution.next_retry_at,
                    'created_at': execution.created_at,
                    'updated_at': execution.updated_at
                })
            
            return results
    except Exception as e:
        logger.error(f"list_daily_task_executions 失败: {e}")
        return []


def get_latest_daily_task_execution(trade_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    获取最新的任务执行记录
    
    Args:
        trade_date: 交易日期（可选，如果提供则获取该日期的最新记录）
        
    Returns:
        执行记录字典，如果不存在返回None
    """
    import json
    try:
        with _session_scope() as s:
            query = s.query(DailyTaskExecution)
            
            if trade_date:
                query = query.filter(DailyTaskExecution.trade_date == str(trade_date))
            
            execution = query.order_by(DailyTaskExecution.created_at.desc()).first()
            
            if not execution:
                return None
            
            steps_completed = None
            if execution.steps_completed:
                try:
                    steps_completed = json.loads(execution.steps_completed)
                except:
                    pass
            
            errors = None
            if execution.errors:
                try:
                    errors = json.loads(execution.errors)
                except:
                    pass
            
            return {
                'id': execution.id,
                'execution_id': execution.execution_id,
                'trade_date': execution.trade_date,
                'trigger_type': execution.trigger_type,
                'status': execution.status,
                'is_duplicate': execution.is_duplicate,
                'started_at': execution.started_at,
                'completed_at': execution.completed_at,
                'duration_seconds': execution.duration_seconds,
                'steps_completed': steps_completed,
                'errors': errors,
                'retry_count': execution.retry_count,
                'max_retries': execution.max_retries,
                'next_retry_at': execution.next_retry_at,
                'created_at': execution.created_at,
                'updated_at': execution.updated_at
            }
    except Exception as e:
        logger.error(f"get_latest_daily_task_execution 失败: {e}")
        return None


def get_running_daily_task_execution() -> Optional[Dict[str, Any]]:
    """
    获取正在运行的任务执行记录（用于并发控制）
    
    Returns:
        执行记录字典，如果不存在返回None
    """
    import json
    try:
        with _session_scope() as s:
            execution = s.query(DailyTaskExecution).filter(
                DailyTaskExecution.status == 'RUNNING'
            ).order_by(DailyTaskExecution.created_at.desc()).first()
            
            if not execution:
                return None
            
            steps_completed = None
            if execution.steps_completed:
                try:
                    steps_completed = json.loads(execution.steps_completed)
                except:
                    pass
            
            errors = None
            if execution.errors:
                try:
                    errors = json.loads(execution.errors)
                except:
                    pass
            
            return {
                'id': execution.id,
                'execution_id': execution.execution_id,
                'trade_date': execution.trade_date,
                'trigger_type': execution.trigger_type,
                'status': execution.status,
                'is_duplicate': execution.is_duplicate,
                'started_at': execution.started_at,
                'completed_at': execution.completed_at,
                'duration_seconds': execution.duration_seconds,
                'steps_completed': steps_completed,
                'errors': errors,
                'retry_count': execution.retry_count,
                'max_retries': execution.max_retries,
                'next_retry_at': execution.next_retry_at,
                'created_at': execution.created_at,
                'updated_at': execution.updated_at
            }
    except Exception as e:
        logger.error(f"get_running_daily_task_execution 失败: {e}")
        return None
