"""
应用配置管理
使用 pydantic-settings 管理环境变量
"""

from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv
from pathlib import Path

# 自动定位项目根目录（即包含 frontend 和 backend 的目录）
BASE_DIR = Path(__file__).resolve().parents[3]

# .env 路径（根目录下）
ENV_PATH = BASE_DIR / ".env"

# 加载 .env
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

# # 本地环境加载 .env
# if not os.getenv("AWS_EXECUTION_ENV") and os.getenv("MODE") != "production":
#     load_dotenv()


class Settings(BaseSettings):
    """应用配置"""

    # 模式：development | production
    MODE: str = os.getenv("MODE", "development")

    # API 配置
    API_PREFIX: str = os.getenv("API_PREFIX", "/api/v1")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

    # OpenAI 配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

    # Qdrant 配置
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "knowledge_base")

    # JWT 配置
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_HOURS: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

    # CORS 配置
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://www.kabi.pro")

    @property
    def CORS_ORIGINS(self) -> List[str]:
        """CORS 允许的来源"""
        if self.MODE == "development":
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://localhost:3002",
            ]

        # 生产允许的域名
        env_origins = os.getenv("CORS_ORIGINS")
        if env_origins:
            return [origin.strip() for origin in env_origins.split(",")]

        return [
            "https://kabi.pro",
            "https://www.kabi.pro",
            "https://api.kabi.pro",
        ]

    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        if self.MODE == "development":
            return ["*"]

        return [
            "*",
            "localhost",
            "127.0.0.1",
            "api.kabi.pro",
            "*.kabi.pro",
        ]

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CLOUDWATCH_LOG_GROUP: str = os.getenv("CLOUDWATCH_LOG_GROUP", "knowledgehub-logs")

    # 数据库配置（必须是字段，不是 property！！！）
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./knowledgehub.db"
    )

    # Redis（可选）
    REDIS_URL: str = os.getenv("REDIS_URL", "")

    # 本地文件存储路径
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")

    # AWS S3 配置
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-west-1")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    
    # 存储类型: local | s3
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步版本数据库 URL（用于 Alembic）"""
        url = self.DATABASE_URL
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        return url.replace("+aiosqlite", "").replace("+asyncpg", "")

    # 生产环境安全检查
    def model_post_init(self, __context):
        if self.MODE == "production":
            if self.JWT_SECRET_KEY == "change-this-secret-key-in-production":
                raise ValueError(
                    "生产环境禁止使用默认 JWT_SECRET_KEY，请配置 Secrets Manager。"
                )

    class Config:
        env_file = None
        case_sensitive = True


# 全局 settings 实例
settings = Settings()
