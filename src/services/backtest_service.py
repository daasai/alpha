"""
Backtest Service - 回测业务逻辑
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_service import BaseService
from ..backtest import VectorBacktester
from ..exceptions import DataFetchError, StrategyError
from ..logging_config import get_logger

logger = get_logger(__name__)


class BacktestResult:
    """回测结果"""
    
    def __init__(
        self,
        success: bool,
        results: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.results = results if results is not None else {}
        self.error = error


class BacktestService(BaseService):
    """Backtest服务 - 回测业务逻辑"""
    
    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        holding_days: int = 5,
        stop_loss_pct: float = 0.08,
        cost_rate: float = 0.002,
        benchmark_code: str = "000300.SH",
        index_code: Optional[str] = None,
        rps_threshold: Optional[float] = None,
        max_positions: Optional[int] = None,
        initial_capital: Optional[float] = None
    ) -> BacktestResult:
        """
        运行回测
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            holding_days: 持仓天数，默认5天
            stop_loss_pct: 止损百分比，默认0.08 (8%)
            cost_rate: 交易成本率，默认0.002 (0.2%)
            benchmark_code: 基准指数代码，默认沪深300
            index_code: 股票池指数代码，如果为None则使用配置的指数
            rps_threshold: RPS阈值，默认使用配置值
            
        Returns:
            BacktestResult: 回测结果
        """
        try:
            logger.info(
                f"Backtest 开始: {start_date} 到 {end_date}, "
                f"持仓天数: {holding_days}, 止损: {stop_loss_pct*100:.1f}%, "
                f"成本: {cost_rate*100:.2f}%"
            )
            
            # 从配置获取参数（如果未提供）
            if index_code is None:
                # 尝试多个配置路径
                index_code = self.config.get('strategy.backtest.index_code') or \
                            self.config.get('backtest.index_code') or \
                            '000300.SH'
                logger.debug(f"使用股票池指数代码: {index_code}")
            
            # 获取历史数据
            try:
                history_df = self.data_provider.fetch_history_batch(
                    start_date=start_date,
                    end_date=end_date,
                    index_code=index_code,
                    use_cache=True
                )
                
                if history_df.empty:
                    raise DataFetchError("无法获取历史数据")
            except Exception as e:
                if isinstance(e, DataFetchError):
                    raise
                raise DataFetchError(f"获取历史数据失败: {str(e)}") from e
            
            # 运行回测引擎
            try:
                backtester = VectorBacktester(self.data_provider)
                
                # 从参数或配置获取回测参数（参数优先）
                final_initial_capital = initial_capital or self.config.get('backtest.initial_capital', 1000000.0)
                final_max_positions = max_positions or self.config.get('backtest.max_positions', 4)
                
                results = backtester.run(
                    history_df,
                    holding_days=holding_days,
                    stop_loss_pct=stop_loss_pct,
                    cost_rate=cost_rate,
                    benchmark_code=benchmark_code,
                    initial_capital=final_initial_capital,
                    max_positions=final_max_positions,
                    rps_threshold=rps_threshold
                )
            except Exception as e:
                raise StrategyError(f"回测执行失败: {str(e)}") from e
            
            # 获取股票名称（用于Top Contributors显示）
            if not results.get('top_contributors', pd.DataFrame()).empty:
                top_contributors = results['top_contributors']
                try:
                    stock_basic = self.data_provider.get_stock_basic()
                    if not stock_basic.empty:
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
                
                results['top_contributors'] = top_contributors
            
            logger.info("Backtest 完成")
            
            return BacktestResult(
                success=True,
                results=results
            )
            
        except (DataFetchError, StrategyError) as e:
            logger.error(f"Backtest 失败: {e}")
            return BacktestResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.exception("Backtest 异常")
            return BacktestResult(
                success=False,
                error=f"回测过程出错: {str(e)}"
            )
