# API 启动指南

## 后端API已成功启动

### 当前状态
✅ **API服务器运行在**: `http://127.0.0.1:8000`
✅ **所有端点测试通过**

### 已验证的API端点

1. **Health Check**
   - `GET /health` - ✅ 正常

2. **Dashboard API**
   - `GET /api/dashboard/overview` - ✅ 正常
   - `GET /api/dashboard/market-trend` - ✅ 正常

3. **Hunter API**
   - `GET /api/hunter/filters` - ✅ 正常
   - `POST /api/hunter/scan` - ✅ 正常

4. **Portfolio API**
   - `GET /api/portfolio/positions` - ✅ 正常
   - `GET /api/portfolio/metrics` - ✅ 正常
   - `POST /api/portfolio/positions` - ✅ 正常
   - `PUT /api/portfolio/positions/{id}` - ✅ 正常
   - `DELETE /api/portfolio/positions/{id}` - ✅ 正常
   - `POST /api/portfolio/refresh-prices` - ✅ 正常

5. **Lab API**
   - `POST /api/lab/backtest` - ✅ 正常

### API文档
访问 `http://127.0.0.1:8000/docs` 查看Swagger UI文档

### 已修复的问题

1. ✅ **JSON序列化错误** - 修复了numpy类型（bool_, int64）的序列化问题
2. ✅ **Equity Curve处理** - 修复了Series和DataFrame的处理逻辑
3. ✅ **依赖安装** - 移除了不存在的python-cors包

### 启动命令

```bash
# 在项目根目录
cd /Users/shawn/Data/daas-alpha
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 测试命令

```bash
# 健康检查
curl http://127.0.0.1:8000/health

# Dashboard概览
curl http://127.0.0.1:8000/api/dashboard/overview

# 市场趋势
curl "http://127.0.0.1:8000/api/dashboard/market-trend?days=60"

# Hunter扫描
curl -X POST "http://127.0.0.1:8000/api/hunter/scan" \
  -H "Content-Type: application/json" \
  -d '{"rps_threshold": 85, "volume_ratio_threshold": 1.5}'
```

### 下一步

现在可以启动前端开发服务器：

```bash
cd frontend
npm run dev
```

前端将运行在 `http://localhost:3000`，并自动代理API请求到后端。
