"""
FastAPI 主应用入口
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import auth, chat, documents, conversations, token_usage, api_keys
from app.db.database import init_db, close_db
from app.middleware.rate_limit import limiter, RateLimitExceeded
from app.middleware.monitoring import MonitoringMiddleware, set_monitoring_instance
from slowapi import _rate_limit_exceeded_handler
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="ABC AI Knowledge Hub API",
    description="企业级知识库系统 API",
    version="1.0.0",
    docs_url="/docs" if settings.MODE == "development" else None,
    redoc_url="/redoc" if settings.MODE == "development" else None,
    lifespan=lifespan,
)

# 添加限流异常处理器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# API 监控中间件（最先添加，以便记录所有请求）
monitoring_middleware = MonitoringMiddleware(app)
set_monitoring_instance(monitoring_middleware)
app.add_middleware(MonitoringMiddleware)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 信任主机中间件（生产环境）
if settings.MODE == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# 注册路由
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["问答"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["文档"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["对话"])
app.include_router(token_usage.router, prefix="/api/v1/token-usage", tags=["Token使用量"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Key管理"])


@app.get("/")
async def root():
    return {
        "message": "ABC AI Knowledge Hub API",
        "version": "1.0.0",
        "mode": settings.MODE,
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "mode": settings.MODE}

@app.get("/api/v1/metrics")
async def get_metrics():
    """
    获取 API 监控指标
    
    仅在生产环境或开发环境开启时可用
    """
    from app.middleware.monitoring import get_monitoring_instance
    
    monitoring = get_monitoring_instance()
    if not monitoring:
        return JSONResponse(
            status_code=503,
            content={"error": "监控服务未初始化"}
        )
    
    stats = monitoring.get_statistics()
    return stats


