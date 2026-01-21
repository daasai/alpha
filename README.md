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

首次使用请先阅读 [docs/guides/QUICK_START.md](docs/guides/QUICK_START.md)（依赖安装、Python 版本、常见问题）。

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

### 📚 文档索引
- **[文档索引](docs/DOCUMENTATION_INDEX.md)** - 所有文档的索引和导航

### 🎯 核心文档
| 文档 | 说明 |
|------|------|
| [docs/product/PRODUCT_SPEC.md](docs/product/PRODUCT_SPEC.md) | 产品规格文档（完整功能说明） |
| [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | 架构概览（系统架构快速参考） |
| [docs/architecture/ARCHITECTURE_REVIEW_REPORT.md](docs/architecture/ARCHITECTURE_REVIEW_REPORT.md) | 架构审查报告（详细分析） |

### 🚀 快速开始
| 文档 | 说明 |
|------|------|
| [docs/guides/QUICK_START.md](docs/guides/QUICK_START.md) | 快速开始、安装、运行、测试 |
| [docs/guides/API_STARTUP_GUIDE.md](docs/guides/API_STARTUP_GUIDE.md) | API 服务启动指南 |
| [docs/guides/FRONTEND_STARTUP_GUIDE.md](docs/guides/FRONTEND_STARTUP_GUIDE.md) | 前端开发环境配置 |
| [docs/guides/DAILY_RUNNER_USER_GUIDE.md](docs/guides/DAILY_RUNNER_USER_GUIDE.md) | Daily Runner 定时任务使用手册 |

### 🔧 技术文档
| 文档 | 说明 |
|------|------|
| [docs/guides/DAILY_RUNNER_USER_GUIDE.md](docs/guides/DAILY_RUNNER_USER_GUIDE.md) | Daily Runner 定时任务使用手册 |
| [docs/technical/CORS_CONFIGURATION.md](docs/technical/CORS_CONFIGURATION.md) | CORS 配置说明 |
| [docs/technical/NOTICES_API_USAGE.md](docs/technical/NOTICES_API_USAGE.md) | 公告 API（Tushare / 东方财富）使用说明 |
| [docs/technical/REFACTORING.md](docs/technical/REFACTORING.md) | 高优先级改造说明 |
| [docs/technical/SERVICE_MANAGEMENT.md](docs/technical/SERVICE_MANAGEMENT.md) | 服务管理文档 |

### 📊 测试与质量
| 文档 | 说明 |
|------|------|
| [docs/testing/TEST_REPORT.md](docs/testing/TEST_REPORT.md) | 测试报告 |
| [docs/testing/FRONTEND_TEST_REPORT.md](docs/testing/FRONTEND_TEST_REPORT.md) | 前端测试报告 |

### 📝 变更记录
| 文档 | 说明 |
|------|------|
| [docs/changelog/CHANGELOG.md](docs/changelog/CHANGELOG.md) | 变更日志 |

### 📖 文档维护
| 文档 | 说明 |
|------|------|
| [docs/DOCUMENTATION_MAINTENANCE.md](docs/DOCUMENTATION_MAINTENANCE.md) | 文档维护指南 |

### 📜 历史文档
| 文档 | 说明 |
|------|------|
| [docs/product/Project DAAS Alpha - Phase 1 MVP Specification.md](docs/product/Project%20DAAS%20Alpha%20-%20Phase%201%20MVP%20Specification.md) | Phase 1 MVP 规格（历史文档） |

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
