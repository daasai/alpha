"""
Hunter Service - 猎场业务逻辑适配层
"""
from typing import Dict, Any, Optional, List
import pandas as pd

from src.services.hunter_service import HunterService as CoreHunterService, HunterResult
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.logging_config import get_logger

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
            
            # 转换DataFrame为列表
            results_list = []
            if not result.result_df.empty:
                for idx, row in result.result_df.iterrows():
                    try:
                        # 计算涨跌幅（如果有历史数据）
                        change_percent = 0.0
                        if 'pct_chg' in row and pd.notna(row['pct_chg']):
                            change_percent = float(row['pct_chg'])
                        
                        # 获取AI分析（如果有）
                        ai_analysis = None
                        if 'ai_analysis' in row and pd.notna(row['ai_analysis']):
                            ai_analysis = str(row['ai_analysis'])
                        
                        # 确保所有必需字段都存在且有有效值
                        ts_code = str(row.get('ts_code', '')) if pd.notna(row.get('ts_code')) else ''
                        name = str(row.get('name', '')) if pd.notna(row.get('name')) else '未知'
                        price = float(row.get('close', 0)) if pd.notna(row.get('close')) else 0.0
                        rps = float(row.get('rps_60', 0)) if pd.notna(row.get('rps_60')) else 0.0
                        volume_ratio = float(row.get('vol_ratio_5', 0)) if pd.notna(row.get('vol_ratio_5')) else 0.0
                        
                        if not ts_code:
                            logger.warning(f"跳过无效记录（缺少ts_code）: idx={idx}")
                            continue
                        
                        results_list.append({
                            "id": f"{ts_code}_{idx}",
                            "code": ts_code,
                            "name": name,
                            "price": price,
                            "change_percent": change_percent,
                            "rps": rps,
                            "volume_ratio": volume_ratio,
                            "ai_analysis": ai_analysis
                        })
                    except Exception as e:
                        logger.warning(f"处理结果行时出错（idx={idx}）: {e}")
                        continue
            
            # Convert diagnostics to JSON-serializable format
            diagnostics_serializable = None
            if result.diagnostics:
                diagnostics_serializable = {}
                for key, value in result.diagnostics.items():
                    if isinstance(value, (pd.Series, pd.DataFrame)):
                        continue  # Skip pandas objects
                    elif hasattr(value, 'item'):  # numpy scalar
                        diagnostics_serializable[key] = value.item()
                    elif isinstance(value, dict):
                        diagnostics_serializable[key] = {
                            k: v.item() if hasattr(v, 'item') else v
                            for k, v in value.items()
                        }
                    else:
                        diagnostics_serializable[key] = value
            
            return {
                "success": True,
                "trade_date": result.trade_date,
                "results": results_list,
                "diagnostics": diagnostics_serializable,
                "error": None
            }
            
        except Exception as e:
            logger.exception("Hunter扫描异常")
            # 恢复原始配置
            if original_rps is not None:
                self.core_service.config.config['strategy']['alpha_trident']['rps_threshold'] = original_rps
            if original_vol_ratio is not None:
                self.core_service.config.config['strategy']['alpha_trident']['vol_ratio_threshold'] = original_vol_ratio
            
            return {
                "success": False,
                "trade_date": trade_date,
                "results": [],
                "diagnostics": None,
                "error": str(e)
            }
    
    def get_filters(self) -> Dict[str, Any]:
        """
        获取可用筛选条件
        
        Returns:
            筛选条件配置字典
        """
        config = self.core_service.config
        
        return {
            "rps_threshold": {
                "default": config.get('strategy.alpha_trident.rps_threshold', 85),
                "min": 50,
                "max": 100,
                "step": 1
            },
            "volume_ratio_threshold": {
                "default": config.get('strategy.alpha_trident.vol_ratio_threshold', 1.5),
                "min": 0.0,
                "max": 10.0,
                "step": 0.1
            },
            "pe_max": {
                "default": config.get('strategy.alpha_trident.pe_max', 30),
                "min": 5,
                "max": 100,
                "step": 1
            }
        }
