"""
创建默认注册码的脚本
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db, init_db
from app.db.models import RegistrationCode, User


async def create_default_registration_code():
    """创建默认注册码"""
    await init_db()
    
    async for db in get_db():
        # 检查是否已存在默认注册码
        result = await db.execute(
            select(RegistrationCode).where(RegistrationCode.code == "WELCOME2024")
        )
        existing_code = result.scalar_one_or_none()
        
        if existing_code:
            print("默认注册码已存在")
            return
        
        # 获取管理员用户
        result = await db.execute(
            select(User).where(User.role == "admin")
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            print("错误：未找到管理员用户")
            return
        
        # 创建默认注册码
        default_code = RegistrationCode(
            code="WELCOME2024",
            description="Default registration code",
            is_active=True,
            max_uses=None,  # 无限制
            created_by=admin_user.id
        )
        
        db.add(default_code)
        await db.commit()
        
        print("✅ 默认注册码创建成功: WELCOME2024")
        break


if __name__ == "__main__":
    asyncio.run(create_default_registration_code())
