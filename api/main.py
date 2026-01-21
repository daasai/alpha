"""
DAAS Alpha FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import APIConfig
from api.utils.exceptions import (
    APIException,
    daas_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from src.exceptions import DAASError
from src.logging_config import setup_logging, get_logger

# 配置日志：输出到 logs/api.log，级别为 DEBUG
setup_logging(log_level='INFO', log_file='logs/api.log')
logger = get_logger(__name__)
logger.info("DAAS Alpha API 服务启动")

# Create FastAPI app
app = FastAPI(
    title=APIConfig.API_TITLE,
    version=APIConfig.API_VERSION,
    description=APIConfig.API_DESCRIPTION,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=APIConfig.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
from api.utils.exceptions import (
    APIException,
    api_exception_handler,
    daas_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
app.add_exception_handler(APIException, api_exception_handler)
app.add_exception_handler(DAASError, daas_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Import routers
from api.routers import dashboard, hunter, portfolio, lab, jobs
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(hunter.router, prefix="/api/hunter", tags=["hunter"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(lab.router, prefix="/api/lab", tags=["lab"])
app.include_router(jobs.router)  # jobs路由已包含/api/v1/jobs前缀


@app.get("/")
async def root():
    """根路径"""
    return {
        "success": True,
        "message": "DAAS Alpha API",
        "version": APIConfig.API_VERSION
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "success": True,
        "status": "healthy",
        "version": APIConfig.API_VERSION
    }


# Task Scheduler - 启动后台调度器（如果启用）
_task_scheduler = None

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    global _task_scheduler
    
    try:
        from src.jobs.scheduler import TaskScheduler
        from src.config_manager import ConfigManager
        
        config = ConfigManager()
        jobs_config = config.get('jobs.daily_runner', {})
        enabled = jobs_config.get('enabled', True)
        
        if enabled:
            # 检查是否已有运行中的调度器（防止重复启动）
            if _task_scheduler and _task_scheduler.is_running():
                logger.warning("任务调度器已在运行，跳过启动")
            else:
                _task_scheduler = TaskScheduler(config=config)
                if _task_scheduler.start():
                    logger.info("任务调度器已启动")
                else:
                    logger.warning("任务调度器启动失败")
        else:
            logger.info("任务调度器已禁用（配置中enabled=false）")
    
    except Exception as e:
        logger.exception(f"启动任务调度器异常: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    global _task_scheduler
    
    if _task_scheduler:
        try:
            _task_scheduler.stop()
            logger.info("任务调度器已停止")
        except Exception as e:
            logger.exception(f"停止任务调度器异常: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=APIConfig.API_HOST,
        port=APIConfig.API_PORT,
        reload=APIConfig.API_RELOAD
    )
