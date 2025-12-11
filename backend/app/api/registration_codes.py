"""
注册码管理 API 路由
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.schemas import RegistrationCodeCreate, RegistrationCodeUpdate, RegistrationCodeResponse
from app.utils.auth import get_current_user
from app.db.database import get_db
from app.db.models import RegistrationCode
from app.api.auth import get_current_admin_user
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[RegistrationCodeResponse])
async def get_registration_codes(
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有注册码（仅管理员）
    """
    result = await db.execute(select(RegistrationCode).order_by(RegistrationCode.created_at.desc()))
    codes = result.scalars().all()
    return codes


@router.post("/", response_model=RegistrationCodeResponse)
async def create_registration_code(
    code_data: RegistrationCodeCreate,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建注册码（仅管理员）
    """
    # 检查注册码是否已存在
    result = await db.execute(
        select(RegistrationCode).where(RegistrationCode.code == code_data.code)
    )
    existing_code = result.scalar_one_or_none()
    
    if existing_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="注册码已存在"
        )
    
    # 创建新注册码
    new_code = RegistrationCode(
        code=code_data.code,
        description=code_data.description,
        token_quota=code_data.token_quota,
        tokens_per_registration=code_data.tokens_per_registration,
        created_by=current_user.get("user_id")
    )
    
    db.add(new_code)
    await db.commit()
    await db.refresh(new_code)
    
    return new_code


@router.put("/{code_id}", response_model=RegistrationCodeResponse)
async def update_registration_code(
    code_id: int,
    code_data: RegistrationCodeUpdate,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    更新注册码（仅管理员）
    """
    result = await db.execute(
        select(RegistrationCode).where(RegistrationCode.id == code_id)
    )
    code = result.scalar_one_or_none()
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="注册码不存在"
        )
    
    # 更新字段
    if code_data.description is not None:
        code.description = code_data.description
    if code_data.is_active is not None:
        code.is_active = code_data.is_active
    if code_data.token_quota is not None:
        code.token_quota = code_data.token_quota
    
    await db.commit()
    await db.refresh(code)
    
    return code


@router.delete("/{code_id}")
async def delete_registration_code(
    code_id: int,
    current_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除注册码（仅管理员）
    """
    result = await db.execute(
        select(RegistrationCode).where(RegistrationCode.id == code_id)
    )
    code = result.scalar_one_or_none()
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="注册码不存在"
        )
    
    await db.delete(code)
    await db.commit()
    
    return {"message": "注册码已删除"}
