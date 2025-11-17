"""
应用配置管理
使用 pydantic-settings 管理环境变量
"""

from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

if not os.getenv("AWS_EXECUTION_ENV") and os.getenv("MODE") != "production":
    from dotenv import load_dotenv
    load_dotenv()


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
    
    def model_post_init(self, __context):
        """初始化后验证，检查生产环境敏感设置"""
        if self.MODE == "production":
            # 生产环境安全检查
            if self.JWT_SECRET_KEY == "change-this-secret-key-in-production":
                import logging
                logger = logging.getLogger(__name__)
                logger.error(
                    "🚨 严重安全错误：生产环境使用了默认的 JWT_SECRET_KEY。"
                    "必须设置环境变量 JWT_SECRET_KEY 为强随机密钥。"
                )
                raise ValueError(
                    "生产环境禁止使用默认 JWT_SECRET_KEY。"
                    "请在环境变量中设置一个强随机密钥。"
                )
    
    # CORS 配置
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    @property
    def CORS_ORIGINS(self) -> List[str]:
        """CORS 允许的来源"""
        if self.MODE == "development":
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:3001",
                "http://localhost:3002",
                "http://localhost:3003",
            ]
        return [self.FRONTEND_URL]
    
    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        """允许的主机"""
        if self.MODE == "development":
            return ["*"]
        return ["api.abc.com", "*.abc.com"]
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CLOUDWATCH_LOG_GROUP: str = os.getenv("CLOUDWATCH_LOG_GROUP", "knowledgehub-logs")
    
    # 数据库配置
    @property
    def DATABASE_URL(self) -> str:
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
        # 如果没有设置 DATABASE_URL，使用 SQLite 作为默认值
        return "sqlite+aiosqlite:///./knowledgehub.db"
    
    # Redis 配置（可选，用于缓存）
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    # 本地存储配置
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步数据库 URL（用于 Alembic 迁移）"""
        url = self.DATABASE_URL
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite://", "sqlite://")
        return url.replace("+aiosqlite", "").replace("+asyncpg", "")
    
    class Config:
        env_file = None
        case_sensitive = True


settings = Settings()

