"""
认证 API 路由
"""
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer
from app.models.schemas import UserLogin, Token, UserCreate, UserResponse
from app.utils.auth import create_access_token, verify_token
from passlib.context import CryptContext
from datetime import timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 临时用户存储（生产环境应使用数据库）
fake_users_db = {
    "admin@abc.com": {
        "id": 1,
        "email": "admin@abc.com",
        "hashed_password": pwd_context.hash("admin123"),
        "full_name": "管理员",
        "is_active": True
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    """
    用户登录
    
    Returns:
        JWT Token
    """
    user = fake_users_db.get(user_credentials.email)
    
    if not user or not verify_password(user_credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    access_token_expires = timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    access_token = create_access_token(
        data={"sub": user["email"], "user_id": user["id"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """
    用户注册（仅开发环境）
    """
    if settings.MODE == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="生产环境不支持注册"
        )
    
    if user_data.email in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户已存在"
        )
    
    # 创建新用户
    user_id = len(fake_users_db) + 1
    fake_users_db[user_data.email] = {
        "id": user_id,
        "email": user_data.email,
        "hashed_password": get_password_hash(user_data.password),
        "full_name": user_data.full_name,
        "is_active": True
    }
    
    user = fake_users_db[user_data.email]
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        is_active=user["is_active"],
        created_at=None  # 简化处理
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(verify_token)):
    """
    获取当前用户信息
    """
    email = current_user.get("sub")
    user = fake_users_db.get(email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        is_active=user["is_active"],
        created_at=None
    )

