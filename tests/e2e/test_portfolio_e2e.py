"""
Portfolio E2E Integration Tests
模拟盘端到端集成测试
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.services.portfolio_service import PortfolioService
from api.dependencies import get_data_provider, get_config, get_portfolio_repository
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.repositories.portfolio_repository import PortfolioRepository
from src.database import Account, Position, Order, _SessionLocal

from tests.e2e.fixtures.portfolio_fixtures import (
    sample_portfolio_positions,
    sample_stock_daily_data,
    test_db_session,
    populated_test_db,
    mock_data_provider,
    mock_config,
    expected_position_schema,
    expected_metrics_schema,
    sample_account,
)
from tests.e2e.helpers.api_client import E2EAPIClient


class TestPortfolioE2E:
    """Portfolio E2E测试类"""
    
    @pytest.fixture
    def api_client(self):
        """创建API测试客户端"""
        return E2EAPIClient(app)
    
    @pytest.fixture
    def override_dependencies(self, mock_data_provider, mock_config, test_db_session, populated_test_db, monkeypatch):
        """覆盖依赖注入"""
        from api.dependencies import get_data_provider, get_config, get_portfolio_repository
        import src.database
        import src.repositories.portfolio_repository
        
        # 确保使用测试数据库的_SessionLocal
        # portfolio_repository现在使用db_module._SessionLocal()，所以直接修改src.database._SessionLocal即可
        # 不需要再monkeypatch portfolio_repository模块
        
        def override_get_data_provider():
            # get_data_provider是生成器，需要yield
            yield mock_data_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            # 使用测试数据库的repository（会使用更新后的_SessionLocal）
            from src.repositories.portfolio_repository import PortfolioRepository
            return PortfolioRepository()
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        yield
        
        # 清理
        app.dependency_overrides.clear()
    
    # ========== TC-001: 获取持仓列表 ==========
    
    def test_tc001_get_positions_success(
        self,
        api_client,
        override_dependencies,
        expected_position_schema,
        sample_portfolio_positions
    ):
        """TC-001: 验证获取持仓列表API成功返回数据"""
        response = api_client.get_portfolio_positions()
        
        # 验证状态码
        assert response['status_code'] == 200, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        positions_data = data.get('data')
        assert positions_data is not None
        assert 'positions' in positions_data
        
        positions = positions_data['positions']
        assert isinstance(positions, list)
        assert len(positions) == len(sample_portfolio_positions), \
            f"持仓数量不匹配: 期望 {len(sample_portfolio_positions)}, 实际 {len(positions)}"
        
        # 验证每个持仓的schema
        for pos in positions:
            valid, errors = api_client.validate_response_schema(
                pos,
                expected_position_schema
            )
            assert valid, f"持仓Schema验证失败: {errors}"
            
            # 验证必需字段（新模型）
            assert 'id' in pos
            assert 'ts_code' in pos
            assert 'name' in pos
            assert 'total_vol' in pos
            assert 'avail_vol' in pos
            assert 'avg_price' in pos
    
    def test_tc001_get_positions_empty(
        self,
        api_client,
        mock_data_provider,
        mock_config,
        test_db_session,
        monkeypatch
    ):
        """TC-001: 验证空持仓列表"""
        # 使用空数据库
        import src.database
        import src.repositories.portfolio_repository
        
        # 确保使用测试数据库
        # portfolio_repository现在使用db_module._SessionLocal()，所以直接使用测试数据库的_SessionLocal即可
        # 不再需要PortfolioPosition，已迁移到Position模型
        
        def override_get_data_provider():
            yield mock_data_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            from src.repositories.portfolio_repository import PortfolioRepository
            return PortfolioRepository()
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            response = api_client.get_portfolio_positions()
            
            assert response['status_code'] == 200
            positions = response['data']['data']['positions']
            assert len(positions) == 0, "空持仓时应返回空列表"
        finally:
            app.dependency_overrides.clear()
    
    def test_tc001_positions_data_persistence(
        self,
        api_client,
        override_dependencies,
        sample_portfolio_positions
    ):
        """TC-001: 验证持仓数据持久化"""
        response = api_client.get_portfolio_positions()
        
        assert response['status_code'] == 200
        positions = response['data']['data']['positions']
        
        # 验证数据与数据库一致（新模型）
        # 创建ts_code到position的映射
        positions_dict = {pos['ts_code']: pos for pos in positions}
        sample_dict = {pos['ts_code']: pos for pos in sample_portfolio_positions}
        
        # 验证每个持仓的数据
        for ts_code, sample_pos in sample_dict.items():
            assert ts_code in positions_dict, f"持仓 {ts_code} 未找到"
            actual_pos = positions_dict[ts_code]
            
            assert actual_pos['ts_code'] == sample_pos['ts_code']
            assert actual_pos['name'] == sample_pos['name']
            assert abs(actual_pos['avg_price'] - sample_pos['avg_price']) < 0.01
            assert actual_pos['total_vol'] == sample_pos['total_vol']
    
    # ========== TC-002: 获取组合指标 ==========
    
    def test_tc002_get_metrics_success(
        self,
        api_client,
        override_dependencies,
        expected_metrics_schema,
        sample_portfolio_positions
    ):
        """TC-002: 验证获取组合指标API成功返回数据"""
        response = api_client.get_portfolio_metrics()
        
        # 验证状态码
        assert response['status_code'] == 200, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        metrics_data = data.get('data')
        assert metrics_data is not None
        assert 'metrics' in metrics_data
        
        metrics = metrics_data['metrics']
        
        # 验证schema
        valid, errors = api_client.validate_response_schema(
            metrics,
            expected_metrics_schema
        )
        assert valid, f"指标Schema验证失败: {errors}"
        
        # 验证指标值
        assert 'total_return' in metrics
        assert 'max_drawdown' in metrics
        assert 'sharpe_ratio' in metrics
        
        # 验证指标值的合理性
        assert isinstance(metrics['total_return'], (int, float))
        assert isinstance(metrics['max_drawdown'], (int, float))
        assert isinstance(metrics['sharpe_ratio'], (int, float))
    
    def test_tc002_metrics_calculation(
        self,
        api_client,
        override_dependencies,
        sample_portfolio_positions
    ):
        """TC-002: 验证组合指标计算正确性"""
        response = api_client.get_portfolio_metrics()
        
        assert response['status_code'] == 200
        metrics = response['data']['data']['metrics']
        
        # 手动计算总收益（新模型）
        total_cost = sum(pos['avg_price'] * pos['total_vol'] for pos in sample_portfolio_positions)
        total_value = sum(pos['current_price'] * pos['total_vol'] for pos in sample_portfolio_positions)
        expected_total_return = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0.0
        
        # 验证总收益计算（允许小的浮点误差）
        assert abs(metrics['total_return'] - expected_total_return) < 0.1, \
            f"总收益计算错误: 期望 {expected_total_return:.2f}, 实际 {metrics['total_return']:.2f}"
    
    def test_tc002_empty_portfolio_metrics(
        self,
        api_client,
        mock_data_provider,
        mock_config,
        test_db_session,
        monkeypatch
    ):
        """TC-002: 验证空持仓时的组合指标"""
        import src.database
        import src.repositories.portfolio_repository
        
        # 确保使用测试数据库
        # portfolio_repository现在使用db_module._SessionLocal()，所以直接使用测试数据库的_SessionLocal即可
        # 不再需要PortfolioPosition，已迁移到Position模型
        
        def override_get_data_provider():
            yield mock_data_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            from src.repositories.portfolio_repository import PortfolioRepository
            return PortfolioRepository()
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            response = api_client.get_portfolio_metrics()
            
            assert response['status_code'] == 200
            metrics = response['data']['data']['metrics']
            
            # 空持仓时所有指标应为0
            assert metrics['total_return'] == 0.0
            assert metrics['max_drawdown'] == 0.0
            assert metrics['sharpe_ratio'] == 0.0
        finally:
            app.dependency_overrides.clear()
    
    # ========== TC-003: 添加持仓 ==========
    
    def test_tc003_execute_buy_success(
        self,
        api_client,
        override_dependencies
    ):
        """TC-003: 验证执行买入订单API成功"""
        # 执行买入订单
        response = api_client.execute_buy(
            ts_code='600001.SH',
            price=20.0,
            volume=500,
            strategy_tag='test'
        )
        
        # 验证状态码
        assert response['status_code'] == 201, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        order_data = data.get('data')
        assert order_data is not None
        
        # 验证订单数据
        assert order_data['action'] == 'BUY'
        assert order_data['ts_code'] == '600001.SH'
        assert order_data['price'] == 20.0
        assert order_data['volume'] == 500
        assert order_data['status'] == 'FILLED'
        assert 'order_id' in order_data
        
        # 验证持仓已创建
        positions_response = api_client.get_portfolio_positions()
        assert positions_response['status_code'] == 200
        positions = positions_response['data']['data']['positions']
        position = next((p for p in positions if p['ts_code'] == '600001.SH'), None)
        assert position is not None
        assert position['total_vol'] == 500
        assert position['avail_vol'] == 0  # T+1 规则
    
    def test_tc003_execute_buy_insufficient_funds(
        self,
        api_client,
        override_dependencies
    ):
        """TC-003: 验证买入时资金不足"""
        # 尝试买入大量股票（资金不足）
        response = api_client.execute_buy(
            ts_code='600002.SH',
            price=1000.0,  # 高价
            volume=10000,  # 大量
            strategy_tag='test'
        )
        
        # 应该返回400错误（资金不足）
        assert response['status_code'] == 400
        assert 'error' in response or '资金不足' in str(response.get('error', ''))
    
    def test_tc003_execute_buy_persistence(
        self,
        api_client,
        override_dependencies
    ):
        """TC-003: 验证买入订单后数据持久化"""
        # 执行买入订单
        buy_response = api_client.execute_buy(
            ts_code='600003.SH',
            price=25.0,
            volume=300,
            strategy_tag='test'
        )
        
        assert buy_response['status_code'] == 201
        order_id = buy_response['data']['data']['order_id']
        
        # 获取持仓列表，验证新持仓已保存
        get_response = api_client.get_portfolio_positions()
        assert get_response['status_code'] == 200
        
        positions = get_response['data']['data']['positions']
        
        # 验证持仓已创建
        new_position = next((pos for pos in positions if pos['ts_code'] == '600003.SH'), None)
        assert new_position is not None, "买入后持仓未创建"
        assert new_position['ts_code'] == '600003.SH'
        assert new_position['total_vol'] == 300
        assert new_position['avail_vol'] == 0  # T+1 规则
        assert abs(new_position['avg_price'] - 25.0) < 0.01
    
    def test_tc003_execute_buy_validation(
        self,
        api_client,
        override_dependencies
    ):
        """TC-003: 验证买入订单的参数验证"""
        # 测试无效的价格（负数）
        response = api_client.execute_buy(
            ts_code='600004.SH',
            price=-10.0,
            volume=100
        )
        assert response['status_code'] == 422, "负数价格应该返回422验证错误"
        
        # 测试无效的数量（负数）
        response = api_client.execute_buy(
            ts_code='600004.SH',
            price=10.0,
            volume=-100
        )
        assert response['status_code'] == 422, "负数数量应该返回422验证错误"
    
    # ========== TC-004: 执行卖出订单 ==========
    
    def test_tc004_execute_sell_success(
        self,
        api_client,
        override_dependencies,
        sample_portfolio_positions
    ):
        """TC-004: 验证执行卖出订单API成功"""
        # 先买入（如果有持仓，先设置avail_vol）
        # 由于fixture中已有持仓，我们需要手动设置avail_vol以允许卖出
        from src.database import _SessionLocal, Position
        session = _SessionLocal()
        try:
            position = session.query(Position).filter(Position.ts_code == sample_portfolio_positions[0]['ts_code']).first()
            if position:
                position.avail_vol = position.total_vol  # 设置可用数量
                session.commit()
        finally:
            session.close()
        
        # 执行卖出订单
        response = api_client.execute_sell(
            ts_code=sample_portfolio_positions[0]['ts_code'],
            price=12.0,
            volume=500,
            reason='test'
        )
        
        # 验证状态码
        assert response['status_code'] == 201, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        order_data = data.get('data')
        assert order_data is not None
        
        # 验证订单数据
        assert order_data['action'] == 'SELL'
        assert order_data['status'] == 'FILLED'
    
    def test_tc004_execute_sell_position_not_found(
        self,
        api_client,
        override_dependencies
    ):
        """TC-004: 验证卖出不存在的持仓"""
        response = api_client.execute_sell(
            ts_code='999999.SH',
            price=10.0,
            volume=100
        )
        
        assert response['status_code'] == 404, "不存在的持仓应该返回404"
    
    def test_tc004_execute_sell_insufficient_volume(
        self,
        api_client,
        override_dependencies,
        sample_portfolio_positions
    ):
        """TC-004: 验证卖出时可用数量不足"""
        # 先将 avail_vol 设置为 0（模拟 T+1 规则，当日买入不可卖出）
        from src.database import _SessionLocal, Position
        session = _SessionLocal()
        try:
            position = session.query(Position).filter(
                Position.ts_code == sample_portfolio_positions[0]['ts_code']
            ).first()
            if position:
                position.avail_vol = 0  # 设置为0，模拟T+1规则
                session.commit()
        finally:
            session.close()
        
        # 尝试卖出（avail_vol为0，应该失败）
        response = api_client.execute_sell(
            ts_code=sample_portfolio_positions[0]['ts_code'],
            price=12.0,
            volume=1000  # 尝试卖出超过可用数量（0）
        )
        
        assert response['status_code'] == 400, "可用数量不足应该返回400"
    
    # ========== TC-005: 获取账户信息 ==========
    
    def test_tc005_get_account_success(
        self,
        api_client,
        override_dependencies,
        sample_account
    ):
        """TC-005: 验证获取账户信息API成功"""
        response = api_client.get_account()
        
        # 验证状态码
        assert response['status_code'] == 200, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        account_data = data.get('data')
        assert account_data is not None
        
        # 验证账户数据
        assert account_data['id'] == 1
        assert 'cash' in account_data
        assert 'total_asset' in account_data
        assert 'market_value' in account_data
        assert account_data['total_asset'] == account_data['cash'] + account_data['market_value']
    
    def test_tc005_get_account_not_initialized(
        self,
        api_client,
        mock_data_provider,
        mock_config,
        test_db_session,
        monkeypatch
    ):
        """TC-005: 验证获取未初始化的账户"""
        # 使用空数据库（没有账户）
        import src.database
        import src.repositories.portfolio_repository
        
        # portfolio_repository现在使用db_module._SessionLocal()，所以直接使用测试数据库的_SessionLocal即可
        
        def override_get_data_provider():
            yield mock_data_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            from src.repositories.portfolio_repository import PortfolioRepository
            return PortfolioRepository()
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            response = api_client.get_account()
            assert response['status_code'] == 404, "未初始化的账户应该返回404"
        finally:
            app.dependency_overrides.clear()
    
    # ========== TC-006: 刷新价格 ==========
    
    def test_tc006_refresh_prices_success(
        self,
        api_client,
        override_dependencies,
        sample_portfolio_positions
    ):
        """TC-006: 验证刷新价格API成功"""
        response = api_client.refresh_prices()
        
        # 验证状态码
        assert response['status_code'] == 200, f"API返回错误: {response.get('error')}"
        
        # 验证响应结构
        data = response['data']
        assert data is not None
        assert data.get('success') is True
        
        result_data = data.get('data')
        assert result_data is not None
        assert 'updated_count' in result_data
        assert 'total_positions' in result_data
        
        # 验证更新数量（可能少于总数，因为某些股票可能获取不到价格）
        assert result_data['updated_count'] >= 0
        assert result_data['total_positions'] == len(sample_portfolio_positions)
        assert 'timestamp' in result_data
    
    def test_tc006_refresh_prices_updates_database(
        self,
        api_client,
        override_dependencies,
        sample_portfolio_positions
    ):
        """TC-006: 验证刷新价格后数据库更新"""
        # 刷新价格
        refresh_response = api_client.refresh_prices()
        assert refresh_response['status_code'] == 200
        
        # 获取持仓列表，验证价格已更新
        get_response = api_client.get_portfolio_positions()
        assert get_response['status_code'] == 200
        
        positions = get_response['data']['data']['positions']
        
        # 验证每个持仓的价格都已更新（从Mock数据获取）
        for pos in positions:
            assert pos['current_price'] is not None
            assert pos['current_price'] > 0
    
    def test_tc006_refresh_prices_empty_portfolio(
        self,
        api_client,
        mock_data_provider,
        mock_config,
        test_db_session,
        monkeypatch
    ):
        """TC-006: 验证空持仓时刷新价格"""
        import src.database
        import src.repositories.portfolio_repository
        
        # 确保使用测试数据库
        # portfolio_repository现在使用db_module._SessionLocal()，所以直接使用测试数据库的_SessionLocal即可
        # 不再需要PortfolioPosition，已迁移到Position模型
        
        def override_get_data_provider():
            yield mock_data_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            from src.repositories.portfolio_repository import PortfolioRepository
            return PortfolioRepository()
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            response = api_client.refresh_prices()
            
            assert response['status_code'] == 200
            result_data = response['data']['data']
            
            assert result_data['updated_count'] == 0
            assert result_data['total_positions'] == 0
        finally:
            app.dependency_overrides.clear()
    
    # ========== TC-007: 错误处理 ==========
    
    def test_tc007_invalid_request_data(
        self,
        api_client,
        override_dependencies
    ):
        """TC-007: 验证无效请求数据的处理"""
        # 测试缺少必需字段（买入订单）
        response = api_client.client.post(
            "/api/portfolio/buy",
            json={'ts_code': '600005.SH'}  # 缺少price和volume
        )
        
        assert response.status_code == 422, "缺少必需字段应该返回422验证错误"
    
    def test_tc007_price_fetch_failure(
        self,
        api_client,
        mock_config,
        populated_test_db
    ):
        """TC-007: 验证价格获取失败时的处理"""
        # Mock DataProvider抛出异常
        mock_provider = MagicMock()
        mock_provider._tushare_client = MagicMock()
        mock_provider._tushare_client.get_daily = MagicMock(side_effect=Exception("价格获取失败"))
        
        def override_get_data_provider():
            yield mock_provider
        
        def override_get_config():
            return mock_config
        
        def override_get_portfolio_repository():
            return PortfolioRepository()
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            # 即使价格获取失败，获取持仓列表应该仍然成功（价格可能为None）
            response = api_client.get_portfolio_positions()
            
            # 应该返回200，但价格可能为None
            assert response['status_code'] == 200
        finally:
            app.dependency_overrides.clear()
    
    # ========== TC-008: 数据一致性测试 ==========
    
    def test_tc008_data_format_consistency(
        self,
        api_client,
        override_dependencies
    ):
        """TC-008: 验证数据格式一致性"""
        # 获取持仓列表
        positions_response = api_client.get_portfolio_positions()
        assert positions_response['status_code'] == 200
        
        positions = positions_response['data']['data']['positions']
        
        if positions:
            # 验证每个持仓的数据格式（新模型）
            for pos in positions:
                assert isinstance(pos['id'], int)
                assert isinstance(pos['ts_code'], str)
                assert isinstance(pos['name'], str)
                assert isinstance(pos['total_vol'], int)
                assert isinstance(pos['avail_vol'], int)
                assert isinstance(pos['avg_price'], (int, float))
                assert pos['total_vol'] >= 0, "总持仓量应该大于等于0"
                assert pos['avail_vol'] >= 0, "可用持仓量应该大于等于0"
        
        # 获取组合指标
        metrics_response = api_client.get_portfolio_metrics()
        assert metrics_response['status_code'] == 200
        
        metrics = metrics_response['data']['data']['metrics']
        
        # 验证指标格式
        assert isinstance(metrics['total_return'], (int, float))
        assert isinstance(metrics['max_drawdown'], (int, float))
        assert isinstance(metrics['sharpe_ratio'], (int, float))
    
    def test_tc008_buy_sell_operations_consistency(
        self,
        api_client,
        override_dependencies
    ):
        """TC-008: 验证买入/卖出操作的一致性"""
        ts_code = '600006.SH'
        
        # 1. 买入
        buy_response = api_client.execute_buy(
            ts_code=ts_code,
            price=30.0,
            volume=400,
            strategy_tag='test'
        )
        assert buy_response['status_code'] == 201
        order_id = buy_response['data']['data']['order_id']
        
        # 2. 读取持仓
        get_response = api_client.get_portfolio_positions()
        assert get_response['status_code'] == 200
        positions = get_response['data']['data']['positions']
        position = next((pos for pos in positions if pos['ts_code'] == ts_code), None)
        assert position is not None, "买入后持仓应该存在"
        assert position['total_vol'] == 400
        assert position['avail_vol'] == 0  # T+1 规则
        
        # 3. 设置可用数量（模拟T+1后）
        from src.database import _SessionLocal, Position
        session = _SessionLocal()
        try:
            pos = session.query(Position).filter(Position.ts_code == ts_code).first()
            if pos:
                pos.avail_vol = pos.total_vol
                session.commit()
        finally:
            session.close()
        
        # 4. 卖出
        sell_response = api_client.execute_sell(
            ts_code=ts_code,
            price=32.0,
            volume=200,
            reason='test'
        )
        assert sell_response['status_code'] == 201
        
        # 5. 验证卖出后持仓
        get_response = api_client.get_portfolio_positions()
        positions = get_response['data']['data']['positions']
        position = next((pos for pos in positions if pos['ts_code'] == ts_code), None)
        assert position is not None
        assert position['total_vol'] == 200  # 400 - 200
        assert position['avail_vol'] == 200  # 400 - 200
        
        # 6. 全部卖出（删除持仓）
        sell_response = api_client.execute_sell(
            ts_code=ts_code,
            price=33.0,
            volume=200,
            reason='test'
        )
        assert sell_response['status_code'] == 201
        
        # 7. 验证持仓已删除
        get_response = api_client.get_portfolio_positions()
        positions = get_response['data']['data']['positions']
        position = next((pos for pos in positions if pos['ts_code'] == ts_code), None)
        assert position is None, "全部卖出后持仓应该被删除"
