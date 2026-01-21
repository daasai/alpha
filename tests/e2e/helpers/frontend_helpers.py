"""
Frontend Test Helpers
前端测试辅助函数（用于模拟前端行为）
"""
from typing import Dict, Any, Optional
import json


def simulate_frontend_api_call(
    api_response: Dict[str, Any],
    expected_fields: list
) -> Dict[str, Any]:
    """
    模拟前端API调用和数据处理
    
    Args:
        api_response: API响应数据
        expected_fields: 期望的字段列表
        
    Returns:
        处理后的数据
    """
    result = {
        'success': False,
        'data': None,
        'errors': [],
    }
    
    if api_response.get('status_code') != 200:
        result['errors'].append(f"API返回错误状态码: {api_response.get('status_code')}")
        return result
    
    data = api_response.get('data', {})
    
    # 检查success字段
    if not data.get('success', False):
        result['errors'].append("API响应success字段为False")
        return result
    
    # 提取data字段
    response_data = data.get('data')
    if response_data is None:
        result['errors'].append("API响应缺少data字段")
        return result
    
    # 检查必需字段
    missing_fields = []
    for field in expected_fields:
        if field not in response_data:
            missing_fields.append(field)
    
    if missing_fields:
        result['errors'].append(f"缺少必需字段: {', '.join(missing_fields)}")
        return result
    
    result['success'] = True
    result['data'] = response_data
    
    return result


def format_portfolio_nav(nav: float) -> str:
    """
    格式化组合净值（模拟前端格式化）
    
    Args:
        nav: 净值数值
        
    Returns:
        格式化后的字符串
    """
    return f"¥{nav:,.0f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    格式化百分比（模拟前端格式化）
    
    Args:
        value: 百分比值
        decimals: 小数位数
        
    Returns:
        格式化后的字符串
    """
    sign = '+' if value > 0 else ''
    return f"{sign}{value:.{decimals}f}%"


def validate_chart_data(data: list) -> tuple[bool, list]:
    """
    验证图表数据格式
    
    Args:
        data: 图表数据列表
        
    Returns:
        (是否有效, 错误列表)
    """
    errors = []
    
    if not isinstance(data, list):
        errors.append("图表数据必须是列表")
        return False, errors
    
    if len(data) == 0:
        errors.append("图表数据为空")
        return False, errors
    
    required_fields = ['date', 'price', 'bbi']
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            errors.append(f"数据点{i}: 必须是字典")
            continue
        
        for field in required_fields:
            if field not in item:
                errors.append(f"数据点{i}: 缺少字段 {field}")
    
    return len(errors) == 0, errors
