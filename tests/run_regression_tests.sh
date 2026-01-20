#!/bin/bash
# 回归测试执行脚本

echo "=========================================="
echo "DAAS Alpha 重构回归测试"
echo "=========================================="
echo ""

# 设置颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
TOTAL=0
PASSED=0
FAILED=0

# 运行测试函数
run_test() {
    local test_name=$1
    local test_file=$2
    
    echo -e "${YELLOW}运行测试: ${test_name}${NC}"
    echo "文件: ${test_file}"
    echo "---"
    
    if pytest "${test_file}" -v --tb=short; then
        echo -e "${GREEN}✓ ${test_name} 通过${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ ${test_name} 失败${NC}"
        ((FAILED++))
    fi
    ((TOTAL++))
    echo ""
}

# P0 优先级测试（必须通过）
echo "=========================================="
echo "P0 优先级测试（必须通过）"
echo "=========================================="
echo ""

run_test "Hunter工作流回归测试" "tests/test_hunter_service_regression.py"
run_test "Backtest工作流回归测试" "tests/test_backtest_service_regression.py"
run_test "Truth工作流回归测试" "tests/test_truth_service_regression.py"
run_test "Service层基础功能" "tests/test_services.py"
run_test "页面路由测试" "tests/test_pages_regression.py"

# P1 优先级测试（重要）
echo "=========================================="
echo "P1 优先级测试（重要）"
echo "=========================================="
echo ""

run_test "Service层异常处理" "tests/test_services_exceptions.py"
run_test "配置管理测试" "tests/test_config_regression.py"
run_test "策略配置集成测试" "tests/test_strategy_config.py"
run_test "Repository层功能" "tests/test_repositories.py"

# P2 优先级测试（补充）
echo "=========================================="
echo "P2 优先级测试（补充）"
echo "=========================================="
echo ""

run_test "UI功能测试" "tests/test_ui_functionality.py"
run_test "异常体系测试" "tests/test_exceptions_regression.py"
run_test "端到端集成测试" "tests/test_integration_regression.py"

# 汇总结果
echo "=========================================="
echo "测试结果汇总"
echo "=========================================="
echo -e "总计: ${TOTAL}"
echo -e "${GREEN}通过: ${PASSED}${NC}"
echo -e "${RED}失败: ${FAILED}${NC}"
echo ""

if [ ${FAILED} -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}✗ 有 ${FAILED} 个测试失败${NC}"
    exit 1
fi
