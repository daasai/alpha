# Hunter E2E 测试说明

## 概述

本目录包含猎场（Hunter）页面的端到端集成测试，验证从前端到后端全链路功能，包括股票扫描、筛选、数据持久化等核心功能。

## 测试用例

### TC-H001: 猎场页面加载和基础渲染
- 验证猎场路由可以访问
- 验证基础UI元素存在

### TC-H002: Hunter Filters API 全链路测试
- 验证筛选条件API成功返回数据
- 验证筛选条件数据格式
- 验证默认值正确

### TC-H003: Hunter Scan API 全链路测试
- 验证扫描API成功返回数据
- 验证扫描结果符合筛选条件
- 验证结果按RPS降序排序

### TC-H004: 筛选器交互测试
- 验证筛选器参数正确传递
- 验证不同阈值参数的处理

### TC-H005: 扫描结果筛选测试
- 验证前端筛选逻辑
- 验证空结果处理

### TC-H006: 添加持仓到组合测试
- 验证添加持仓API调用
- 验证数据库持久化
- 验证持仓数据正确性

### TC-H007: 自动扫描功能测试
- 验证自动扫描参数处理
- 验证默认参数使用

### TC-H008: 错误处理和降级测试
- 验证扫描API失败时的错误处理
- 验证筛选条件API失败时的错误处理
- 验证空扫描结果时的处理

### TC-H009: 数据一致性测试
- 验证数据格式一致性
- 验证字段映射正确（ts_code vs code）

### TC-H010: 性能测试
- 验证筛选条件API响应时间
- 验证扫描API响应时间

### TC-H011: RPS计算验证测试
- 验证RPS值在有效范围内
- 验证RPS计算逻辑合理性

### TC-H012: 筛选条件持久化测试
- 验证筛选条件从配置正确读取
- 验证临时修改阈值不影响配置

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

### 运行所有Hunter E2E测试

```bash
# 从项目根目录运行
pytest tests/e2e/test_hunter_e2e.py -v
```

### 运行特定测试用例

```bash
# 运行TC-H002
pytest tests/e2e/test_hunter_e2e.py::TestHunterE2E::test_tc_h002_filters_api_success -v

# 运行TC-H003
pytest tests/e2e/test_hunter_e2e.py::TestHunterE2E::test_tc_h003_scan_api_success -v

# 运行TC-H006（添加持仓测试）
pytest tests/e2e/test_hunter_e2e.py::TestHunterE2E::test_tc_h006_add_to_portfolio -v
```

### 运行测试并查看覆盖率

```bash
pytest tests/e2e/test_hunter_e2e.py -v --cov=api.services.hunter_service --cov=src.services.hunter_service --cov-report=html
```

## 测试数据

测试使用Mock数据和临时数据库：
- Mock股票基础数据（5个股票）
- Mock历史日线数据（120天）
- Mock增强数据（包含因子计算结果）
- Mock扫描结果数据
- 临时SQLite数据库（每个测试独立）

## 注意事项

1. **不修改测试用例**：如果测试失败，必须修复实现代码，而不是修改测试
2. **Root Cause Analysis**：深入分析失败原因，不应用"创可贴"修复
3. **数据隔离**：每个测试使用独立的数据库，避免相互影响
4. **Mock外部依赖**：Mock Tushare API和因子计算，避免依赖外部服务
5. **清理资源**：测试后清理数据库和临时文件
6. **RPS计算验证**：确保RPS计算逻辑正确，这是Hunter功能的核心

## 实现修复

根据测试结果，可能需要修复以下实现代码：

1. **APIHunterService.run_scan()**
   - 确保数据转换正确
   - 确保错误处理完善

2. **HunterService.run_scan()**
   - 验证RPS计算逻辑
   - 优化性能

3. **前端Hunter组件**
   - 改进错误显示
   - 优化加载状态
   - 改进筛选逻辑

## 测试结果

运行测试后，所有测试用例应该通过。如果测试失败：

1. 查看错误信息
2. 分析根本原因
3. 修复实现代码（不修改测试）
4. 重新运行测试验证修复

## 与Dashboard测试的区别

Hunter测试相比Dashboard测试更复杂，因为：
1. 涉及因子计算（RPS、量比等）
2. 涉及策略筛选逻辑
3. 涉及数据转换（DataFrame到JSON）
4. 涉及与Portfolio的集成（添加持仓）

因此测试中大量使用了Mock来简化这些复杂流程，重点测试API层和数据流。
