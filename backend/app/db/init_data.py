"""
数据库初始化数据
"""
import os
import logging
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.db.database import AsyncSessionLocal
from app.db.models import User
from passlib.context import CryptContext

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)

async def create_admin_user():
    """创建默认管理员用户"""
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(User).where(User.email == "admin@abc.com")
            )
            admin_user = result.scalar_one_or_none()
            
            if admin_user:
                logger.info("管理员用户已存在，跳过创建")
                return
            
            admin_user = User(
                email="admin@abc.com",
                hashed_password=get_password_hash(os.getenv("ADMIN_PASSWORD", "admin123")),
                full_name="管理员",
                is_active=True,
                role="admin"
            )
            
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            
            logger.info(f"管理员用户创建成功: {admin_user.email} (ID: {admin_user.id})")
        except IntegrityError as e:
            # 如果用户已存在（由于并发创建），这是正常情况，不需要抛出异常
            logger.info(f"管理员用户已存在（并发创建检测到）: {e}")
            await session.rollback()
        except Exception as e:
            logger.error(f"创建管理员用户失败: {e}")
            await session.rollback()
            raise
