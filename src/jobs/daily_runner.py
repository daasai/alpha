"""
Daily Runner - 每日自动化引擎

在每日收盘后（17:30之后）执行自动化处理流程：
1. 数据更新与安全检查
2. 组合盯市（Mark-to-Market）
3. 风险管理（止损检查）
4. 信号生成（Hunter扫描）
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import pandas as pd

# 确保项目根目录在 Python 路径中
try:
    # 从当前文件位置计算项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
except (NameError, AttributeError):
    # 如果 __file__ 不可用，尝试使用当前工作目录
    project_root = Path(os.getcwd())
    # 如果当前目录不是项目根目录，尝试向上查找
    while project_root != project_root.parent and not (project_root / 'api').exists():
        project_root = project_root.parent

# 确保项目根目录在路径中
project_root_str = str(project_root)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from api.services.portfolio_service import PortfolioService
from src.services.hunter_service import HunterService
from src.database import save_or_update_daily_nav, save_daily_predictions, get_cached_daily_history
from src.logging_config import get_logger
from src.strategy import get_trade_date

logger = get_logger(__name__)


class DailyRunner:
    """每日自动化引擎"""
    
    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        config: Optional[ConfigManager] = None,
        portfolio_service: Optional[PortfolioService] = None,
        hunter_service: Optional[HunterService] = None
    ):
        """
        初始化 DailyRunner
        
        Args:
            data_provider: 数据提供者，如果为None则创建新实例
            config: 配置管理器，如果为None则创建新实例
            portfolio_service: 组合服务，如果为None则创建新实例
            hunter_service: Hunter服务，如果为None则创建新实例
        """
        # 初始化配置
        if config is None:
            self.config = ConfigManager()
        else:
            self.config = config
        
        # 初始化数据提供者
        if data_provider is None:
            self.data_provider = DataProvider(config=self.config)
        else:
            self.data_provider = data_provider
        
        # 初始化组合服务
        if portfolio_service is None:
            from src.repositories.portfolio_repository import PortfolioRepository
            repository = PortfolioRepository()
            self.portfolio_service = PortfolioService(
                data_provider=self.data_provider,
                config=self.config,
                repository=repository
            )
        else:
            self.portfolio_service = portfolio_service
        
        # 初始化Hunter服务
        if hunter_service is None:
            self.hunter_service = HunterService(
                data_provider=self.data_provider,
                config=self.config
            )
        else:
            self.hunter_service = hunter_service
        
        # 从配置读取止损阈值
        self.stop_loss_threshold = self.config.get('risk.stop_loss_threshold', -0.08)
        
        logger.info("DailyRunner 初始化完成")
    
    def run(self, trade_date: Optional[str] = None, execution_id: Optional[str] = None) -> Dict[str, Any]:
        """
        执行每日自动化流程
        
        Args:
            trade_date: 交易日期（YYYYMMDD格式），如果为None则使用当前交易日
            execution_id: 执行ID（可选，用于日志追踪）
        
        Returns:
            执行结果字典，包含 success, steps_completed, errors
        """
        # 确定交易日期
        if trade_date is None:
            trade_date = datetime.now().strftime('%Y%m%d')
        
        result = {
            'success': False,
            'trade_date': trade_date,
            'execution_id': execution_id,
            'steps_completed': [],
            'errors': []
        }
        
        current_time = datetime.now().strftime('%H:%M')
        exec_id_str = f" [execution_id: {execution_id}]" if execution_id else ""
        logger.info(f"[{current_time}] 每日任务开始，交易日期: {trade_date}{exec_id_str}")
        
        # Step A: 数据更新与安全检查
        try:
            if not self._step_a_data_check(trade_date):
                error_msg = "数据可用性检查失败: Tushare数据尚未就绪"
                result['errors'].append(error_msg)
                logger.warning(f"⚠️ {error_msg}，交易日期: {trade_date}{exec_id_str}。终止执行。")
                return result
            result['steps_completed'].append('Step A: 数据更新与安全检查')
        except Exception as e:
            error_msg = f"Step A 执行失败: {str(e)}"
            logger.error(f"{error_msg}{exec_id_str}", exc_info=True)
            result['errors'].append(error_msg)
            return result
        
        # Step B: 组合盯市
        try:
            benchmark_val = self._step_b_mark_to_market(trade_date)
            result['steps_completed'].append('Step B: 组合盯市')
        except Exception as e:
            error_msg = f"Step B 执行失败: {str(e)}"
            logger.error(f"{error_msg}{exec_id_str}", exc_info=True)
            result['errors'].append(error_msg)
            benchmark_val = None
        
        # Step C: 风险管理
        try:
            self._step_c_risk_management(trade_date)
            result['steps_completed'].append('Step C: 风险管理')
        except Exception as e:
            error_msg = f"Step C 执行失败: {str(e)}"
            logger.error(f"{error_msg}{exec_id_str}", exc_info=True)
            result['errors'].append(error_msg)
        
        # Step D: 信号生成
        try:
            self._step_d_signal_generation(trade_date)
            result['steps_completed'].append('Step D: 信号生成')
        except Exception as e:
            error_msg = f"Step D 执行失败: {str(e)}"
            logger.error(f"{error_msg}{exec_id_str}", exc_info=True)
            result['errors'].append(error_msg)
        
        # 判断整体成功
        result['success'] = len(result['errors']) == 0
        
        current_time = datetime.now().strftime('%H:%M')
        if result['success']:
            logger.info(f"[{current_time}] 每日任务完成，交易日期: {trade_date}{exec_id_str}")
        else:
            logger.warning(
                f"[{current_time}] 每日任务完成（有错误），交易日期: {trade_date}, "
                f"错误数: {len(result['errors'])}{exec_id_str}"
            )
        
        return result
    
    def _step_a_data_check(self, trade_date: str) -> bool:
        """
        Step A: 数据更新与安全检查
        
        Args:
            trade_date: 交易日期
        
        Returns:
            如果数据可用返回True，否则返回False
        """
        current_time = datetime.now().strftime('%H:%M')
        
        # 1. 数据可用性检查：检查指数数据
        try:
            index_data = self.data_provider._tushare_client.get_daily(
                ts_code="000001.SH",
                trade_date=trade_date,
                fields="ts_code,trade_date,close"
            )
            
            if index_data.empty:
                logger.warning(f"⚠️ Tushare数据尚未就绪，交易日期: {trade_date}。终止执行。")
                return False
        except Exception as e:
            logger.warning(f"⚠️ 数据可用性检查失败: {e}")
            return False
        
        # 2. 获取并缓存股票数据
        try:
            # 尝试调用 fetch_and_cache_daily（如果存在）
            if hasattr(self.data_provider, 'fetch_and_cache_daily'):
                self.data_provider.fetch_and_cache_daily(trade_date)
            else:
                # 降级：调用 get_daily_basic 获取数据
                basic_df = self.data_provider.get_daily_basic(trade_date)
                if not basic_df.empty:
                    logger.info(f"[{current_time}] 数据同步完成: {len(basic_df)} 只股票")
        except Exception as e:
            logger.warning(f"获取股票数据失败: {e}")
        
        # 3. 获取指数数据（用于BBI和基准值）
        try:
            if hasattr(self.data_provider, 'fetch_index_data'):
                index_df = self.data_provider.fetch_index_data(trade_date)
            else:
                # 降级：直接调用 Tushare API
                index_df = self.data_provider._tushare_client._pro.index_daily(
                    ts_code="000300.SH",
                    trade_date=trade_date,
                    fields="trade_date,close"
                )
                if not index_df.empty:
                    logger.debug(f"获取指数数据: {len(index_df)} 条记录")
        except Exception as e:
            logger.warning(f"获取指数数据失败: {e}")
        
        return True
    
    def _step_b_mark_to_market(self, trade_date: str) -> Optional[float]:
        """
        Step B: 组合盯市（Mark-to-Market）
        
        Args:
            trade_date: 交易日期
        
        Returns:
            基准指数收盘价（如果获取成功）
        """
        current_time = datetime.now().strftime('%H:%M')
        
        # 1. 获取持仓列表
        positions = self.portfolio_service.get_positions()
        
        if not positions:
            logger.info(f"[{current_time}] 无持仓，跳过盯市")
            return None
        
        # 2. 批量获取持仓价格
        prices_dict = {}
        ts_codes = [pos['ts_code'] for pos in positions]
        
        # 从缓存获取价格
        try:
            cached_df = get_cached_daily_history(ts_codes, trade_date, trade_date)
            if not cached_df.empty:
                # 过滤出目标交易日的数据
                target_df = cached_df[cached_df['trade_date'] == trade_date]
                for _, row in target_df.iterrows():
                    if pd.notna(row.get('close')):
                        prices_dict[row['ts_code']] = float(row['close'])
        except Exception as e:
            logger.warning(f"从缓存获取价格失败: {e}")
        
        # 对于缓存中没有的股票，尝试从API获取
        missing_codes = [code for code in ts_codes if code not in prices_dict]
        if missing_codes:
            for ts_code in missing_codes:
                try:
                    daily = self.data_provider._tushare_client.get_daily(
                        ts_code=ts_code,
                        trade_date=trade_date,
                        fields="close"
                    )
                    if not daily.empty and pd.notna(daily.iloc[0].get('close')):
                        prices_dict[ts_code] = float(daily.iloc[0]['close'])
                except Exception as e:
                    logger.warning(f"获取 {ts_code} 价格失败: {e}")
        
        # 3. 批量更新持仓价格
        if prices_dict:
            self.portfolio_service.repository.update_positions_market_value(prices_dict)
            logger.info(f"[{current_time}] 持仓盯市完成: {len(prices_dict)}/{len(positions)} 只股票")
        else:
            logger.warning(f"[{current_time}] 未能获取任何持仓价格")
        
        # 4. 计算并保存 NAV
        account = self.portfolio_service.get_account()
        if account:
            total_asset = account['cash'] + account['market_value']
            
            # 获取基准指数收盘价
            benchmark_val = None
            try:
                index_data = self.data_provider._tushare_client._pro.index_daily(
                    ts_code="000300.SH",
                    trade_date=trade_date,
                    fields="close"
                )
                if not index_data.empty and pd.notna(index_data.iloc[0].get('close')):
                    benchmark_val = float(index_data.iloc[0]['close'])
            except Exception as e:
                logger.warning(f"获取基准指数数据失败: {e}")
            
            # 保存 NAV
            save_or_update_daily_nav(trade_date, total_asset, benchmark_val)
            logger.info(f"[{current_time}] NAV已保存: 总资产={total_asset:.2f}, 基准={benchmark_val:.2f if benchmark_val else 'N/A'}")
            
            return benchmark_val
        else:
            logger.warning(f"[{current_time}] 账户未初始化，无法保存NAV")
            return None
    
    def _step_c_risk_management(self, trade_date: str) -> None:
        """
        Step C: 风险管理（止损检查）
        
        Args:
            trade_date: 交易日期
        """
        current_time = datetime.now().strftime('%H:%M')
        
        positions = self.portfolio_service.get_positions()
        
        if not positions:
            return
        
        stop_loss_count = 0
        for pos in positions:
            ts_code = pos['ts_code']
            current_price = pos.get('current_price')
            avg_price = pos.get('avg_price', 0)
            
            if current_price is None or avg_price <= 0:
                continue
            
            # 计算收益率
            return_pct = (current_price - avg_price) / avg_price
            
            # 止损检查
            if return_pct < self.stop_loss_threshold:
                stop_loss_count += 1
                logger.warning(
                    f"⚠️ 止损触发: {ts_code}, "
                    f"当前价格={current_price:.2f}, "
                    f"成本价={avg_price:.2f}, "
                    f"亏损={return_pct*100:.2f}%"
                )
                # V1.4预留：未来可插入 alerts 表记录
        
        if stop_loss_count > 0:
            logger.info(f"[{current_time}] 风险管理检查完成: {stop_loss_count} 只股票触发止损")
        else:
            logger.info(f"[{current_time}] 风险管理检查完成: 无止损触发")
    
    def _step_d_signal_generation(self, trade_date: str) -> None:
        """
        Step D: 信号生成（Hunter扫描）
        
        Args:
            trade_date: 交易日期
        """
        current_time = datetime.now().strftime('%H:%M')
        
        # 运行 Hunter 扫描
        result = self.hunter_service.run_scan(trade_date=trade_date)
        
        if not result.success:
            logger.error(f"[{current_time}] Hunter扫描失败: {result.error}")
            return
        
        if result.result_df.empty:
            logger.info(f"[{current_time}] Hunter扫描完成: 无符合条件的股票")
            return
        
        # 转换结果并保存
        predictions = []
        for _, row in result.result_df.iterrows():
            # 获取RPS值（如果存在）
            rps_60 = row.get('rps_60', 0)
            if pd.isna(rps_60):
                rps_60 = 0
            
            # 构建预测记录
            prediction = {
                'trade_date': trade_date,
                'ts_code': row['ts_code'],
                'name': row.get('name', ''),
                'ai_score': int(rps_60),
                'ai_reason': f"Alpha Trident筛选: RPS={rps_60:.1f}",
                'strategy_tag': row.get('strategy_tag', ''),
                'suggested_shares': int(row.get('suggested_shares', 0)) if pd.notna(row.get('suggested_shares')) else None,
                'price_at_prediction': float(row.get('close', 0)) if pd.notna(row.get('close')) else None
            }
            predictions.append(prediction)
        
        # 保存到数据库
        if predictions:
            save_daily_predictions(predictions)
            logger.info(f"[{current_time}] Hunter信号已保存: {len(predictions)} 只股票")
        else:
            logger.warning(f"[{current_time}] 无有效预测记录可保存")
