#!/usr/bin/env python3
"""
清理孤立的 token_usage 记录
删除所有 user_id 为 NULL 的记录
"""
import asyncio
from sqlalchemy import text
from app.db.database import engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def cleanup_orphaned_token_usage():
    """清理孤立的 token_usage 记录"""
    try:
        async with engine.begin() as conn:
            # 查询孤立记录数量
            count_query = text("""
                SELECT COUNT(*) 
                FROM token_usage 
                WHERE user_id IS NULL
            """)
            result = await conn.execute(count_query)
            orphaned_count = result.scalar()
            
            if orphaned_count == 0:
                logger.info("✓ No orphaned token_usage records found")
                return
            
            logger.info(f"Found {orphaned_count} orphaned token_usage records")
            
            # 删除孤立记录
            delete_query = text("""
                DELETE FROM token_usage 
                WHERE user_id IS NULL
            """)
            await conn.execute(delete_query)
            
            logger.info(f"✓ Successfully deleted {orphaned_count} orphaned records")
            
    except Exception as e:
        logger.error(f"Failed to cleanup orphaned records: {e}", exc_info=True)
        raise


async def main():
    """主函数"""
    logger.info("Starting cleanup of orphaned token_usage records...")
    await cleanup_orphaned_token_usage()
    logger.info("Cleanup completed!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
