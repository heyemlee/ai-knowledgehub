import ssl
import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.orm import declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# ------------------------------
# 数据库 URL（由 settings 提供）
# 开发：SQLite
# 生产：PostgreSQL (asyncpg)
# ------------------------------

DATABASE_URL = settings.DATABASE_URL


# ------------------------------
# 创建 SSL Context（仅 PostgreSQL 使用）
# asyncpg 不支持 sslmode 参数，只能通过 connect_args 注入 SSL
# ------------------------------
def get_ssl_context():
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE   # RDS 允许无证书 SSL
        return ssl_context
    except Exception as e:
        logger.error(f"创建 SSL Context 失败: {e}")
        return None


# ------------------------------
# 根据环境选择 engine 配置
# ------------------------------
def create_engine_by_mode():
    if DATABASE_URL.startswith("postgresql+asyncpg"):
        # 生产环境 - PostgreSQL + SSL
        ssl_context = get_ssl_context()

        connect_args = {"ssl": ssl_context} if ssl_context else {}

        logger.info("正在使用 PostgreSQL + asyncpg + SSL")

        return create_async_engine(
            DATABASE_URL,
            echo=settings.MODE == "development",
            future=True,
            connect_args=connect_args
        )

    else:
        # 开发模式 SQLite / 其他
        logger.info("正在使用 SQLite（开发环境）")
        return create_async_engine(
            DATABASE_URL,
            echo=True,
            future=True
        )


# 创建 engine
engine = create_engine_by_mode()


# 创建 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


# ------------------------------
# Session 依赖
# ------------------------------
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ------------------------------
# 创建表结构（自动迁移）
# ------------------------------
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


# ------------------------------
# 关闭连接
# ------------------------------
async def close_db():
    await engine.dispose()
    logger.info("数据库连接已关闭")
