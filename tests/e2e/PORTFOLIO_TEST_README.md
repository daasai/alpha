# Portfolio E2E 测试说明

## 概述

本目录包含模拟盘（Portfolio）的端到端集成测试，验证从前端到后端全链路功能，包括数据持久化验证。

## 测试用例

### TC-001: 获取持仓列表
- 验证获取持仓列表API成功返回数据
- 验证空持仓列表
- 验证持仓数据持久化

### TC-002: 获取组合指标
- 验证获取组合指标API成功返回数据
- 验证组合指标计算正确性
- 验证空持仓时的组合指标

### TC-003: 添加持仓
- 验证添加持仓API成功
- 验证使用默认值添加持仓
- 验证添加持仓后数据持久化
- 验证添加持仓的参数验证

### TC-004: 更新持仓
- 验证更新持仓API成功
- 验证更新持仓后数据持久化
- 验证更新不存在的持仓
- 验证部分更新持仓（只更新部分字段）

### TC-005: 删除持仓
- 验证删除持仓API成功
- 验证删除持仓后数据持久化
- 验证删除不存在的持仓

### TC-006: 刷新价格
- 验证刷新价格API成功
- 验证刷新价格后数据库更新
- 验证空持仓时刷新价格

### TC-007: 错误处理
- 验证无效请求数据的处理
- 验证价格获取失败时的处理

### TC-008: 数据一致性测试
- 验证数据格式一致性
- 验证CRUD操作的一致性

## 运行测试

### 前置条件

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 确保FastAPI和相关依赖已安装：
```bash
pip install fastapi uvicorn httpx pytest pytest-mock
```

### 运行所有E2E测试

```bash
# 从项目根目录运行
pytest tests/e2e/test_portfolio_e2e.py -v
```

### 运行特定测试用例

```bash
# 运行TC-001
pytest tests/e2e/test_portfolio_e2e.py::TestPortfolioE2E::test_tc001_get_positions_success -v

# 运行TC-002
pytest tests/e2e/test_portfolio_e2e.py::TestPortfolioE2E::test_tc002_get_metrics_success -v

# 运行TC-003（添加持仓）
pytest tests/e2e/test_portfolio_e2e.py::TestPortfolioE2E::test_tc003_add_position_success -v

# 运行TC-004（更新持仓）
pytest tests/e2e/test_portfolio_e2e.py::TestPortfolioE2E::test_tc004_update_position_success -v

# 运行TC-005（删除持仓）
pytest tests/e2e/test_portfolio_e2e.py::TestPortfolioE2E::test_tc005_delete_position_success -v

# 运行TC-006（刷新价格）
pytest tests/e2e/test_portfolio_e2e.py::TestPortfolioE2E::test_tc006_refresh_prices_success -v
```

### 运行测试并查看覆盖率

```bash
pytest tests/e2e/test_portfolio_e2e.py -v --cov=api.services.portfolio_service --cov-report=html
```

## 测试数据

测试使用Mock数据和临时数据库：
- Mock股票日线数据（用于价格查询）
- 测试持仓数据（3个持仓）
- 临时SQLite数据库（每个测试独立）

## 注意事项

1. **不修改测试用例**：如果测试失败，必须修复实现代码，而不是修改测试
2. **Root Cause Analysis**：深入分析失败原因，不应用"创可贴"修复
3. **数据隔离**：每个测试使用独立的数据库，避免相互影响
4. **Mock外部依赖**：Mock Tushare API，避免依赖外部服务

## 测试覆盖的功能

### API端点
- `GET /api/portfolio/positions` - 获取持仓列表
- `GET /api/portfolio/metrics` - 获取组合指标
- `POST /api/portfolio/positions` - 添加持仓
- `PUT /api/portfolio/positions/{position_id}` - 更新持仓
- `DELETE /api/portfolio/positions/{position_id}` - 删除持仓
- `POST /api/portfolio/refresh-prices` - 刷新价格

### 数据持久化
- 持仓数据的创建、读取、更新、删除
- 价格更新和持久化
- 组合指标的计算和返回

### 业务逻辑
- 默认持仓数量和止损比例的应用
- 价格获取和更新
- 组合指标计算（总收益、最大回撤、夏普比率）

## 实现修复

根据测试结果，已修复以下实现代码：

1. **数据库隔离**
   - 使用monkeypatch确保测试使用独立的测试数据库
   - 修复了`PortfolioRepository`的`_SessionLocal`引用问题

2. **API响应处理**
   - 修复了DELETE请求（204 No Content）的响应处理
   - 正确处理无响应体的HTTP状态码

## 测试结果

运行测试后，所有24个测试用例应该通过。如果测试失败：

1. 查看错误信息
2. 分析根本原因
3. 修复实现代码（不修改测试）
4. 重新运行测试验证修复

## 已知问题

1. **Pydantic警告**：使用了已弃用的`.dict()`方法，应迁移到`.model_dump()`
   - 位置：`api/routers/portfolio.py:69, 85`
   - 影响：不影响功能，但会在未来版本中移除

2. **HTTP状态码警告**：使用了已弃用的`HTTP_422_UNPROCESSABLE_ENTITY`
   - 影响：不影响功能，但会在未来版本中移除
