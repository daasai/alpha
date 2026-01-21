# Dashboard E2E 测试说明

## 概述

本目录包含首页（Dashboard）的端到端集成测试，验证从前端到后端全链路功能，包括数据持久化验证。

## 测试用例

### TC-001: 首页加载和基础渲染
- 验证首页路由可以访问
- 验证健康检查端点

### TC-002: Dashboard Overview API 全链路测试
- 验证Overview API成功返回数据
- 验证带trade_date参数的API
- 验证前端数据处理和格式化

### TC-003: Market Trend API 全链路测试
- 验证Market Trend API成功返回数据
- 验证BBI计算正确性
- 验证数据排序
- 验证图表数据格式
- 验证不同指数代码

### TC-004: Portfolio NAV 数据持久化测试
- 验证Portfolio NAV从数据库计算
- 验证空持仓时的NAV

### TC-005: 错误处理和降级测试
- 验证外部API失败时的错误处理
- 验证空数据时的处理
- 验证无效参数的处理

### TC-006: 数据一致性测试
- 验证数据格式一致性
- 验证枚举值一致性

### TC-007: 性能测试
- 验证API响应时间

## 运行测试

### 前置条件

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 确保FastAPI和相关依赖已安装：
```bash
pip install fastapi uvicorn httpx
```

### 运行所有E2E测试

```bash
# 从项目根目录运行
pytest tests/e2e/test_dashboard_e2e.py -v
```

### 运行特定测试用例

```bash
# 运行TC-001
pytest tests/e2e/test_dashboard_e2e.py::TestDashboardE2E::test_tc001_homepage_loads -v

# 运行TC-002
pytest tests/e2e/test_dashboard_e2e.py::TestDashboardE2E::test_tc002_overview_api_success -v

# 运行TC-004（Portfolio NAV测试）
pytest tests/e2e/test_dashboard_e2e.py::TestDashboardE2E::test_tc004_portfolio_nav_from_database -v
```

### 运行测试并查看覆盖率

```bash
pytest tests/e2e/test_dashboard_e2e.py -v --cov=api.services.dashboard_service --cov-report=html
```

## 测试数据

测试使用Mock数据和临时数据库：
- Mock指数日线数据（60天）
- 测试持仓数据（3个持仓）
- 临时SQLite数据库（每个测试独立）

## 注意事项

1. **不修改测试用例**：如果测试失败，必须修复实现代码，而不是修改测试
2. **Root Cause Analysis**：深入分析失败原因，不应用"创可贴"修复
3. **数据隔离**：每个测试使用独立的数据库，避免相互影响
4. **Mock外部依赖**：Mock Tushare API，避免依赖外部服务

## 实现修复

根据测试结果，已修复以下实现代码：

1. **DashboardService._get_portfolio_nav()**
   - 从模拟数据改为从数据库读取
   - 使用PortfolioRepository获取持仓
   - 计算NAV = Σ(current_price × shares)
   - 计算变化百分比

2. **DashboardService.__init__()**
   - 添加PortfolioRepository依赖注入（可选）
   - 如果没有提供，自动创建新实例

## 测试结果

运行测试后，所有测试用例应该通过。如果测试失败：

1. 查看错误信息
2. 分析根本原因
3. 修复实现代码（不修改测试）
4. 重新运行测试验证修复
