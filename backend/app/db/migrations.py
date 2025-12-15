"""
数据库迁移模块
支持 PostgreSQL (asyncpg) 和 SQLite
在应用启动时自动运行
"""
import logging
from sqlalchemy import text
from app.db.database import engine

logger = logging.getLogger(__name__)


async def run_migrations():
    """运行所有数据库迁移"""
    try:
        logger.info("Starting database migrations...")
        
        # 迁移 1: 添加 token_quota 字段
        await migrate_add_token_quota()
        
        logger.info("All migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration error: {e}", exc_info=True)
        # 不抛出异常，避免阻止应用启动
        logger.warning("Migration failed, but application will continue to start")


async def migrate_add_token_quota():
    """迁移：为 users 表添加 token_quota 字段"""
    try:
        async with engine.begin() as conn:
            # 检查字段是否已存在
            # PostgreSQL 和 SQLite 都支持这种查询方式
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name = 'token_quota'
            """)
            
            result = await conn.execute(check_query)
            exists = result.fetchone() is not None
            
            if exists:
                logger.info("✓ token_quota field already exists, skipping migration")
                return
            
            logger.info("Adding token_quota field to users table...")
            
            # 添加字段 - PostgreSQL 语法
            alter_query = text("""
                ALTER TABLE users 
                ADD COLUMN token_quota INTEGER NOT NULL DEFAULT 800000
            """)
            
            await conn.execute(alter_query)
            logger.info("✓ Successfully added token_quota field")
            
            # 验证
            count_query = text("SELECT COUNT(*) FROM users")
            result = await conn.execute(count_query)
            user_count = result.scalar()
            logger.info(f"✓ Migration completed. {user_count} users updated with default quota")
            
    except Exception as e:
        # 如果是因为字段已存在导致的错误，忽略
        error_msg = str(e).lower()
        if 'already exists' in error_msg or 'duplicate column' in error_msg:
            logger.info("✓ token_quota field already exists (detected via error), skipping migration")
            return
        
        logger.error(f"Failed to add token_quota field: {e}", exc_info=True)
        raise
