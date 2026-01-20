"""
Hunter Service - 机会挖掘业务逻辑

提供Hunter（机会挖掘）功能的业务逻辑封装，包括：
- 数据获取
- 因子计算
- 策略筛选
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from .base_service import BaseService
from ..strategy import get_trade_date, AlphaStrategy
from ..factors import FactorPipeline, RPSFactor, MAFactor, VolumeRatioFactor, PEProxyFactor
from ..exceptions import DataFetchError, StrategyError, FactorError
from ..logging_config import get_logger

logger = get_logger(__name__)


class HunterResult:
    """
    Hunter扫描结果
    
    Attributes:
        success: 是否成功
        result_df: 筛选结果DataFrame
        trade_date: 交易日期
        diagnostics: 诊断信息字典
        error: 错误信息（如果失败）
    """
    
    def __init__(
        self,
        success: bool,
        result_df: Optional[pd.DataFrame] = None,
        trade_date: Optional[str] = None,
        diagnostics: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        初始化Hunter结果
        
        Args:
            success: 是否成功
            result_df: 筛选结果DataFrame，如果为None则创建空DataFrame
            trade_date: 交易日期 (YYYYMMDD)
            diagnostics: 诊断信息字典，如果为None则创建空字典
            error: 错误信息（如果失败）
        """
        self.success: bool = success
        self.result_df: pd.DataFrame = result_df if result_df is not None else pd.DataFrame()
        self.trade_date: Optional[str] = trade_date
        self.diagnostics: Dict[str, Any] = diagnostics if diagnostics is not None else {}
        self.error: Optional[str] = error


class HunterService(BaseService):
    """
    Hunter服务 - 机会挖掘业务逻辑
    
    提供基于Alpha Trident策略的智能选股功能，包括：
    1. 获取股票基础数据和历史数据
    2. 计算技术因子（RPS、MA、量比、PE等）
    3. 应用Alpha Trident策略筛选符合条件的股票
    """
    
    def run_scan(self, trade_date: Optional[str] = None) -> HunterResult:
        """
        执行Hunter扫描
        
        Args:
            trade_date: 交易日期，如果为None则使用当前交易日
            
        Returns:
            HunterResult: 扫描结果
        """
        try:
            # 1. 确定交易日期
            if trade_date is None:
                trade_date = get_trade_date()
            
            logger.info(f"Hunter 扫描开始，交易日期: {trade_date}")
            
            # 2. 获取基础数据
            try:
                basic_df = self.data_provider.get_daily_basic(trade_date)
                if basic_df.empty:
                    raise DataFetchError("无法获取基础数据")
            except Exception as e:
                if isinstance(e, DataFetchError):
                    raise
                raise DataFetchError(f"获取基础数据失败: {str(e)}") from e
            
            # 3. 获取历史日线数据
            # 考虑到节假日、停牌等因素，60个交易日约需要120个自然日
            history_days = self.config.get('hunter.history_days', 120)
            start_date = (
                datetime.strptime(trade_date, "%Y%m%d") - timedelta(days=history_days)
            ).strftime("%Y%m%d")
            
            try:
                history_df = self.data_provider.fetch_history_for_hunter(
                    trade_date=trade_date,
                    start_date=start_date,
                    index_code=None,  # 使用配置的指数
                    use_cache=True
                )
                
                if history_df.empty:
                    raise DataFetchError("无法获取历史日线数据")
            except Exception as e:
                if isinstance(e, DataFetchError):
                    raise
                raise DataFetchError(f"获取历史数据失败: {str(e)}") from e
            
            # 4. 合并数据
            # 确保trade_date格式一致（都是字符串格式 'YYYYMMDD'）
            if history_df['trade_date'].dtype != 'object':
                history_df['trade_date'] = history_df['trade_date'].astype(str)
            if basic_df['trade_date'].dtype != 'object':
                basic_df['trade_date'] = basic_df['trade_date'].astype(str)
            
            daily_df = history_df[history_df['trade_date'] == trade_date].copy()
            if daily_df.empty:
                logger.warning(f"目标交易日 {trade_date} 无数据，尝试使用最近交易日")
                # 尝试使用历史数据中的最近交易日
                if not history_df.empty:
                    available_dates = sorted(history_df['trade_date'].unique(), reverse=True)
                    if available_dates:
                        latest_date = str(available_dates[0])
                        logger.info(f"使用最近交易日: {latest_date}")
                        daily_df = history_df[history_df['trade_date'] == latest_date].copy()
                        trade_date = latest_date  # 更新trade_date为实际使用的日期
            
            if daily_df.empty:
                return HunterResult(
                    success=False,
                    error="无法获取目标交易日数据"
                )
            
            merged_df = basic_df.merge(daily_df, on=["ts_code", "trade_date"], how="inner")
            if merged_df.empty:
                return HunterResult(
                    success=False,
                    error="数据合并失败"
                )
            
            # 5. 准备因子计算数据（包含历史数据）
            valid_codes = set(merged_df['ts_code'].unique())
            history_for_factors = history_df[history_df['ts_code'].isin(valid_codes)].copy()
            
            # 诊断：检查每个股票的历史数据数量
            stock_data_counts = history_for_factors.groupby('ts_code').size()
            stocks_with_enough_data = (stock_data_counts >= 60).sum()
            
            # 合并历史数据到 merged_df（用于因子计算）
            basic_df_unique = basic_df[
                ['ts_code', 'name', 'list_date', 'pe_ttm', 'pb', 'mv', 'dividend_yield']
            ].drop_duplicates(subset=['ts_code'], keep='first')
            
            merged_df = history_for_factors.merge(
                basic_df_unique,
                on='ts_code',
                how='inner'
            )
            
            # 确保 trade_date 是 datetime 格式（因子计算需要）
            if 'trade_date' in merged_df.columns:
                if merged_df['trade_date'].dtype == 'object':
                    # 尝试转换为datetime
                    merged_df['trade_date'] = pd.to_datetime(
                        merged_df['trade_date'], 
                        format='%Y%m%d', 
                        errors='coerce'
                    )
                # 检查是否有转换失败的情况
                if merged_df['trade_date'].isna().any():
                    invalid_count = merged_df['trade_date'].isna().sum()
                    logger.warning(f"发现 {invalid_count} 条记录的trade_date转换失败，将过滤这些记录")
                    # 过滤掉无效日期的记录
                    merged_df = merged_df[merged_df['trade_date'].notna()].copy()
                    if merged_df.empty:
                        raise FactorError("所有记录的trade_date转换失败，无法继续计算因子")
            
            # 6. 计算因子
            try:
                enriched_df = self._compute_factors(merged_df)
            except Exception as e:
                raise FactorError(f"因子计算失败: {str(e)}") from e
            
            # 7. 应用策略
            try:
                result_df = self._apply_strategy(enriched_df, trade_date)
            except Exception as e:
                raise StrategyError(f"策略应用失败: {str(e)}") from e
            
            # 8. 构建诊断信息
            diagnostics = {
                'total_stocks': len(valid_codes),
                'stocks_with_enough_data': stocks_with_enough_data,
                'history_records': len(history_df),
                'enriched_records': len(enriched_df),
                'result_count': len(result_df)
            }
            
            # 添加RPS因子诊断
            if 'rps_60' in enriched_df.columns:
                rps_valid = enriched_df['rps_60'].notna().sum()
                if rps_valid > 0:
                    diagnostics['rps_stats'] = {
                        'valid_count': int(rps_valid),
                        'total_count': len(enriched_df),
                        'max': float(enriched_df['rps_60'].max()),
                        'min': float(enriched_df['rps_60'].min()),
                        'mean': float(enriched_df['rps_60'].mean()),
                        'above_85': int((enriched_df['rps_60'] > 85).sum())
                    }
            
            logger.info(f"Hunter 扫描完成: {len(result_df)} 只股票")
            
            return HunterResult(
                success=True,
                result_df=result_df,
                trade_date=trade_date,
                diagnostics=diagnostics
            )
            
        except (DataFetchError, StrategyError, FactorError) as e:
            logger.error(f"Hunter 扫描失败: {e}")
            return HunterResult(
                success=False,
                error=str(e)
            )
        except Exception as e:
            logger.exception("Hunter 扫描异常")
            return HunterResult(
                success=False,
                error=f"扫描过程出错: {str(e)}"
            )
    
    def _compute_factors(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算因子
        
        使用FactorPipeline计算以下因子：
        - RPS因子（相对强度）
        - MA因子（移动平均）
        - VolumeRatio因子（量比）
        - PEProxy因子（估值代理）
        
        Args:
            df: 包含历史数据的DataFrame，必须包含列：
                ts_code, trade_date, open, high, low, close, vol, pe_ttm
                
        Returns:
            包含因子列的DataFrame，新增列：
                rps_60, above_ma_20, vol_ratio_5, is_undervalued
                
        Raises:
            FactorError: 因子计算失败时抛出
        """
        # 从配置获取因子参数
        rps_window = self.config.get('factors.rps.window', 60)
        ma_window = self.config.get('factors.ma.window', 20)
        volume_ratio_window = self.config.get('factors.volume_ratio.window', 5)
        pe_max = self.config.get('factors.pe.max', 30)
        
        pipeline = FactorPipeline()
        pipeline.add(RPSFactor(window=rps_window))
        pipeline.add(MAFactor(window=ma_window))
        pipeline.add(VolumeRatioFactor(window=volume_ratio_window))
        pipeline.add(PEProxyFactor(max_pe=pe_max))
        
        return pipeline.run(df.copy())
    
    def _apply_strategy(
        self, 
        enriched_df: pd.DataFrame, 
        trade_date: str
    ) -> pd.DataFrame:
        """
        应用Alpha Trident策略
        
        筛选条件（从配置读取阈值）：
        1. rps_60 > threshold (默认85)
        2. is_undervalued == True
        3. vol_ratio_5 > threshold (默认1.5)
        4. above_ma_20 == True
        
        Args:
            enriched_df: 包含因子列的DataFrame，必须包含列：
                rps_60, is_undervalued, vol_ratio_5, above_ma_20
            trade_date: 目标交易日期 (YYYYMMDD)
            
        Returns:
            筛选后的DataFrame，包含列：
                ts_code, name, close, pe_ttm, rps_60, vol_ratio_5, strategy_tag
                按rps_60降序排序
                
        Raises:
            StrategyError: 策略应用失败时抛出
        """
        # 只使用目标交易日的数据进行策略筛选
        # 确保trade_date格式一致
        if pd.api.types.is_datetime64_any_dtype(enriched_df['trade_date']):
            # 如果是 datetime，转换为字符串进行比较
            enriched_df['trade_date_str'] = enriched_df['trade_date'].dt.strftime('%Y%m%d')
            target_date_df = enriched_df[enriched_df['trade_date_str'] == trade_date].copy()
            if 'trade_date_str' in target_date_df.columns:
                target_date_df = target_date_df.drop(columns=['trade_date_str'])
        else:
            # 确保是字符串格式
            enriched_df['trade_date'] = enriched_df['trade_date'].astype(str)
            target_date_df = enriched_df[enriched_df['trade_date'] == trade_date].copy()
        
        # 去重
        before_dedup = len(target_date_df)
        target_date_df = target_date_df.drop_duplicates(subset=['ts_code'], keep='first')
        if len(target_date_df) < before_dedup:
            logger.warning(f"发现重复股票记录，已去重: {before_dedup} -> {len(target_date_df)}")
        
        if target_date_df.empty:
            return pd.DataFrame()
        
        strategy = AlphaStrategy(target_date_df, self.config)
        return strategy.filter_alpha_trident()
