"""
数据库初始化脚本
创建数据库表并创建默认管理员用户
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_db, engine, AsyncSessionLocal
from app.db.init_data import create_admin_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """主函数"""
    try:
        logger.info("开始初始化数据库...")
        await init_db()
        logger.info("数据库表创建完成")
        
        logger.info("创建默认管理员用户...")
        await create_admin_user()
        
        logger.info("数据库初始化完成！")
        logger.info("默认管理员账号: admin@abc.com / admin123")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

