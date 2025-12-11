"""
认证 API 路由
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.schemas import UserLogin, Token, UserCreate, UserResponse
from app.utils.auth import create_access_token, get_current_user
from app.db.database import get_db
from app.db.models import User
from app.middleware.rate_limit import limiter
from app.core.constants import RateLimitConfig
from passlib.context import CryptContext
from datetime import timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """从数据库获取用户"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@router.post("/login", response_model=Token)
@limiter.limit(RateLimitConfig.AUTH_RATE_LIMIT)
async def login(
    request: Request,
    user_credentials: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录
    
    Returns:
        JWT Token
    """
    user = await get_user_by_email(db, user_credentials.email)
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
@limiter.limit(RateLimitConfig.AUTH_RATE_LIMIT)
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    用户注册
    """
    # if settings.MODE == "production":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="生产环境不支持注册"
    #     )
    
    # 验证注册码
    from app.db.models import RegistrationCode
    result = await db.execute(
        select(RegistrationCode).where(
            RegistrationCode.code == user_data.registration_code,
            RegistrationCode.is_active == True
        )
    )
    reg_code = result.scalar_one_or_none()
    
    if not reg_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册码无效或已禁用"
        )
    
    # 检查 Token 配额
    if reg_code.token_quota is not None:
        remaining_tokens = reg_code.token_quota - reg_code.tokens_used
        if remaining_tokens < reg_code.tokens_per_registration:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"注册码 Token 配额不足。剩余: {remaining_tokens} tokens, 需要: {reg_code.tokens_per_registration} tokens"
            )
    
    # 检查用户是否已存在
    existing_user = await get_user_by_email(db, user_data.account)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已存在"
        )
    
    # 创建新用户
    new_user = User(
        email=user_data.account,  # 使用 account 字段作为 email
        hashed_password=get_password_hash(user_data.password),
        full_name=None,  # 不再使用 full_name
        is_active=True
    )
    
    db.add(new_user)
    
    # 消耗 Token 配额
    reg_code.tokens_used += reg_code.tokens_per_registration
    
    await db.commit()
    await db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        is_active=new_user.is_active,
        role=new_user.role,
        created_at=new_user.created_at
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户信息
    """
    email = current_user.get("sub")
    user = await get_user_by_email(db, email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        role=user.role,
        created_at=user.created_at
    )


async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """
    检查当前用户是否是管理员
    """
    user_role = current_user.get("role")
    
    if user_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    
    return current_user
