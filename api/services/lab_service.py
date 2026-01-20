"""
Lab Service - 实验室业务逻辑适配层
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
from datetime import datetime

from src.services.backtest_service import BacktestService as CoreBacktestService, BacktestResult
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.logging_config import get_logger

logger = get_logger(__name__)


class APILabService:
    """Lab API服务层（适配器）"""
    
    def __init__(self, data_provider: DataProvider, config: ConfigManager):
        self.core_service = CoreBacktestService(data_provider=data_provider, config=config)
    
    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        holding_days: int = 5,
        stop_loss_pct: float = 0.08,
        cost_rate: float = 0.002,
        benchmark_code: str = "000300.SH",
        index_code: Optional[str] = None,
        max_positions: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            holding_days: 持仓天数
            stop_loss_pct: 止损百分比
            cost_rate: 交易成本率
            benchmark_code: 基准指数代码
            index_code: 股票池指数代码
            max_positions: 最大持仓数
            
        Returns:
            回测结果字典
        """
        try:
            # 如果提供了max_positions，临时更新配置
            original_max_positions = None
            if max_positions is not None:
                # 尝试多个配置路径
                original_max_positions = self.core_service.config.get('strategy.backtest.max_positions') or \
                                        self.core_service.config.get('backtest.max_positions')
                # 确保配置字典存在
                if 'strategy' not in self.core_service.config.config:
                    self.core_service.config.config['strategy'] = {}
                if 'backtest' not in self.core_service.config.config['strategy']:
                    self.core_service.config.config['strategy']['backtest'] = {}
                self.core_service.config.config['strategy']['backtest']['max_positions'] = max_positions
            
            try:
                # 执行回测
                result: BacktestResult = self.core_service.run_backtest(
                    start_date=start_date,
                    end_date=end_date,
                    holding_days=holding_days,
                    stop_loss_pct=stop_loss_pct,
                    cost_rate=cost_rate,
                    benchmark_code=benchmark_code,
                    index_code=index_code
                )
                
                # 恢复原始配置
                if original_max_positions is not None:
                    if 'strategy' in self.core_service.config.config and \
                       'backtest' in self.core_service.config.config['strategy']:
                        self.core_service.config.config['strategy']['backtest']['max_positions'] = original_max_positions
                
                if not result.success:
                    return {
                        "success": False,
                        "metrics": None,
                        "equity_curve": [],
                        "top_winners": [],
                        "top_losers": [],
                        "error": result.error
                    }
                
                # 转换结果
                return self._format_backtest_results(result.results)
                
            except Exception as e:
                # 恢复原始配置
                if original_max_positions is not None:
                    if 'strategy' in self.core_service.config.config and \
                       'backtest' in self.core_service.config.config['strategy']:
                        self.core_service.config.config['strategy']['backtest']['max_positions'] = original_max_positions
                raise
                
        except Exception as e:
            logger.exception(f"回测异常: {type(e).__name__}: {str(e)}")
            error_message = f"回测执行失败: {str(e)}" if str(e) else "回测执行失败: 未知错误"
            return {
                "success": False,
                "metrics": None,
                "equity_curve": [],
                "top_winners": [],
                "top_losers": [],
                "error": error_message
            }
    
    def _format_backtest_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化回测结果
        
        Args:
            results: 原始回测结果
            
        Returns:
            格式化后的结果
        """
        # 权益曲线
        equity_curve = []
        if 'equity_curve' in results:
            ec = results['equity_curve']
            
            if isinstance(ec, pd.Series):
                # 如果是Series，索引是trade_date，值是equity（归一化的净值）
                if not ec.empty:
                    # 计算基准净值曲线（从benchmark_metrics或使用默认值）
                    benchmark_initial = 1.0
                    benchmark_metrics = results.get('benchmark_metrics', {})
                    benchmark_total_return = benchmark_metrics.get('total_return', 0.0) / 100.0
                    
                    # 简单线性插值基准净值（实际应该从benchmark数据计算）
                    dates = list(ec.index)
                    if len(dates) > 1:
                        benchmark_final = 1.0 + benchmark_total_return
                        benchmark_values = np.linspace(benchmark_initial, benchmark_final, len(dates))
                    else:
                        benchmark_values = [benchmark_initial]
                    
                    for i, (date, strategy_val) in enumerate(ec.items()):
                        benchmark_val = float(benchmark_values[i]) if i < len(benchmark_values) else benchmark_initial
                        
                        date_str = date.strftime("%Y-%m-%d") if hasattr(date, 'strftime') else str(date)
                        equity_curve.append({
                            "date": date_str,
                            "strategy_equity": float(strategy_val),
                            "benchmark_equity": benchmark_val
                        })
            elif isinstance(ec, pd.DataFrame) and not ec.empty:
                # 如果是DataFrame
                for _, row in ec.iterrows():
                    equity_curve.append({
                        "date": row['trade_date'].strftime("%Y-%m-%d") if hasattr(row.get('trade_date'), 'strftime') else str(row.get('trade_date', '')),
                        "strategy_equity": float(row.get('strategy_equity', row.get('equity', 0))),
                        "benchmark_equity": float(row.get('benchmark_equity', 0))
                    })
        
        # 计算指标
        metrics = self._calculate_metrics(results)
        
        # Top Winners/Losers
        top_winners = []
        top_losers = []
        
        if 'top_contributors' in results and not results['top_contributors'].empty:
            contributors = results['top_contributors']
            
            # 按总收益排序
            contributors_sorted = contributors.sort_values('total_gain', ascending=False)
            
            # Top 3 Winners
            winners = contributors_sorted.head(3)
            for _, row in winners.iterrows():
                top_winners.append({
                    "code": str(row.get('ts_code', '')),
                    "name": str(row.get('name', '未知')),
                    "total_gain": float(row.get('total_gain', 0)),
                    "total_gain_pct": float(row.get('total_gain_pct', 0))
                })
            
            # Top 3 Losers
            losers = contributors_sorted.tail(3)
            for _, row in losers.iterrows():
                top_losers.append({
                    "code": str(row.get('ts_code', '')),
                    "name": str(row.get('name', '未知')),
                    "total_gain": float(row.get('total_gain', 0)),
                    "total_gain_pct": float(row.get('total_gain_pct', 0))
                })
        
        return {
            "success": True,
            "metrics": metrics,
            "equity_curve": equity_curve,
            "top_winners": top_winners,
            "top_losers": top_losers,
            "error": None
        }
    
    def _calculate_metrics(self, results: Dict[str, Any]) -> Dict[str, float]:
        """
        计算回测指标
        
        Args:
            results: 回测结果
            
        Returns:
            指标字典
        """
        metrics = {
            "total_return": 0.0,
            "benchmark_return": 0.0,
            "max_drawdown": 0.0,
            "win_rate": None,
            "sharpe_ratio": None,
            "total_trades": None
        }
        
        # 从equity_curve计算
        ec = results.get('equity_curve')
        if ec is not None:
            if isinstance(ec, pd.Series) and not ec.empty:
                # Series格式：索引是日期，值是净值
                initial_strategy = float(ec.iloc[0])
                final_strategy = float(ec.iloc[-1])
                metrics['total_return'] = ((final_strategy - initial_strategy) / initial_strategy * 100) if initial_strategy > 0 else 0.0
                
                # 最大回撤
                running_max = ec.expanding().max()
                drawdown = (ec - running_max) / running_max * 100
                metrics['max_drawdown'] = abs(float(drawdown.min())) if not drawdown.empty else 0.0
                
                # 基准收益率从benchmark_metrics获取
                benchmark_metrics = results.get('benchmark_metrics', {})
                metrics['benchmark_return'] = float(benchmark_metrics.get('total_return', 0.0))
            elif isinstance(ec, pd.DataFrame) and not ec.empty:
                # DataFrame格式
                if 'strategy_equity' in ec.columns and 'benchmark_equity' in ec.columns:
                    initial_strategy = float(ec.iloc[0]['strategy_equity'])
                    final_strategy = float(ec.iloc[-1]['strategy_equity'])
                    metrics['total_return'] = ((final_strategy - initial_strategy) / initial_strategy * 100) if initial_strategy > 0 else 0.0
                    
                    initial_benchmark = float(ec.iloc[0]['benchmark_equity'])
                    final_benchmark = float(ec.iloc[-1]['benchmark_equity'])
                    metrics['benchmark_return'] = ((final_benchmark - initial_benchmark) / initial_benchmark * 100) if initial_benchmark > 0 else 0.0
                    
                    # 最大回撤
                    strategy_equity = ec['strategy_equity']
                    running_max = strategy_equity.expanding().max()
                    drawdown = (strategy_equity - running_max) / running_max * 100
                    metrics['max_drawdown'] = abs(float(drawdown.min())) if not drawdown.empty else 0.0
        
        # 从results获取其他指标
        if 'win_rate' in results:
            metrics['win_rate'] = float(results['win_rate'])
        if 'sharpe_ratio' in results:
            metrics['sharpe_ratio'] = float(results['sharpe_ratio'])
        
        # 计算总交易数
        total_trades = None
        strategy_metrics = results.get('strategy_metrics', {})
        if 'total_trades' in strategy_metrics:
            total_trades = int(strategy_metrics['total_trades'])
        elif 'trades' in results:
            trades = results['trades']
            if isinstance(trades, pd.DataFrame):
                total_trades = len(trades)
            elif isinstance(trades, list):
                total_trades = len(trades)
        
        metrics['total_trades'] = total_trades
        
        return metrics
