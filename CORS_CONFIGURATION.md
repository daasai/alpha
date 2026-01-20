# CORS配置说明

## 配置完成 ✅

已成功配置后端CORS以允许前端请求，并优化了前端API客户端以使用Vite代理。

---

## 🔧 已完成的更改

### 1. 后端CORS配置更新

**文件**: `api/config.py`

**更改内容**:
- 扩展了CORS允许的源列表，包含常见开发端口（3000-3005）
- 支持Vite自动端口选择功能
- 同时支持`localhost`和`127.0.0.1`

**允许的源**:
```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:3005",
    "http://localhost:5173",  # Vite default port
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:3003",
    "http://127.0.0.1:3004",
    "http://127.0.0.1:3005",
    "http://127.0.0.1:5173",
]
```

### 2. 前端API客户端优化

**文件**: 
- `frontend/src/api/client.ts`
- `frontend/src/api/endpoints.ts`

**更改内容**:
- 在开发环境中使用相对路径（空字符串），利用Vite代理
- 在生产环境中使用完整的API URL
- 优先使用环境变量`VITE_API_BASE_URL`

**工作原理**:
1. **开发环境**: 使用空字符串作为baseURL，请求路径为`/api/...`
   - Vite代理自动将`/api`请求转发到`http://localhost:8000/api`
   - 这样请求是同源的，不需要CORS
   
2. **生产环境**: 使用完整的API URL（从环境变量或默认值）
   - 直接访问后端API，需要CORS配置

---

## 🎯 两种请求方式

### 方式1: 通过Vite代理（推荐，开发环境）

```
前端 (http://localhost:3000)
  ↓ 请求 /api/dashboard/overview
Vite代理
  ↓ 转发到 http://localhost:8000/api/dashboard/overview
后端API (http://localhost:8000)
```

**优点**:
- ✅ 不需要CORS（同源请求）
- ✅ 自动处理跨域问题
- ✅ 开发体验更好

### 方式2: 直接访问后端（生产环境或需要时）

```
前端 (http://localhost:3000)
  ↓ 直接请求 http://localhost:8000/api/dashboard/overview
后端API (http://localhost:8000)
  ↓ 检查CORS配置
返回响应（带CORS头）
```

**优点**:
- ✅ 可以绕过代理
- ✅ 需要CORS配置支持

---

## 📝 环境变量配置

### 开发环境

如果需要在开发环境中直接访问后端（不使用代理），可以设置：

```bash
# .env 文件
VITE_API_BASE_URL=http://localhost:8000
```

### 生产环境

生产环境必须设置完整的API URL：

```bash
# .env.production 文件
VITE_API_BASE_URL=https://api.yourdomain.com
```

---

## 🔍 验证配置

### 1. 检查后端CORS配置

```bash
# 启动后端
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000

# 测试CORS（使用curl）
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://127.0.0.1:8000/api/dashboard/overview \
     -v
```

应该看到响应头包含：
```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
```

### 2. 检查前端代理

```bash
# 启动前端
cd frontend
npm run dev

# 在浏览器中打开 http://localhost:3000
# 打开开发者工具 -> Network标签
# 查看API请求，应该看到：
# - 请求URL: http://localhost:3000/api/dashboard/overview
# - 状态: 200 OK
# - 没有CORS错误
```

### 3. 检查浏览器控制台

打开浏览器控制台，应该：
- ✅ 没有CORS错误
- ✅ API请求成功
- ✅ 数据正常加载

---

## 🚨 故障排除

### 问题1: 仍然看到CORS错误

**可能原因**:
1. 后端没有重启
2. 前端使用了错误的端口
3. 环境变量配置错误

**解决方案**:
1. 重启后端服务器
2. 检查前端实际运行的端口，确保在CORS允许列表中
3. 检查`.env`文件中的`VITE_API_BASE_URL`配置

### 问题2: 代理不工作

**可能原因**:
1. Vite配置错误
2. 前端API客户端使用了绝对URL

**解决方案**:
1. 检查`vite.config.ts`中的代理配置
2. 确保开发环境中`API_BASE_URL`为空字符串或未设置
3. 检查网络请求，应该看到请求发送到`/api/...`而不是`http://localhost:8000/api/...`

### 问题3: 需要添加新的端口

如果前端运行在其他端口（例如3006），可以：

**方案1**: 更新`api/config.py`中的`CORS_ORIGINS`列表

**方案2**: 使用环境变量（推荐）
```bash
# .env 文件
CORS_ORIGINS=http://localhost:3006,http://127.0.0.1:3006
```

---

## 📊 配置总结

| 配置项 | 开发环境 | 生产环境 |
|--------|---------|---------|
| 前端baseURL | `''` (空字符串) | `VITE_API_BASE_URL` 或默认值 |
| 请求方式 | 通过Vite代理 | 直接访问后端 |
| CORS需求 | 不需要（同源） | 需要（跨域） |
| 后端CORS配置 | 已配置多个端口 | 需要配置生产域名 |

---

## ✅ 测试清单

- [x] 后端CORS配置已更新
- [x] 前端API客户端已优化
- [x] Vite代理配置正确
- [ ] 测试开发环境请求（通过代理）
- [ ] 测试生产环境请求（直接访问）
- [ ] 验证所有API端点正常工作

---

## 🎉 完成

CORS配置已完成！现在前端应该可以正常访问后端API了。

如果遇到任何问题，请检查：
1. 后端服务器是否运行
2. 前端服务器是否运行
3. 浏览器控制台是否有错误
4. 网络请求是否成功

---

*配置完成时间: 2025年1月*  
*配置人员: AI Assistant*
