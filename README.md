# DAAS Alpha 量化选股系统

基于价值与质量因子的多因子选股与公告异动监控系统，支持 Tushare Pro 与东方财富免费 API。

## 运行

**Phase 1（批处理）**
```bash
python3 main.py
```

**Phase 2（DAAS Alpha Streamlit）**
```bash
streamlit run app.py
```
需在 `.env` 中配置：`TUSHARE_TOKEN`、`OPENAI_API_KEY`；可选 `OPENAI_API_BASE`（如 DeepSeek：`https://api.deepseek.com`）、`OPENAI_MODEL`（模型名称，默认：`gpt-3.5-turbo`）。数据库：`data/daas.db`。

首次使用请先阅读 [docs/QUICK_START.md](docs/QUICK_START.md)（依赖安装、Python 版本、常见问题）。

## 诊断工具

测试公告 API 是否正常（Tushare / 东方财富）：

```bash
python3 diagnose_notices.py
```

测试 AI 评分接口是否正常：

```bash
python3 tests/test_ai_scoring.py
# 或
python3 -m tests.test_ai_scoring
```

## 文档

| 文档 | 说明 |
|------|------|
| [docs/QUICK_START.md](docs/QUICK_START.md) | 快速开始、安装、运行、测试 |
| [docs/Project DAAS Alpha - Phase 1 MVP Specification.md](docs/Project%20DAAS%20Alpha%20-%20Phase%201%20MVP%20Specification.md) | 产品规格 |
| [docs/NOTICES_API_USAGE.md](docs/NOTICES_API_USAGE.md) | 公告 API（Tushare / 东方财富）使用说明 |
| [docs/REFACTORING.md](docs/REFACTORING.md) | 高优先级改造说明 |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | 变更日志 |
| [docs/TEST_REPORT.md](docs/TEST_REPORT.md) | 测试报告 |

## 测试

```bash
python3 -m pytest tests/ -v
```

## 项目结构

```
config/       # 配置（settings.yaml, keywords.yaml）
data/         # 数据目录（output, raw, daas.db）
docs/         # 文档
src/          # 源码（data_loader, strategy, monitor, reporter, database, data_provider, api…）
tests/        # 测试
main.py       # 入口
app.py        # DAAS Alpha Streamlit 入口
diagnose_notices.py  # 公告 API 诊断
```
