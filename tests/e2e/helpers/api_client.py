"""
API Client Helper for E2E Tests
提供测试用的API客户端
"""
from fastapi.testclient import TestClient
from typing import Dict, Any, Optional
import json


class E2EAPIClient:
    """测试用API客户端（E2E测试辅助类）"""
    
    def __init__(self, app):
        """
        初始化测试客户端
        
        Args:
            app: FastAPI应用实例
        """
        self.client = TestClient(app)
    
    def get_dashboard_overview(self, trade_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取Dashboard概览
        
        Args:
            trade_date: 交易日期 (YYYYMMDD)
            
        Returns:
            API响应
        """
        params = {}
        if trade_date:
            params['trade_date'] = trade_date
        
        response = self.client.get("/api/dashboard/overview", params=params)
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    def get_market_trend(
        self,
        days: int = 60,
        index_code: str = "000001.SH"
    ) -> Dict[str, Any]:
        """
        获取市场趋势数据
        
        Args:
            days: 获取天数
            index_code: 指数代码
            
        Returns:
            API响应
        """
        params = {
            'days': days,
            'index_code': index_code,
        }
        
        response = self.client.get("/api/dashboard/market-trend", params=params)
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    def validate_response_schema(
        self,
        response_data: Dict[str, Any],
        schema: Dict[str, Any],
        path: str = ""
    ) -> tuple:
        """
        验证响应数据是否符合schema
        
        Args:
            response_data: 响应数据
            schema: schema定义
            path: 当前路径（用于错误报告）
            
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        if not isinstance(response_data, dict):
            errors.append(f"{path}: 期望dict，得到{type(response_data).__name__}")
            return False, errors
        
        for key, expected_type in schema.items():
            current_path = f"{path}.{key}" if path else key
            
            if key not in response_data:
                errors.append(f"{current_path}: 缺少必需字段")
                continue
            
            value = response_data[key]
            
            # 处理类型元组（允许多种类型）
            if isinstance(expected_type, tuple):
                if not any(isinstance(value, t) for t in expected_type if t is not type(None)):
                    if type(None) in expected_type and value is None:
                        continue
                    type_names = [t.__name__ if t is not type(None) else 'None' for t in expected_type]
                    errors.append(f"{current_path}: 期望类型 {', '.join(type_names)}，得到 {type(value).__name__}")
            elif isinstance(expected_type, dict):
                # 递归验证嵌套字典
                if not isinstance(value, dict):
                    errors.append(f"{current_path}: 期望dict，得到{type(value).__name__}")
                else:
                    valid, nested_errors = self.validate_response_schema(value, expected_type, current_path)
                    if not valid:
                        errors.extend(nested_errors)
            elif isinstance(expected_type, list):
                # 列表类型（简化处理）
                if not isinstance(value, list):
                    errors.append(f"{current_path}: 期望list，得到{type(value).__name__}")
            else:
                # 单一类型
                if not isinstance(value, expected_type):
                    errors.append(f"{current_path}: 期望类型 {expected_type.__name__}，得到 {type(value).__name__}")
        
        return len(errors) == 0, errors
    
    def get_hunter_filters(self) -> Dict[str, Any]:
        """
        获取Hunter筛选条件
        
        Returns:
            API响应
        """
        response = self.client.get("/api/hunter/filters")
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    def scan_hunter(
        self,
        rps_threshold: Optional[float] = None,
        volume_ratio_threshold: Optional[float] = None,
        trade_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行Hunter扫描
        
        Args:
            rps_threshold: RPS阈值
            volume_ratio_threshold: 量比阈值
            trade_date: 交易日期 (YYYYMMDD)
            
        Returns:
            API响应
        """
        request_data = {}
        if rps_threshold is not None:
            request_data['rps_threshold'] = rps_threshold
        if volume_ratio_threshold is not None:
            request_data['volume_ratio_threshold'] = volume_ratio_threshold
        if trade_date is not None:
            request_data['trade_date'] = trade_date
        
        response = self.client.post("/api/hunter/scan", json=request_data)
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    # ========== Portfolio API Methods ==========
    
    def get_portfolio_positions(self) -> Dict[str, Any]:
        """
        获取持仓列表
        
        Returns:
            API响应
        """
        response = self.client.get("/api/portfolio/positions")
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """
        获取组合指标
        
        Returns:
            API响应
        """
        response = self.client.get("/api/portfolio/metrics")
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    def add_position(
        self,
        code: str,
        name: str,
        cost: float,
        shares: Optional[int] = None,
        stop_loss_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        添加持仓
        
        Args:
            code: 股票代码
            name: 股票名称
            cost: 成本价
            shares: 持仓数量（可选）
            stop_loss_price: 止损价（可选）
            
        Returns:
            API响应
        """
        request_data = {
            'code': code,
            'name': name,
            'cost': cost,
        }
        if shares is not None:
            request_data['shares'] = shares
        if stop_loss_price is not None:
            request_data['stop_loss_price'] = stop_loss_price
        
        response = self.client.post("/api/portfolio/positions", json=request_data)
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code in [200, 201] else None,
            'error': response.json() if response.status_code not in [200, 201] else None,
        }
    
    def update_position(
        self,
        position_id: str,
        cost: Optional[float] = None,
        shares: Optional[int] = None,
        stop_loss_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        更新持仓
        
        Args:
            position_id: 持仓ID
            cost: 成本价（可选）
            shares: 持仓数量（可选）
            stop_loss_price: 止损价（可选）
            
        Returns:
            API响应
        """
        request_data = {}
        if cost is not None:
            request_data['cost'] = cost
        if shares is not None:
            request_data['shares'] = shares
        if stop_loss_price is not None:
            request_data['stop_loss_price'] = stop_loss_price
        
        response = self.client.put(f"/api/portfolio/positions/{position_id}", json=request_data)
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    def delete_position(self, position_id: str) -> Dict[str, Any]:
        """
        删除持仓
        
        Args:
            position_id: 持仓ID
            
        Returns:
            API响应
        """
        response = self.client.delete(f"/api/portfolio/positions/{position_id}")
        # 204 No Content 没有响应体
        if response.status_code == 204:
            return {
                'status_code': response.status_code,
                'data': None,
                'error': None,
            }
        else:
            return {
                'status_code': response.status_code,
                'data': None,
                'error': response.json() if response.content else None,
            }
    
    def refresh_prices(self) -> Dict[str, Any]:
        """
        刷新持仓价格
        
        Returns:
            API响应
        """
        response = self.client.post("/api/portfolio/refresh-prices")
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
    
    def execute_buy(
        self,
        ts_code: str,
        price: float,
        volume: int,
        strategy_tag: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行买入订单
        
        Args:
            ts_code: 股票代码
            price: 买入价格
            volume: 买入数量
            strategy_tag: 策略标签（可选）
            
        Returns:
            API响应
        """
        request_data = {
            'ts_code': ts_code,
            'price': price,
            'volume': volume,
        }
        if strategy_tag is not None:
            request_data['strategy_tag'] = strategy_tag
        
        response = self.client.post("/api/portfolio/buy", json=request_data)
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code in [200, 201] else None,
            'error': response.json() if response.status_code not in [200, 201] else None,
        }
    
    def execute_sell(
        self,
        ts_code: str,
        price: float,
        volume: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行卖出订单
        
        Args:
            ts_code: 股票代码
            price: 卖出价格
            volume: 卖出数量
            reason: 卖出原因（可选）
            
        Returns:
            API响应
        """
        request_data = {
            'ts_code': ts_code,
            'price': price,
            'volume': volume,
        }
        if reason is not None:
            request_data['reason'] = reason
        
        response = self.client.post("/api/portfolio/sell", json=request_data)
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code in [200, 201] else None,
            'error': response.json() if response.status_code not in [200, 201] else None,
        }
    
    def get_account(self) -> Dict[str, Any]:
        """
        获取账户信息
        
        Returns:
            API响应
        """
        response = self.client.get("/api/portfolio/account")
        return {
            'status_code': response.status_code,
            'data': response.json() if response.status_code == 200 else None,
            'error': response.json() if response.status_code != 200 else None,
        }
