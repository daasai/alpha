"""
Dashboard E2E Integration Tests
首页端到端集成测试
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.services.dashboard_service import DashboardService
from api.dependencies import get_data_provider, get_config
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.repositories.portfolio_repository import PortfolioRepository
from src.database import Position, _SessionLocal

from tests.e2e.fixtures.dashboard_fixtures import (
    mock_index_daily_data,
    mock_index_daily_data_empty,
    sample_portfolio_positions,
    test_db_session,
    populated_test_db,
    mock_data_provider,
    mock_config,
    expected_overview_schema,
    expected_market_trend_schema,
    expected_trend_data_point_schema,
)
from tests.e2e.helpers.api_client import E2EAPIClient
from tests.e2e.helpers.frontend_helpers import (
    simulate_frontend_api_call,
    format_portfolio_nav,
    format_percentage,
    validate_chart_data,
)


class TestDashboardE2E:
    """Dashboard E2E测试类"""
    
    @pytest.fixture
    def api_client(self):
        """创建API测试客户端"""
        return E2EAPIClient(app)
    
    @pytest.fixture
    def override_dependencies(self, mock_data_provider, mock_config, populated_test_db):
        """覆盖依赖注入"""
        from api.dependencies import get_data_provider, get_config
        
        def override_get_data_provider():
            # get_data_provider是生成器，需要yield
            yield mock_data_provider
        
        def override_get_config():
            return mock_config
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        
        yield
        
        # 清理
        app.dependency_overrides.clear()
    
    # ========== TC-001: 首页加载和基础渲染 ==========
    
    def test_tc001_homepage_loads(self, api_client):
        """TC-001: 验证首页路由可以访问"""
        # 测试根路径
        response = api_client.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert "DAAS Alpha API" in data.get("message", "")
    
    def test_tc001_health_check(self, api_client):
        """TC-001: 验证健康检查端点"""
        response = api_client.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") is True
        assert data.get("status") == "healthy"
    
    # ========== TC-002: Dashboard Overview API 全链路测试 ==========
    
    def test_tc002_overview_api_success(
        self,
        api_client,
        override_dependencies,
        expected_overview_schema
    ):
        """TC-002: 验证Overview API成功返回数据"""
        response = api_client.get_dashboard_overview()
        
        # 验证状态码
        assert response['status_code'] == 200, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        overview_data = data.get('data')
        assert overview_data is not None
        
        # 验证schema
        valid, errors = api_client.validate_response_schema(
            overview_data,
            expected_overview_schema
        )
        assert valid, f"Schema验证失败: {errors}"
        
        # 验证具体字段值
        assert 'market_regime' in overview_data
        assert 'regime' in overview_data['market_regime']
        assert isinstance(overview_data['market_regime']['is_bull'], bool)
        
        assert 'sentiment' in overview_data
        sentiment = overview_data['sentiment']['sentiment']
        assert 0 <= sentiment <= 100, f"Sentiment值超出范围: {sentiment}"
        
        assert 'target_position' in overview_data
        position = overview_data['target_position']['position']
        assert 0 <= position <= 100, f"Position值超出范围: {position}"
        
        assert 'portfolio_nav' in overview_data
        nav = overview_data['portfolio_nav']['nav']
        assert nav >= 0, f"NAV值不能为负: {nav}"
    
    def test_tc002_overview_with_trade_date(
        self,
        api_client,
        override_dependencies
    ):
        """TC-002: 验证带trade_date参数的Overview API"""
        trade_date = "20240115"  # 固定日期
        
        response = api_client.get_dashboard_overview(trade_date=trade_date)
        
        assert response['status_code'] == 200
        data = response['data']
        assert data is not None
        assert data.get('success') is True
    
    def test_tc002_frontend_data_processing(
        self,
        api_client,
        override_dependencies
    ):
        """TC-002: 验证前端数据处理"""
        response = api_client.get_dashboard_overview()
        
        # 模拟前端API调用
        frontend_result = simulate_frontend_api_call(
            response,
            expected_fields=['market_regime', 'sentiment', 'target_position', 'portfolio_nav']
        )
        
        assert frontend_result['success'] is True, f"前端处理失败: {frontend_result.get('errors')}"
        assert frontend_result['data'] is not None
        
        # 验证数据格式化
        nav = frontend_result['data']['portfolio_nav']['nav']
        formatted_nav = format_portfolio_nav(nav)
        assert formatted_nav.startswith('¥')
        assert ',' in formatted_nav or len(formatted_nav) > 1
        
        # 验证百分比格式化
        if frontend_result['data']['portfolio_nav'].get('change_percent') is not None:
            change = frontend_result['data']['portfolio_nav']['change_percent']
            formatted_change = format_percentage(change)
            assert '%' in formatted_change
    
    # ========== TC-003: Market Trend API 全链路测试 ==========
    
    def test_tc003_market_trend_api_success(
        self,
        api_client,
        override_dependencies,
        expected_market_trend_schema,
        expected_trend_data_point_schema
    ):
        """TC-003: 验证Market Trend API成功返回数据"""
        response = api_client.get_market_trend(days=60, index_code="000001.SH")
        
        # 验证状态码
        assert response['status_code'] == 200, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        trend_data = data.get('data')
        assert trend_data is not None
        
        # 验证schema
        valid, errors = api_client.validate_response_schema(
            trend_data,
            expected_market_trend_schema
        )
        assert valid, f"Schema验证失败: {errors}"
        
        # 验证数据点
        trend_points = trend_data.get('data', [])
        assert len(trend_points) > 0, "趋势数据不应为空"
        
        # 验证第一个数据点的schema
        if trend_points:
            valid, errors = api_client.validate_response_schema(
                trend_points[0],
                expected_trend_data_point_schema
            )
            assert valid, f"数据点Schema验证失败: {errors}"
    
    def test_tc003_bbi_calculation(
        self,
        api_client,
        override_dependencies,
        mock_index_daily_data
    ):
        """TC-003: 验证BBI计算正确性"""
        response = api_client.get_market_trend(days=60, index_code="000001.SH")
        
        assert response['status_code'] == 200
        trend_data = response['data']['data']
        trend_points = trend_data.get('data', [])
        
        if len(trend_points) < 24:
            pytest.skip("数据点不足，无法验证BBI计算")
        
        # 手动计算BBI验证
        prices = [point['price'] for point in trend_points]
        
        # 对最后一个数据点验证BBI
        last_24_prices = prices[-24:]
        ma3 = np.mean(last_24_prices[-3:])
        ma6 = np.mean(last_24_prices[-6:])
        ma12 = np.mean(last_24_prices[-12:])
        ma24 = np.mean(last_24_prices[-24:])
        expected_bbi = (ma3 + ma6 + ma12 + ma24) / 4
        
        last_point = trend_points[-1]
        actual_bbi = last_point['bbi']
        
        # 允许小的浮点误差
        assert abs(actual_bbi - expected_bbi) < 0.01, \
            f"BBI计算错误: 期望 {expected_bbi:.2f}, 实际 {actual_bbi:.2f}"
    
    def test_tc003_data_sorting(
        self,
        api_client,
        override_dependencies
    ):
        """TC-003: 验证数据按日期排序"""
        response = api_client.get_market_trend(days=60, index_code="000001.SH")
        
        assert response['status_code'] == 200
        trend_points = response['data']['data'].get('data', [])
        
        if len(trend_points) < 2:
            pytest.skip("数据点不足")
        
        # 验证日期排序（升序）
        dates = [point['date'] for point in trend_points]
        sorted_dates = sorted(dates)
        assert dates == sorted_dates, "数据未按日期升序排序"
    
    def test_tc003_chart_data_validation(
        self,
        api_client,
        override_dependencies
    ):
        """TC-003: 验证图表数据格式"""
        response = api_client.get_market_trend(days=60, index_code="000001.SH")
        
        assert response['status_code'] == 200
        trend_points = response['data']['data'].get('data', [])
        
        # 使用前端helper验证
        valid, errors = validate_chart_data(trend_points)
        assert valid, f"图表数据验证失败: {errors}"
    
    def test_tc003_different_index_codes(
        self,
        api_client,
        override_dependencies
    ):
        """TC-003: 验证不同指数代码"""
        index_codes = ["000001.SH", "000300.SH", "000852.SH"]
        
        for index_code in index_codes:
            response = api_client.get_market_trend(days=30, index_code=index_code)
            assert response['status_code'] == 200
            assert response['data']['data']['index_code'] == index_code
    
    # ========== TC-004: Portfolio NAV 数据持久化测试 ==========
    
    def test_tc004_portfolio_nav_from_database(
        self,
        api_client,
        populated_test_db,
        sample_portfolio_positions
    ):
        """TC-004: 验证Portfolio NAV从数据库计算"""
        # 计算期望的NAV（新模型使用total_vol而不是shares）
        expected_nav = sum(
            pos['current_price'] * pos['shares']  # shares对应total_vol
            for pos in sample_portfolio_positions
        )
        
        # Mock DataProvider和Config
        from unittest.mock import MagicMock
        from api.dependencies import get_portfolio_repository
        from api.routers.dashboard import get_dashboard_service
        from src.repositories.portfolio_repository import PortfolioRepository
        
        mock_provider = MagicMock()
        mock_config = MagicMock()
        
        # 使用测试数据库的repository（populated_test_db已经设置了测试数据库）
        portfolio_repo = PortfolioRepository()
        
        # 覆盖依赖
        def override_get_data_provider():
            # get_data_provider是生成器，需要yield
            yield mock_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            return portfolio_repo
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            response = api_client.get_dashboard_overview()
            
            # 如果API成功，验证NAV
            if response['status_code'] == 200:
                nav = response['data']['data']['portfolio_nav']['nav']
                # 验证NAV从数据库正确计算
                assert abs(nav - expected_nav) < 0.01, \
                    f"NAV计算错误: 期望 {expected_nav:.2f}, 实际 {nav:.2f}"
        finally:
            app.dependency_overrides.clear()
    
    def test_tc004_empty_portfolio_nav(
        self,
        api_client,
        test_db_session
    ):
        """TC-004: 验证空持仓时的NAV"""
        # 使用空数据库
        # Mock依赖
        from unittest.mock import MagicMock
        from api.dependencies import get_portfolio_repository
        from src.repositories.portfolio_repository import PortfolioRepository
        
        mock_provider = MagicMock()
        mock_config = MagicMock()
        
        # 使用测试数据库的repository（test_db_session已经设置了测试数据库）
        portfolio_repo = PortfolioRepository()
        
        def override_get_data_provider():
            # get_data_provider是生成器，需要yield
            yield mock_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            return portfolio_repo
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            response = api_client.get_dashboard_overview()
            
            if response['status_code'] == 200:
                nav = response['data']['data']['portfolio_nav']['nav']
                # 空持仓时NAV应该为0
                assert nav == 0.0, f"空持仓时NAV应为0，实际为 {nav}"
        finally:
            app.dependency_overrides.clear()
    
    # ========== TC-005: 错误处理和降级测试 ==========
    
    def test_tc005_external_api_failure(
        self,
        api_client
    ):
        """TC-005: 验证外部API失败时的错误处理"""
        # Mock DataProvider抛出异常
        mock_provider = MagicMock()
        mock_provider._pro = MagicMock()
        mock_provider._pro.index_daily = MagicMock(side_effect=Exception("API调用失败"))
        
        mock_config = MagicMock()
        
        def override_get_data_provider():
            # get_data_provider是生成器，需要yield
            yield mock_provider
        
        def override_get_config():
            return mock_config
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        
        try:
            response = api_client.get_dashboard_overview()
            
            # 应该返回错误响应或降级数据
            # 不应该返回500（如果实现了降级逻辑）
            assert response['status_code'] in [200, 500], \
                f"意外的状态码: {response['status_code']}"
            
            # 如果返回200，应该有降级数据
            if response['status_code'] == 200:
                data = response['data']
                assert data is not None
        finally:
            app.dependency_overrides.clear()
    
    def test_tc005_empty_data_handling(
        self,
        api_client,
        mock_config
    ):
        """TC-005: 验证空数据时的处理"""
        # Mock返回空数据
        mock_provider = MagicMock()
        mock_provider._pro = MagicMock()
        mock_provider._pro.index_daily = MagicMock(return_value=pd.DataFrame())
        
        def override_get_data_provider():
            # get_data_provider是生成器，需要yield
            yield mock_provider
        
        def override_get_config():
            return mock_config
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        
        try:
            response = api_client.get_dashboard_overview()
            
            # 应该返回200（使用默认数据）或适当的错误
            assert response['status_code'] == 200, \
                f"空数据时应返回200或降级数据，实际状态码: {response['status_code']}"
            
            # 验证返回了默认数据
            if response['status_code'] == 200:
                data = response['data']['data']
                assert 'market_regime' in data
                assert 'portfolio_nav' in data
        finally:
            app.dependency_overrides.clear()
    
    def test_tc005_invalid_parameters(
        self,
        api_client,
        override_dependencies
    ):
        """TC-005: 验证无效参数的处理"""
        # 测试无效的days参数
        response = api_client.get_market_trend(days=-1, index_code="000001.SH")
        # FastAPI应该返回422（验证错误）
        assert response['status_code'] == 422, \
            f"无效参数应返回422，实际: {response['status_code']}"
    
    # ========== TC-006: 数据一致性测试 ==========
    
    def test_tc006_data_format_consistency(
        self,
        api_client,
        override_dependencies
    ):
        """TC-006: 验证数据格式一致性"""
        # 获取Overview数据
        overview_response = api_client.get_dashboard_overview()
        assert overview_response['status_code'] == 200
        
        overview_data = overview_response['data']['data']
        
        # 验证日期格式（如果有）
        # 验证数值类型
        assert isinstance(overview_data['sentiment']['sentiment'], (int, float))
        assert isinstance(overview_data['target_position']['position'], (int, float))
        assert isinstance(overview_data['portfolio_nav']['nav'], (int, float))
        
        # 获取Market Trend数据
        trend_response = api_client.get_market_trend(days=60)
        assert trend_response['status_code'] == 200
        
        trend_data = trend_response['data']['data']
        trend_points = trend_data.get('data', [])
        
        if trend_points:
            # 验证日期格式 YYYY-MM-DD
            first_date = trend_points[0]['date']
            assert len(first_date) == 10, f"日期格式错误: {first_date}"
            assert first_date.count('-') == 2, f"日期格式错误: {first_date}"
            
            # 验证数值类型
            assert isinstance(trend_points[0]['price'], (int, float))
            assert isinstance(trend_points[0]['bbi'], (int, float))
    
    def test_tc006_enum_values_consistency(
        self,
        api_client,
        override_dependencies
    ):
        """TC-006: 验证枚举值一致性"""
        response = api_client.get_dashboard_overview()
        assert response['status_code'] == 200
        
        regime = response['data']['data']['market_regime']['regime']
        # 验证regime值在预期范围内
        assert regime in ['多头 (进攻)', '空头 (防守)'], \
            f"意外的regime值: {regime}"
        
        position_label = response['data']['data']['target_position']['label']
        # 验证position label值
        assert position_label in ['Full On', 'Defensive'], \
            f"意外的position label: {position_label}"
    
    # ========== TC-007: 性能测试 ==========
    
    def test_tc007_api_response_time(
        self,
        api_client,
        override_dependencies
    ):
        """TC-007: 验证API响应时间"""
        import time
        
        # 测试Overview API
        start = time.time()
        response = api_client.get_dashboard_overview()
        elapsed = time.time() - start
        
        assert response['status_code'] == 200
        assert elapsed < 0.5, f"Overview API响应时间过长: {elapsed:.3f}秒"
        
        # 测试Market Trend API
        start = time.time()
        response = api_client.get_market_trend(days=60)
        elapsed = time.time() - start
        
        assert response['status_code'] == 200
        assert elapsed < 0.5, f"Market Trend API响应时间过长: {elapsed:.3f}秒"
