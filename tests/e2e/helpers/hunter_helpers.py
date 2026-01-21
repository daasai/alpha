"""
Hunter Test Helpers
Hunter测试辅助函数
"""
from typing import Dict, Any, List, Optional
import json


def validate_scan_results(
    results: List[Dict[str, Any]],
    rps_threshold: float,
    volume_ratio_threshold: float
) -> tuple[bool, list]:
    """
    验证扫描结果是否符合筛选条件
    
    Args:
        results: 扫描结果列表
        rps_threshold: RPS阈值
        volume_ratio_threshold: 量比阈值
        
    Returns:
        (是否有效, 错误列表)
    """
    errors = []
    
    if not isinstance(results, list):
        errors.append("扫描结果必须是列表")
        return False, errors
    
    for i, result in enumerate(results):
        if not isinstance(result, dict):
            errors.append(f"结果项{i}: 必须是字典")
            continue
        
        # 验证必需字段
        required_fields = ['id', 'code', 'name', 'price', 'change_percent', 'rps', 'volume_ratio']
        for field in required_fields:
            if field not in result:
                errors.append(f"结果项{i}: 缺少字段 {field}")
        
        # 验证筛选条件
        if 'rps' in result:
            rps = result['rps']
            if rps < rps_threshold:
                errors.append(f"结果项{i}: RPS值 {rps} 低于阈值 {rps_threshold}")
        
        if 'volume_ratio' in result:
            vol_ratio = result['volume_ratio']
            if vol_ratio < volume_ratio_threshold:
                errors.append(f"结果项{i}: 量比 {vol_ratio} 低于阈值 {volume_ratio_threshold}")
    
    return len(errors) == 0, errors


def validate_rps_value(rps: float) -> tuple[bool, str]:
    """
    验证RPS值是否在有效范围内
    
    Args:
        rps: RPS值
        
    Returns:
        (是否有效, 错误信息)
    """
    if not isinstance(rps, (int, float)):
        return False, f"RPS值必须是数值类型，得到 {type(rps).__name__}"
    
    if rps < 0 or rps > 100:
        return False, f"RPS值必须在0-100范围内，得到 {rps}"
    
    return True, ""


def simulate_frontend_filter(
    results: List[Dict[str, Any]],
    rps_threshold: float
) -> List[Dict[str, Any]]:
    """
    模拟前端筛选逻辑
    
    Args:
        results: 原始结果列表
        rps_threshold: RPS阈值（前端筛选使用 rps >= rpsThreshold - 20）
        
    Returns:
        筛选后的结果列表
    """
    if not results:
        return []
    
    filtered = [
        item for item in results
        if item.get('rps', 0) >= rps_threshold - 20
    ]
    
    return filtered


def format_stock_code(code: str) -> str:
    """
    格式化股票代码（模拟前端格式化）
    
    Args:
        code: 股票代码（如 000001.SZ）
        
    Returns:
        格式化后的代码
    """
    return code


def format_price(price: float) -> str:
    """
    格式化价格（模拟前端格式化）
    
    Args:
        price: 价格数值
        
    Returns:
        格式化后的字符串
    """
    return f"{price:.2f}"


def format_percentage(value: float) -> str:
    """
    格式化百分比（模拟前端格式化）
    
    Args:
        value: 百分比值
        
    Returns:
        格式化后的字符串
    """
    sign = '+' if value > 0 else ''
    return f"{sign}{value:.2f}%"


def validate_filters_response(data: Dict[str, Any]) -> tuple[bool, list]:
    """
    验证筛选条件响应格式
    
    Args:
        data: 响应数据
        
    Returns:
        (是否有效, 错误列表)
    """
    errors = []
    
    if not isinstance(data, dict):
        errors.append("筛选条件响应必须是字典")
        return False, errors
    
    required_keys = ['rps_threshold', 'volume_ratio_threshold', 'pe_max']
    for key in required_keys:
        if key not in data:
            errors.append(f"缺少筛选条件: {key}")
            continue
        
        threshold_config = data[key]
        if not isinstance(threshold_config, dict):
            errors.append(f"{key}: 必须是字典")
            continue
        
        required_config_keys = ['default', 'min', 'max', 'step']
        for config_key in required_config_keys:
            if config_key not in threshold_config:
                errors.append(f"{key}.{config_key}: 缺少配置项")
    
    return len(errors) == 0, errors
