# 重构回归测试说明

## 概述

本目录包含针对架构重构的全面回归测试，确保重构后的代码功能正常，没有破坏现有功能。

## 测试文件列表

### P0 优先级（必须通过）

1. **test_hunter_service_regression.py** - Hunter工作流回归测试
   - 验证HunterService与原有逻辑等价性
   - 测试数据获取、因子计算、策略筛选流程

2. **test_backtest_service_regression.py** - Backtest工作流回归测试
   - 验证BacktestService与原有逻辑等价性
   - 测试回测参数传递和结果计算

3. **test_truth_service_regression.py** - Truth工作流回归测试
   - 验证TruthService功能正确性
   - 测试价格更新和胜率计算

4. **test_services.py** - Service层基础功能测试
   - 测试Service初始化
   - 测试依赖注入功能
   - 测试配置读取

5. **test_pages_regression.py** - 页面路由测试
   - 验证pages模块导入
   - 验证app.py路由逻辑

### P1 优先级（重要）

6. **test_services_exceptions.py** - Service层异常处理测试
   - 测试DataFetchError、StrategyError、FactorError处理
   - 验证错误信息传递

7. **test_config_regression.py** - 配置管理测试
   - 验证所有新增配置项可正确读取
   - 测试配置默认值和降级处理

8. **test_strategy_config.py** - 策略配置集成测试
   - 验证AlphaStrategy从配置读取阈值
   - 测试向后兼容性

9. **test_repositories.py** - Repository层测试
   - 测试PredictionRepository、HistoryRepository、ConstituentRepository
   - 验证数据访问抽象层功能

### P2 优先级（补充）

10. **test_exceptions_regression.py** - 异常体系测试
    - 验证异常类层次结构
    - 测试异常继承关系

11. **test_integration_regression.py** - 端到端集成测试
    - 完整Hunter/Backtest/Truth流程
    - 验证Service到Repository的集成

12. **test_ui_functionality.py** - UI功能测试（已更新）
    - 适配新的pages结构
    - 验证Service层调用

## 运行测试

### 运行所有回归测试

```bash
# 使用脚本（推荐）
./tests/run_regression_tests.sh

# 或使用pytest
pytest tests/test_*_regression.py -v
```

### 运行特定测试

```bash
# 运行P0优先级测试
pytest tests/test_hunter_service_regression.py \
       tests/test_backtest_service_regression.py \
       tests/test_truth_service_regression.py \
       tests/test_services.py \
       tests/test_pages_regression.py -v

# 运行Service层测试
pytest tests/test_services*.py -v

# 运行配置测试
pytest tests/test_config*.py tests/test_strategy_config.py -v

# 运行Repository测试
pytest tests/test_repositories.py -v
```

### 运行完整测试套件（含覆盖率）

```bash
pytest tests/ -v --cov=src --cov-report=html --cov-report=term
```

## 成功标准

### 功能完整性
- ✅ 所有P0测试通过
- ✅ 至少90%的P1测试通过
- ✅ 核心业务流程无回归

### 代码质量
- ✅ 无新的linter错误
- ✅ 测试覆盖率不低于重构前水平

## 测试覆盖范围

### 核心功能
- ✅ Hunter工作流（数据获取 → 因子计算 → 策略筛选）
- ✅ Backtest工作流（历史数据 → 回测执行 → 结果分析）
- ✅ Truth工作流（价格更新 → 胜率计算）

### 新架构组件
- ✅ Service层（HunterService、BacktestService、TruthService）
- ✅ Repository层（PredictionRepository、HistoryRepository、ConstituentRepository）
- ✅ 配置管理（ConfigManager扩展）
- ✅ 异常处理（统一异常体系）

### 页面和路由
- ✅ pages模块导入
- ✅ app.py路由逻辑
- ✅ UI功能完整性

## 注意事项

1. **数据库依赖**: 部分测试需要数据库，会自动创建临时数据库
2. **API Mock**: 测试使用Mock数据，不调用真实API
3. **配置依赖**: 测试会读取config/settings.yaml，确保配置文件存在

## 故障排查

### 测试失败常见原因

1. **导入错误**: 检查Python路径和模块导入
2. **配置缺失**: 确保config/settings.yaml存在且格式正确
3. **数据库错误**: 检查数据库文件权限和路径

### 调试技巧

```bash
# 运行单个测试并显示详细输出
pytest tests/test_hunter_service_regression.py::TestHunterServiceRegression::test_hunter_service_initialization -v -s

# 运行测试并停在第一个失败处
pytest tests/ -x

# 显示测试覆盖率
pytest tests/ --cov=src --cov-report=term-missing
```
