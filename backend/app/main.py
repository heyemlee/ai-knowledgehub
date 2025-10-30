"""
FastAPI 主应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings
from app.api import auth, chat, documents

app = FastAPI(
    title="ABC AI Knowledge Hub API",
    description="企业级知识库系统 API",
    version="1.0.0",
    docs_url="/docs" if settings.MODE == "development" else None,
    redoc_url="/redoc" if settings.MODE == "development" else None,
)

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

