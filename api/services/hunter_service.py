"""
Hunter Service - 猎场业务逻辑适配层
"""
from typing import Dict, Any, Optional, List
import pandas as pd

from src.services.hunter_service import HunterService as CoreHunterService, HunterResult
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.logging_config import get_logger
from api.schemas.hunter import StockSignal

logger = get_logger(__name__)


class APIHunterService:
    """Hunter API服务层（适配器）"""
    
    def __init__(self, data_provider: DataProvider, config: ConfigManager):
        self.core_service = CoreHunterService(data_provider=data_provider, config=config)
    
    def run_scan(
        self,
        trade_date: Optional[str] = None,
        rps_threshold: Optional[float] = None,
        volume_ratio_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        执行Hunter扫描
        
        Args:
            trade_date: 交易日期
            rps_threshold: RPS阈值（如果提供，会临时更新配置）
            volume_ratio_threshold: 量比阈值（如果提供，会临时更新配置）
            
        Returns:
            扫描结果字典
        """
        # 如果提供了阈值，临时更新配置
        original_rps = None
        original_vol_ratio = None
        
        if rps_threshold is not None:
            original_rps = self.core_service.config.get('strategy.alpha_trident.rps_threshold')
            self.core_service.config.config['strategy']['alpha_trident']['rps_threshold'] = rps_threshold
        
        if volume_ratio_threshold is not None:
            original_vol_ratio = self.core_service.config.get('strategy.alpha_trident.vol_ratio_threshold')
            self.core_service.config.config['strategy']['alpha_trident']['vol_ratio_threshold'] = volume_ratio_threshold
        
        try:
            # 执行扫描
            result: HunterResult = self.core_service.run_scan(trade_date)
            
            # 恢复原始配置
            if original_rps is not None:
                self.core_service.config.config['strategy']['alpha_trident']['rps_threshold'] = original_rps
            if original_vol_ratio is not None:
                self.core_service.config.config['strategy']['alpha_trident']['vol_ratio_threshold'] = original_vol_ratio
            
            # 转换结果
            if not result.success:
                return {
                    "success": False,
                    "trade_date": result.trade_date,
                    "results": [],
                    "diagnostics": None,
                    "error": result.error
                }
            
            # 转换DataFrame为StockSignal列表
            results_list: List[StockSignal] = []
            if not result.result_df.empty:
                # 确保结果按RPS降序排序（策略层已经排序，但这里再次确保）
                sorted_df = result.result_df.copy()
                if 'rps_60' in sorted_df.columns:
                    sorted_df = sorted_df.sort_values('rps_60', ascending=False, na_position='last')
                
                for idx, (_, row) in enumerate(sorted_df.iterrows()):
                    try:
                        # 确保所有必需字段都存在且有有效值
                        ts_code = str(row.get('ts_code', '')) if pd.notna(row.get('ts_code')) else ''
                        if not ts_code:
                            logger.warning(f"跳过无效记录（缺少ts_code）: idx={idx}")
                            continue
                        
                        # 获取股票名称
                        name = str(row.get('name', '')) if pd.notna(row.get('name')) else '未知'
                        
                        # 获取价格，确保是有效数值
                        price = 0.0
                        if 'close' in row and pd.notna(row.get('close')):
                            try:
                                price = float(row.get('close'))
                                if price < 0:
                                    logger.warning(f"股票 {ts_code} 价格异常: {price}")
                                    price = 0.0
                            except (ValueError, TypeError):
                                logger.warning(f"股票 {ts_code} 价格转换失败: {row.get('close')}")
                        
                        # 获取RPS值，确保在0-100范围内
                        rps = 0.0
                        if 'rps_60' in row and pd.notna(row.get('rps_60')):
                            try:
                                rps = float(row.get('rps_60'))
                                # 确保RPS值在0-100范围内
                                rps = max(0.0, min(100.0, rps))
                            except (ValueError, TypeError):
                                logger.warning(f"股票 {ts_code} RPS值转换失败: {row.get('rps_60')}")
                                rps = 0.0
                        else:
                            logger.warning(f"股票 {ts_code} RPS值为空，使用默认值0")
                        
                        # 获取量比，确保是有效数值
                        volume_ratio = 0.0
                        if 'vol_ratio_5' in row and pd.notna(row.get('vol_ratio_5')):
                            try:
                                volume_ratio = float(row.get('vol_ratio_5'))
                                if volume_ratio < 0:
                                    logger.warning(f"股票 {ts_code} 量比异常: {volume_ratio}")
                                    volume_ratio = 0.0
                            except (ValueError, TypeError):
                                logger.warning(f"股票 {ts_code} 量比转换失败: {row.get('vol_ratio_5')}")
                        
                        # 获取PE值
                        pe = None
                        if 'pe_ttm' in row and pd.notna(row.get('pe_ttm')):
                            try:
                                pe_val = float(row.get('pe_ttm'))
                                if pe_val > 0:
                                    pe = pe_val
                            except (ValueError, TypeError):
                                pass
                        
                        # 获取行业信息（当前数据提供者不包含，设置为None）
                        industry = None
                        # 如果将来数据提供者包含行业信息，可以在这里提取
                        # if 'industry' in row and pd.notna(row.get('industry')):
                        #     industry = str(row.get('industry'))
                        
                        # 生成原因字段
                        reason = None
                        strategy_tag = row.get('strategy_tag', '')
                        if strategy_tag:
                            reason = f"Alpha Trident筛选: RPS={rps:.1f}, 量比={volume_ratio:.1f}x"
                        else:
                            reason = f"Alpha Trident筛选: RPS={rps:.1f}, 量比={volume_ratio:.1f}x"
                        
                        # 创建StockSignal对象
                        signal = StockSignal(
                            code=ts_code,
                            name=name,
                            price=price,
                            rps=rps,
                            volume_ratio=volume_ratio,
                            pe=pe,
                            industry=industry,
                            reason=reason
                        )
                        results_list.append(signal)
                    except Exception as e:
                        logger.warning(f"处理结果行时出错（idx={idx}）: {e}", exc_info=True)
                        continue
            
            # Convert diagnostics to JSON-serializable format
            diagnostics_serializable = None
            if result.diagnostics:
                diagnostics_serializable = {}
                for key, value in result.diagnostics.items():
                    try:
                        if isinstance(value, (pd.Series, pd.DataFrame)):
                            continue  # Skip pandas objects
                        elif hasattr(value, 'item'):  # numpy scalar
                            diagnostics_serializable[key] = value.item()
                        elif isinstance(value, dict):
                            # Recursively convert dict values
                            converted_dict = {}
                            for k, v in value.items():
                                if isinstance(v, (pd.Series, pd.DataFrame)):
                                    continue
                                elif hasattr(v, 'item'):
                                    converted_dict[k] = v.item()
                                elif isinstance(v, (int, float, str, bool, type(None))):
                                    converted_dict[k] = v
                                elif isinstance(v, dict):
                                    # Recursive conversion for nested dicts
                                    converted_dict[k] = {
                                        k2: v2.item() if hasattr(v2, 'item') else v2
                                        for k2, v2 in v.items()
                                        if not isinstance(v2, (pd.Series, pd.DataFrame))
                                    }
                                else:
                                    converted_dict[k] = str(v)  # Fallback to string
                            diagnostics_serializable[key] = converted_dict
                        elif isinstance(value, (int, float, str, bool, type(None))):
                            diagnostics_serializable[key] = value
                        else:
                            # Fallback: convert to string for unknown types
                            diagnostics_serializable[key] = str(value)
                    except Exception as e:
                        logger.warning(f"诊断信息序列化失败 (key={key}): {e}")
                        continue
            
            # 将StockSignal列表转换为字典列表（用于JSON序列化）
            results_dict_list = [signal.model_dump() for signal in results_list]
            
            return {
                "success": True,
                "trade_date": result.trade_date,
                "results": results_dict_list,
                "diagnostics": diagnostics_serializable,
                "error": None
            }
            
        except Exception as e:
            logger.exception("Hunter扫描异常")
            # 恢复原始配置
            try:
                if original_rps is not None:
                    self.core_service.config.config['strategy']['alpha_trident']['rps_threshold'] = original_rps
                if original_vol_ratio is not None:
                    self.core_service.config.config['strategy']['alpha_trident']['vol_ratio_threshold'] = original_vol_ratio
            except Exception as restore_error:
                logger.error(f"恢复配置失败: {restore_error}")
            
            # 提供更详细的错误信息
            error_message = str(e)
            if not error_message:
                error_message = "扫描过程发生未知错误"
            
            return {
                "success": False,
                "trade_date": trade_date,
                "results": [],
                "diagnostics": None,
                "error": error_message
            }
    
    def get_filters(self) -> Dict[str, Any]:
        """
        获取可用筛选条件
        
        Returns:
            筛选条件配置字典
        """
        try:
            config = self.core_service.config
            
            # 获取配置值，确保类型正确
            rps_default = config.get('strategy.alpha_trident.rps_threshold', 85)
            vol_ratio_default = config.get('strategy.alpha_trident.vol_ratio_threshold', 1.5)
            pe_max_default = config.get('strategy.alpha_trident.pe_max', 30)
            
            # 验证和修正默认值
            rps_default = max(50, min(100, float(rps_default))) if rps_default is not None else 85
            vol_ratio_default = max(0.0, min(10.0, float(vol_ratio_default))) if vol_ratio_default is not None else 1.5
            pe_max_default = max(5, min(100, int(pe_max_default))) if pe_max_default is not None else 30
            
            # 生成可用交易日期列表（最近30个交易日）
            available_dates = self._generate_trade_dates(30)
            
            return {
                "rps_threshold": {
                    "default": rps_default,
                    "min": 50,
                    "max": 100,
                    "step": 1
                },
                "volume_ratio_threshold": {
                    "default": vol_ratio_default,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1
                },
                "pe_max": {
                    "default": pe_max_default,
                    "min": 5,
                    "max": 100,
                    "step": 1
                },
                "available_dates": available_dates
            }
        except Exception as e:
            logger.exception("获取筛选条件失败")
            # 返回默认值作为降级方案
            return {
                "rps_threshold": {
                    "default": 85,
                    "min": 50,
                    "max": 100,
                    "step": 1
                },
                "volume_ratio_threshold": {
                    "default": 1.5,
                    "min": 0.0,
                    "max": 10.0,
                    "step": 0.1
                },
                "pe_max": {
                    "default": 30,
                    "min": 5,
                    "max": 100,
                    "step": 1
                },
                "available_dates": []
            }
    
    def _generate_trade_dates(self, count: int = 30) -> List[Dict[str, str]]:
        """
        生成可用交易日期列表
        
        Args:
            count: 需要生成的交易日数量
            
        Returns:
            交易日期选项列表，格式: [{"value": "20241220", "label": "2024-12-20"}, ...]
        """
        from datetime import datetime, timedelta
        from src.strategy import get_trade_date
        
        dates = []
        current_date = datetime.now()
        
        # 如果当前时间 < 17:00，从昨天开始
        if current_date.hour < 17:
            current_date = current_date - timedelta(days=1)
        
        # 生成最近N个交易日
        date_obj = current_date
        generated_count = 0
        
        while generated_count < count:
            # 跳过周末
            while date_obj.weekday() >= 5:
                date_obj -= timedelta(days=1)
            
            # 格式化日期
            date_str = date_obj.strftime("%Y%m%d")
            date_label = date_obj.strftime("%Y-%m-%d")
            
            dates.append({
                "value": date_str,
                "label": date_label
            })
            
            generated_count += 1
            date_obj -= timedelta(days=1)
            
            # 防止无限循环
            if (current_date - date_obj).days > count * 2:
                break
        
        return dates
