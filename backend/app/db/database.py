"""
数据库连接和会话管理
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.MODE == "development",
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncSession:
    """
    获取数据库会话（依赖注入）
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库（创建表）
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


async def close_db():
    """
    关闭数据库连接
    """
    await engine.dispose()
    logger.info("数据库连接已关闭")









