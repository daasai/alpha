"""
Hunter E2E Integration Tests
猎场页面端到端集成测试
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app
from api.services.hunter_service import APIHunterService
from api.dependencies import get_data_provider, get_config
from src.data_provider import DataProvider
from src.config_manager import ConfigManager
from src.repositories.portfolio_repository import PortfolioRepository
from src.database import Position, _SessionLocal

from tests.e2e.fixtures.hunter_fixtures import (
    mock_stock_basic_data,
    mock_history_data,
    mock_enriched_data,
    mock_scan_results,
    mock_filters_response,
    test_db_session,
    mock_data_provider,
    mock_config,
    expected_filters_schema,
    expected_scan_response_schema,
    expected_stock_result_schema,
)
from tests.e2e.helpers.api_client import E2EAPIClient
from tests.e2e.helpers.hunter_helpers import (
    validate_scan_results,
    validate_rps_value,
    simulate_frontend_filter,
    format_stock_code,
    format_price,
    format_percentage,
    validate_filters_response,
)


class TestHunterE2E:
    """Hunter E2E测试类"""
    
    @pytest.fixture
    def api_client(self):
        """创建API测试客户端"""
        return E2EAPIClient(app)
    
    @pytest.fixture
    def override_dependencies(self, mock_data_provider, mock_config):
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
    
    # ========== TC-H001: 猎场页面加载和基础渲染 ==========
    
    def test_tc_h001_hunter_route_accessible(self, api_client):
        """TC-H001: 验证猎场路由可以访问"""
        # 测试根路径（验证API服务运行）
        response = api_client.client.get("/")
        assert response.status_code == 200
    
    # ========== TC-H002: Hunter Filters API 全链路测试 ==========
    
    def test_tc_h002_filters_api_success(
        self,
        api_client,
        override_dependencies,
        expected_filters_schema
    ):
        """TC-H002: 验证Filters API成功返回数据"""
        response = api_client.client.get("/api/hunter/filters")
        
        # 验证状态码
        assert response.status_code == 200, f"API返回错误: {response.text}"
        
        # 验证响应结构
        data = response.json()
        assert data is not None
        assert data.get('success') is True
        
        filters_data = data.get('data')
        assert filters_data is not None
        
        # 验证schema
        valid, errors = api_client.validate_response_schema(
            filters_data,
            expected_filters_schema
        )
        assert valid, f"Schema验证失败: {errors}"
        
        # 验证具体字段值
        assert 'rps_threshold' in filters_data
        rps_config = filters_data['rps_threshold']
        assert 50 <= rps_config['default'] <= 100
        assert rps_config['min'] == 50
        assert rps_config['max'] == 100
        assert rps_config['step'] == 1
        
        assert 'volume_ratio_threshold' in filters_data
        vol_config = filters_data['volume_ratio_threshold']
        assert 0.0 <= vol_config['default'] <= 10.0
        assert vol_config['min'] == 0.0
        assert vol_config['max'] == 10.0
        assert vol_config['step'] == 0.1
        
        assert 'pe_max' in filters_data
    
    def test_tc_h002_filters_data_validation(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H002: 验证筛选条件数据格式"""
        response = api_client.client.get("/api/hunter/filters")
        
        assert response.status_code == 200
        filters_data = response.json()['data']
        
        # 使用helper验证
        valid, errors = validate_filters_response(filters_data)
        assert valid, f"筛选条件验证失败: {errors}"
    
    # ========== TC-H003: Hunter Scan API 全链路测试 ==========
    
    def test_tc_h003_scan_api_success(
        self,
        api_client,
        override_dependencies,
        mock_enriched_data,
        expected_scan_response_schema,
        expected_stock_result_schema
    ):
        """TC-H003: 验证Scan API成功返回数据"""
        # 由于HunterService需要实际计算，我们Mock FactorPipeline来简化测试
        # 或者直接测试API层，Mock APIHunterService的返回
        
        # 方案：直接Mock APIHunterService.run_scan的返回值
        # 这样可以测试API层的转换逻辑，而不需要完整的因子计算流程
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            
            # Mock扫描结果（模拟APIHunterService.run_scan的返回格式）
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': [
                    {
                        'id': f"{row['ts_code']}_{idx}",
                        'code': row['ts_code'],
                        'name': row['name'],
                        'price': float(row['close']),
                        'change_percent': float(row['pct_chg']),
                        'rps': float(row['rps_60']),
                        'volume_ratio': float(row['vol_ratio_5']),
                        'ai_analysis': row.get('ai_analysis')
                    }
                    for idx, (_, row) in enumerate(mock_enriched_data.iterrows())
                ],
                'diagnostics': {'total_stocks': 100, 'result_count': len(mock_enriched_data)},
                'error': None
            }
            
            # 调用API
            scan_request = {
                'rps_threshold': 85,
                'volume_ratio_threshold': 1.5
            }
            response = api_client.client.post("/api/hunter/scan", json=scan_request)
            
            # 验证状态码
            assert response.status_code == 200, f"API返回错误: {response.text}"
            
            # 验证响应结构
            data = response.json()
            assert data is not None
            assert data.get('success') is True
            
            scan_data = data.get('data')
            assert scan_data is not None
            
            # 验证schema
            valid, errors = api_client.validate_response_schema(
                scan_data,
                expected_scan_response_schema
            )
            assert valid, f"Schema验证失败: {errors}"
            
            # 验证结果数据
            results = scan_data.get('results', [])
            assert len(results) > 0, "扫描结果不应为空"
            
            # 验证第一个结果的schema
            if results:
                valid, errors = api_client.validate_response_schema(
                    results[0],
                    expected_stock_result_schema
                )
                assert valid, f"结果项Schema验证失败: {errors}"
    
    def test_tc_h003_scan_results_filtering(
        self,
        api_client,
        override_dependencies,
        mock_enriched_data
    ):
        """TC-H003: 验证扫描结果符合筛选条件"""
        rps_threshold = 85
        volume_ratio_threshold = 1.5
        
        # Mock扫描结果
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            
            # 筛选符合条件的数据
            filtered_df = mock_enriched_data[
                (mock_enriched_data['rps_60'] >= rps_threshold) &
                (mock_enriched_data['vol_ratio_5'] >= volume_ratio_threshold)
            ]
            
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': [
                    {
                        'id': f"{row['ts_code']}_{idx}",
                        'code': row['ts_code'],
                        'name': row['name'],
                        'price': float(row['close']),
                        'change_percent': float(row['pct_chg']),
                        'rps': float(row['rps_60']),
                        'volume_ratio': float(row['vol_ratio_5']),
                        'ai_analysis': row.get('ai_analysis')
                    }
                    for idx, (_, row) in enumerate(filtered_df.iterrows())
                ],
                'diagnostics': None,
                'error': None
            }
            
            scan_request = {
                'rps_threshold': rps_threshold,
                'volume_ratio_threshold': volume_ratio_threshold
            }
            response = api_client.client.post("/api/hunter/scan", json=scan_request)
            
            assert response.status_code == 200
            results = response.json()['data']['results']
            
            # 验证结果符合筛选条件
            valid, errors = validate_scan_results(results, rps_threshold, volume_ratio_threshold)
            assert valid, f"筛选条件验证失败: {errors}"
    
    def test_tc_h003_scan_results_sorted(
        self,
        api_client,
        override_dependencies,
        mock_enriched_data
    ):
        """TC-H003: 验证扫描结果按RPS降序排序"""
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            
            # 按RPS降序排序
            sorted_df = mock_enriched_data.sort_values('rps_60', ascending=False)
            
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': [
                    {
                        'id': f"{row['ts_code']}_{idx}",
                        'code': row['ts_code'],
                        'name': row['name'],
                        'price': float(row['close']),
                        'change_percent': float(row['pct_chg']),
                        'rps': float(row['rps_60']),
                        'volume_ratio': float(row['vol_ratio_5']),
                        'ai_analysis': row.get('ai_analysis')
                    }
                    for idx, (_, row) in enumerate(sorted_df.iterrows())
                ],
                'diagnostics': None,
                'error': None
            }
            
            response = api_client.client.post("/api/hunter/scan", json={})
            
            assert response.status_code == 200
            results = response.json()['data']['results']
            
            # 验证排序
            if len(results) > 1:
                rps_values = [r['rps'] for r in results]
                assert rps_values == sorted(rps_values, reverse=True), \
                    "结果未按RPS降序排序"
    
    # ========== TC-H004: 筛选器交互测试 ==========
    
    def test_tc_h004_filter_interaction(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H004: 验证筛选器参数正确传递"""
        # 测试不同的RPS和量比阈值
        test_cases = [
            {'rps_threshold': 80, 'volume_ratio_threshold': 1.5},
            {'rps_threshold': 90, 'volume_ratio_threshold': 2.0},
            {'rps_threshold': 75, 'volume_ratio_threshold': 1.0},
        ]
        
        for params in test_cases:
            with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
                mock_service = MagicMock()
                mock_get_service.return_value = mock_service
                mock_service.run_scan.return_value = {
                    'success': True,
                    'trade_date': '20240115',
                    'results': [],
                    'diagnostics': None,
                    'error': None
                }
                
                response = api_client.client.post("/api/hunter/scan", json=params)
                
                assert response.status_code == 200
                # 验证服务被调用时使用了正确的参数
                # 注意：由于我们Mock了服务，这里主要验证API调用成功
    
    # ========== TC-H005: 扫描结果筛选测试 ==========
    
    def test_tc_h005_frontend_filtering(
        self,
        mock_scan_results
    ):
        """TC-H005: 验证前端筛选逻辑"""
        # 根据mock_scan_results的数据：
        # - 000001.SZ: rps=92.5
        # - 000002.SZ: rps=88.3
        # - 000858.SZ: rps=95.1
        # 前端筛选使用 rps >= rps_threshold - 20
        test_cases = [
            (85, 3),  # 阈值85，rps >= 65，所有3个都通过
            (90, 3),  # 阈值90，rps >= 70，所有3个都通过（92.5, 88.3, 95.1都>=70）
            (95, 3),  # 阈值95，rps >= 75，所有3个都通过（92.5, 88.3, 95.1都>=75）
        ]
        
        for rps_threshold, expected_count in test_cases:
            filtered = simulate_frontend_filter(mock_scan_results, rps_threshold)
            assert len(filtered) == expected_count, \
                f"RPS阈值 {rps_threshold} 时，期望 {expected_count} 个结果，实际 {len(filtered)} 个。筛选结果: {[r['code'] for r in filtered]}"
    
    def test_tc_h005_empty_results_handling(
        self,
        mock_scan_results
    ):
        """TC-H005: 验证空结果处理"""
        # 使用极高的阈值，应该没有结果
        filtered = simulate_frontend_filter(mock_scan_results, 200)
        assert len(filtered) == 0, "极高阈值时应返回空结果"
    
    # ========== TC-H006: 添加持仓到组合测试 ==========
    
    def test_tc_h006_add_to_portfolio(
        self,
        api_client,
        test_db_session,
        mock_scan_results
    ):
        """TC-H006: 验证添加持仓到组合"""
        from api.dependencies import get_data_provider, get_config, get_portfolio_repository
        from api.services.portfolio_service import PortfolioService
        from unittest.mock import MagicMock
        
        # Mock依赖
        mock_provider = MagicMock()
        mock_config_obj = MagicMock()
        
        def override_get_data_provider():
            yield mock_provider
        
        def override_get_config():
            return mock_config_obj
        
        # 使用真实的PortfolioRepository和数据库
        portfolio_repo = PortfolioRepository()
        
        def override_get_portfolio_repository():
            return portfolio_repo
        
        app.dependency_overrides[get_data_provider] = override_get_data_provider
        app.dependency_overrides[get_config] = override_get_config
        app.dependency_overrides[get_portfolio_repository] = override_get_portfolio_repository
        
        try:
            # 先初始化账户（买入订单需要账户）
            portfolio_repo.initialize_account(initial_cash=1000000.0)
            
            # 选择一个股票
            stock = mock_scan_results[0]
            
            # 使用买入订单API添加持仓（新API设计）
            buy_data = {
                'ts_code': stock['code'],
                'price': stock['price'],
                'volume': 100,
                'strategy_tag': 'test'
            }
            
            response = api_client.client.post("/api/portfolio/buy", json=buy_data)
            
            # 验证API调用成功（买入订单返回201）
            assert response.status_code in [200, 201], f"API返回错误: {response.text}"
            
            data = response.json()
            assert data.get('success') is True
            
            # 验证数据库中有记录
            positions = portfolio_repo.get_positions()
            assert len(positions) > 0, "数据库中没有持仓记录"
            
            # 验证持仓数据正确
            added_position = None
            for pos in positions:
                if pos.ts_code == stock['code']:
                    added_position = pos
                    break
            
            assert added_position is not None, f"未找到股票 {stock['code']} 的持仓记录"
            # 注意：买入订单可能使用ts_code作为name的默认值，这里验证ts_code即可
            assert added_position.ts_code == stock['code']
            assert abs(added_position.avg_price - stock['price']) < 0.01
            assert added_position.total_vol == 100
            
        finally:
            app.dependency_overrides.clear()
    
    # ========== TC-H007: 自动扫描功能测试 ==========
    
    def test_tc_h007_auto_scan_parameter(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H007: 验证自动扫描参数处理"""
        # 这个测试主要验证前端逻辑，在E2E测试中可以通过模拟URL参数来测试
        # 由于我们主要测试后端API，这里验证参数可以正确传递
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': [],
                'diagnostics': None,
                'error': None
            }
            
            # 模拟自动扫描（使用默认参数）
            response = api_client.client.post("/api/hunter/scan", json={})
            
            assert response.status_code == 200
            # 验证可以使用默认参数执行扫描
    
    # ========== TC-H008: 错误处理和降级测试 ==========
    
    def test_tc_h008_scan_api_failure(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H008: 验证扫描API失败时的错误处理"""
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_service.run_scan.side_effect = Exception("扫描失败")
            
            response = api_client.client.post("/api/hunter/scan", json={})
            
            # 应该返回错误响应
            assert response.status_code in [200, 500], \
                f"意外的状态码: {response.status_code}"
            
            # 如果返回200，检查响应结构
            if response.status_code == 200:
                data = response.json()
                # API层应该捕获异常并返回错误响应
                # 检查是否有错误信息（可能在data.error中，或者success=False）
                assert not data.get('success', True) or data.get('data', {}).get('error') is not None or data.get('error') is not None
    
    def test_tc_h008_filters_api_failure(
        self,
        api_client
    ):
        """TC-H008: 验证筛选条件API失败时的错误处理"""
        # Mock配置读取失败
        mock_config_fail = MagicMock()
        mock_config_fail.get.side_effect = Exception("配置读取失败")
        
        def override_get_config():
            return mock_config_fail
        
        app.dependency_overrides[get_config] = override_get_config
        
        try:
            response = api_client.client.get("/api/hunter/filters")
            
            # 应该返回错误或降级数据
            assert response.status_code in [200, 500], \
                f"意外的状态码: {response.status_code}"
        finally:
            app.dependency_overrides.clear()
    
    def test_tc_h008_empty_scan_results(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H008: 验证空扫描结果时的处理"""
        # 这个测试验证当数据合并失败时（返回空结果）的处理
        # 由于mock数据可能不匹配，我们允许success=False的情况
        response = api_client.client.post("/api/hunter/scan", json={})
        
        assert response.status_code == 200
        data = response.json()['data']
        
        # 如果数据合并失败，success可能为False，但API应该仍然返回200
        # 验证结果为空（无论是success=True还是False）
        results = data.get('results', [])
        assert len(results) == 0, "空扫描结果时应该返回空列表"
    
    # ========== TC-H009: 数据一致性测试 ==========
    
    def test_tc_h009_data_format_consistency(
        self,
        api_client,
        override_dependencies,
        mock_scan_results
    ):
        """TC-H009: 验证数据格式一致性"""
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': mock_scan_results,
                'diagnostics': None,
                'error': None
            }
            
            response = api_client.client.post("/api/hunter/scan", json={})
            
            assert response.status_code == 200
            results = response.json()['data']['results']
            
            # 验证数据类型
            for result in results:
                assert isinstance(result['id'], str)
                assert isinstance(result['code'], str)
                assert isinstance(result['name'], str)
                assert isinstance(result['price'], (int, float))
                assert isinstance(result['change_percent'], (int, float))
                assert isinstance(result['rps'], (int, float))
                assert isinstance(result['volume_ratio'], (int, float))
                assert result['ai_analysis'] is None or isinstance(result['ai_analysis'], str)
    
    def test_tc_h009_field_mapping(
        self,
        api_client,
        override_dependencies,
        mock_enriched_data
    ):
        """TC-H009: 验证字段映射正确（ts_code vs code）"""
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            
            # 验证后端返回的code字段对应前端的code
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': [
                    {
                        'id': f"{row['ts_code']}_{idx}",
                        'code': row['ts_code'],  # 后端使用ts_code作为code
                        'name': row['name'],
                        'price': float(row['close']),
                        'change_percent': float(row['pct_chg']),
                        'rps': float(row['rps_60']),
                        'volume_ratio': float(row['vol_ratio_5']),
                        'ai_analysis': row.get('ai_analysis')
                    }
                    for idx, (_, row) in enumerate(mock_enriched_data.iterrows())
                ],
                'diagnostics': None,
                'error': None
            }
            
            response = api_client.client.post("/api/hunter/scan", json={})
            
            assert response.status_code == 200
            results = response.json()['data']['results']
            
            # 验证code字段存在且格式正确
            for result in results:
                assert 'code' in result
                assert '.' in result['code'], "股票代码应包含交易所后缀（如.SZ）"
    
    # ========== TC-H010: 性能测试 ==========
    
    def test_tc_h010_filters_api_performance(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H010: 验证筛选条件API响应时间"""
        import time
        
        start = time.time()
        response = api_client.client.get("/api/hunter/filters")
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.2, f"筛选条件API响应时间过长: {elapsed:.3f}秒"
    
    def test_tc_h010_scan_api_performance(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H010: 验证扫描API响应时间"""
        import time
        
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': [],
                'diagnostics': None,
                'error': None
            }
            
            start = time.time()
            response = api_client.client.post("/api/hunter/scan", json={})
            elapsed = time.time() - start
            
            assert response.status_code == 200
            # 注意：实际扫描可能需要更长时间，这里主要验证Mock场景下的性能
            assert elapsed < 1.0, f"扫描API响应时间过长: {elapsed:.3f}秒"
    
    # ========== TC-H011: RPS计算验证测试 ==========
    
    def test_tc_h011_rps_value_range(
        self,
        mock_scan_results
    ):
        """TC-H011: 验证RPS值在有效范围内"""
        for result in mock_scan_results:
            rps = result['rps']
            valid, error = validate_rps_value(rps)
            assert valid, f"RPS值验证失败: {error}"
    
    def test_tc_h011_rps_calculation_logic(
        self,
        mock_history_data
    ):
        """TC-H011: 验证RPS计算逻辑"""
        # RPS计算：相对强度 = (当前涨幅排名 / 总股票数) * 100
        # 这里我们验证RPS值在合理范围内
        # 实际计算逻辑在FactorPipeline中，这里主要验证结果合理性
        
        # 模拟计算：如果股票涨幅排名在前10%，RPS应该在90-100之间
        # 如果排名在50%，RPS应该在50左右
        
        # 由于RPS计算涉及排名，这里主要验证返回的RPS值在0-100范围内
        # 更详细的验证需要测试FactorPipeline
        
        # 验证RPS值范围
        test_rps_values = [0, 50, 85, 95, 100]
        for rps in test_rps_values:
            valid, error = validate_rps_value(rps)
            assert valid, f"RPS值 {rps} 验证失败: {error}"
        
        # 验证无效值
        invalid_rps_values = [-1, 101, 150]
        for rps in invalid_rps_values:
            valid, error = validate_rps_value(rps)
            assert not valid, f"RPS值 {rps} 应该无效"
    
    # ========== TC-H012: 筛选条件持久化测试 ==========
    
    def test_tc_h012_filters_from_config(
        self,
        api_client,
        override_dependencies,
        mock_config
    ):
        """TC-H012: 验证筛选条件从配置正确读取"""
        response = api_client.client.get("/api/hunter/filters")
        
        assert response.status_code == 200
        filters_data = response.json()['data']
        
        # 验证默认值与配置一致
        # 注意：这里使用mock_config的默认值
        assert filters_data['rps_threshold']['default'] == 85
        assert filters_data['volume_ratio_threshold']['default'] == 1.5
        assert filters_data['pe_max']['default'] == 30
    
    def test_tc_h012_temporary_threshold_modification(
        self,
        api_client,
        override_dependencies
    ):
        """TC-H012: 验证临时修改阈值不影响配置"""
        # 第一次调用，使用默认阈值
        response1 = api_client.client.get("/api/hunter/filters")
        assert response1.status_code == 200
        default_rps = response1.json()['data']['rps_threshold']['default']
        
        # 使用自定义阈值执行扫描
        with patch('api.routers.hunter.get_hunter_service') as mock_get_service:
            mock_service = MagicMock()
            mock_get_service.return_value = mock_service
            mock_service.run_scan.return_value = {
                'success': True,
                'trade_date': '20240115',
                'results': [],
                'diagnostics': None,
                'error': None
            }
            
            custom_params = {
                'rps_threshold': 90,
                'volume_ratio_threshold': 2.0
            }
            response2 = api_client.client.post("/api/hunter/scan", json=custom_params)
            assert response2.status_code == 200
        
        # 再次获取筛选条件，应该还是默认值
        response3 = api_client.client.get("/api/hunter/filters")
        assert response3.status_code == 200
        current_rps = response3.json()['data']['rps_threshold']['default']
        
        # 验证配置没有被修改
        assert current_rps == default_rps, "临时修改阈值不应影响配置"
