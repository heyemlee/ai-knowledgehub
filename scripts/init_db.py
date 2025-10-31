"""
数据库初始化脚本
创建数据库表并创建默认管理员用户
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_db, engine, AsyncSessionLocal
from app.db.models import User
from passlib.context import CryptContext
import logging

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_admin_user():
    """创建默认管理员用户"""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        
        result = await session.execute(
            select(User).where(User.email == "admin@abc.com")
        )
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            logger.info("管理员用户已存在，跳过创建")
            return
        
        admin_user = User(
            email="admin@abc.com",
            hashed_password=get_password_hash("admin123"),
            full_name="管理员",
            is_active=True
        )
        
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)
        
        logger.info(f"管理员用户创建成功: {admin_user.email} (ID: {admin_user.id})")


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

