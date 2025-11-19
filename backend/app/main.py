"""
FastAPI 主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from contextlib import asynccontextmanager
from app.core.config import settings
from app.api import (
    auth, chat, documents, conversations, token_usage, api_keys, admin
)
from app.db.database import init_db, close_db
from app.db.init_data import create_admin_user
from app.middleware.rate_limit import limiter, RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.middleware.monitoring import MonitoringMiddleware, set_monitoring_instance

import logging
logger = logging.getLogger(__name__)


# ==============================
# Lifespan
# ==============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await create_admin_user()
    yield
    await close_db()


# ==============================
# FastAPI 实例
# ==============================
app = FastAPI(
    title="ABC AI Knowledge Hub API",
    description="企业级知识库系统 API",
    version="1.0.0",
    docs_url="/docs" if settings.MODE == "development" else None,
    redoc_url="/redoc" if settings.MODE == "development" else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ==============================
# 中间件
# ==============================

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Trusted Host ----
# 必须允许: localhost / 127.0.0.1  否则 ECS 容器内部健康检查会 400
if settings.MODE == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "*",                # 生产 ALB 转发需要
            "localhost",        # 容器自检
            "127.0.0.1",        # 容器自检
            *settings.ALLOWED_HOSTS,  # 你配置的正式域名等
        ],
    )

# ---- Monitoring ----
monitor = MonitoringMiddleware(app)
set_monitoring_instance(monitor)
app.add_middleware(MonitoringMiddleware)


# ==============================
# 路由
# ==============================
app.include_router(auth.router, prefix="/api/v1/auth", tags=["认证"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["问答"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["文档"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["对话"])
app.include_router(token_usage.router, prefix="/api/v1/token-usage", tags=["Token 使用量"])
app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["API Key 管理"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["管理员"])


# ==============================
# 健康检查（ALB 用）
# ==============================
@app.get("/")
async def root():
    return {
        "message": "ABC AI Knowledge Hub API",
        "version": "1.0.0",
        "mode": settings.MODE,
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
