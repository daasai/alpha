# DAAS Alpha 服务管理脚本使用指南

## 概述

`daas.sh` 是一个用于管理 DAAS Alpha 项目服务的脚本，支持启动、停止、重启和查询服务运行状态。

## 功能特性

- ✅ **启动服务**: 支持启动 API 和前端服务
- ✅ **停止服务**: 优雅停止服务，必要时强制终止
- ✅ **重启服务**: 一键重启所有服务
- ✅ **状态查询**: 实时查看服务运行状态
- ✅ **日志管理**: 自动记录服务日志
- ✅ **进程管理**: 使用 PID 文件跟踪进程
- ✅ **端口检测**: 自动检测端口占用情况

## 快速开始

### 基本用法

```bash
# 启动所有服务
./daas.sh start

# 查看服务状态
./daas.sh status

# 停止所有服务
./daas.sh stop

# 重启所有服务
./daas.sh restart
```

### 命令列表

| 命令 | 说明 |
|------|------|
| `start` | 启动所有服务 (API + 前端) |
| `start-api` | 仅启动 API 服务 |
| `start-frontend` | 仅启动前端服务 |
| `stop` | 停止所有服务 |
| `stop-api` | 仅停止 API 服务 |
| `stop-frontend` | 仅停止前端服务 |
| `restart` | 重启所有服务 |
| `status` | 查询服务运行状态 |
| `help` | 显示帮助信息 |

## 服务配置

### API 服务

- **地址**: http://127.0.0.1:8000
- **文档**: http://127.0.0.1:8000/docs
- **日志**: `logs/api.log`
- **PID 文件**: `.pids/api.pid`

### 前端服务

- **地址**: http://localhost:3000 (或自动递增端口)
- **日志**: `logs/frontend.log`
- **PID 文件**: `.pids/frontend.pid`

## 使用示例

### 1. 启动所有服务

```bash
./daas.sh start
```

输出示例：
```
=== 启动所有服务 ===

启动 API 服务...
✓ API 服务启动成功 (PID: 12345, Port: 8000)
  API 地址: http://127.0.0.1:8000
  API 文档: http://127.0.0.1:8000/docs
  日志文件: logs/api.log

启动前端服务...
✓ 前端服务启动成功 (PID: 12346)
  前端地址: http://localhost:3000
  日志文件: logs/frontend.log

=== 启动完成 ===
```

### 2. 查看服务状态

```bash
./daas.sh status
```

输出示例：
```
=== DAAS Alpha 服务状态 ===

✓ API 服务: 运行中 (PID: 12345, Port: 8000)
  端口 8000 正在监听

✓ 前端服务: 运行中 (PID: 12346, Port: 3000)

日志文件:
  API:     logs/api.log
  前端:    logs/frontend.log
```

### 3. 仅启动 API 服务

```bash
./daas.sh start-api
```

### 4. 仅启动前端服务

```bash
./daas.sh start-frontend
```

### 5. 停止所有服务

```bash
./daas.sh stop
```

### 6. 重启服务

```bash
./daas.sh restart
```

## 目录结构

脚本会自动创建以下目录和文件：

```
daas-alpha/
├── .pids/              # PID 文件目录
│   ├── api.pid        # API 服务进程 ID
│   └── frontend.pid   # 前端服务进程 ID
├── logs/              # 日志文件目录
│   ├── api.log        # API 服务日志
│   └── frontend.log   # 前端服务日志
└── daas.sh            # 服务管理脚本
```

## 故障排查

### 1. 端口被占用

如果启动时提示端口被占用：

```bash
# 查看占用端口的进程
lsof -i :8000
lsof -i :3000

# 停止占用端口的进程，或修改脚本中的端口配置
```

### 2. 服务启动失败

检查日志文件：

```bash
# 查看 API 日志
tail -f logs/api.log

# 查看前端日志
tail -f logs/frontend.log
```

### 3. PID 文件残留

如果进程已停止但 PID 文件仍存在：

```bash
# 手动清理 PID 文件
rm -f .pids/*.pid
```

### 4. 权限问题

确保脚本有执行权限：

```bash
chmod +x daas.sh
```

### 5. 依赖未安装

前端服务首次启动会自动安装依赖，如果失败：

```bash
cd frontend
npm install
cd ..
```

## 高级用法

### 后台运行

脚本使用 `nohup` 在后台运行服务，即使关闭终端也不会停止。

### 自定义配置

编辑 `daas.sh` 文件可以修改以下配置：

```bash
# API 配置
API_HOST="127.0.0.1"
API_PORT=8000

# 日志文件路径
API_LOG="$LOG_DIR/api.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"
```

### 查看实时日志

```bash
# 查看 API 实时日志
tail -f logs/api.log

# 查看前端实时日志
tail -f logs/frontend.log

# 同时查看两个日志
tail -f logs/*.log
```

## 注意事项

1. **首次启动**: 前端服务首次启动会自动安装 npm 依赖，可能需要一些时间
2. **端口冲突**: 如果端口被占用，脚本会提示错误，需要手动处理
3. **日志文件**: 日志文件会持续增长，建议定期清理或使用日志轮转
4. **进程管理**: 脚本使用 PID 文件跟踪进程，异常退出时可能需要手动清理
5. **环境要求**: 确保已安装 Python 和 Node.js/npm

## 系统要求

- macOS / Linux
- Python 3.x
- Node.js 和 npm
- Bash shell

## 相关文档

- [API 启动指南](./API_STARTUP_GUIDE.md)
- [前端启动指南](./FRONTEND_STARTUP_GUIDE.md)
- [CORS 配置](./CORS_CONFIGURATION.md)
