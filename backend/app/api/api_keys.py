"""
API Key 管理 API 路由
用于管理加密存储的 API Key 和轮换
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.auth import get_current_user
from app.db.database import get_db
from app.services.api_key_manager import api_key_manager, api_key_rotation_service
from app.core.config import settings
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()


class APIKeyRotationRequest(BaseModel):
    """API Key 轮换请求"""
    key_name: str
    new_api_key: str
    old_encrypted_key: Optional[str] = None


class APIKeyEncryptRequest(BaseModel):
    """API Key 加密请求"""
    api_key: str


class APIKeyDecryptRequest(BaseModel):
    """API Key 解密请求"""
    encrypted_key: str


@router.post("/encrypt")
async def encrypt_api_key(
    request_data: APIKeyEncryptRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    加密 API Key
    
    仅管理员可用（生产环境需要添加管理员权限检查）
    """
    if settings.MODE == "production":
        pass
    
    try:
        encrypted = api_key_manager.encrypt_key(request_data.api_key)
        return {
            "encrypted_key": encrypted,
            "message": "API Key 加密成功"
        }
    except Exception as e:
        logger.error(f"加密 API Key 失败: {e}")
        raise HTTPException(status_code=500, detail=f"加密失败: {str(e)}")


@router.post("/decrypt")
async def decrypt_api_key(
    request_data: APIKeyDecryptRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    解密 API Key
    
    仅管理员可用（生产环境需要添加管理员权限检查）
    """
    if settings.MODE == "production":
        pass
    
    try:
        decrypted = api_key_manager.decrypt_key(request_data.encrypted_key)
        return {
            "decrypted_key": decrypted,
            "message": "API Key 解密成功"
        }
    except Exception as e:
        logger.error(f"解密 API Key 失败: {e}")
        raise HTTPException(status_code=500, detail=f"解密失败: {str(e)}")


@router.post("/rotate")
async def rotate_api_key(
    request_data: APIKeyRotationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    轮换 API Key
    
    仅管理员可用（生产环境需要添加管理员权限检查）
    """
    if settings.MODE == "production":
        pass
    
    try:
        should_rotate = api_key_rotation_service.should_rotate(
            request_data.key_name,
            max_age_days=90
        )
        
        if not should_rotate and request_data.old_encrypted_key:
            logger.warning(f"密钥 {request_data.key_name} 未达到轮换期限，但强制轮换")
        
        new_encrypted = api_key_rotation_service.rotate_key(
            key_name=request_data.key_name,
            old_encrypted_key=request_data.old_encrypted_key or "",
            new_api_key=request_data.new_api_key
        )
        
        return {
            "encrypted_key": new_encrypted,
            "key_name": request_data.key_name,
            "message": "API Key 轮换成功"
        }
    except Exception as e:
        logger.error(f"轮换 API Key 失败: {e}")
        raise HTTPException(status_code=500, detail=f"轮换失败: {str(e)}")


@router.get("/rotation-status/{key_name}")
async def get_rotation_status(
    key_name: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取密钥轮换状态
    
    仅管理员可用（生产环境需要添加管理员权限检查）
    """
    if settings.MODE == "production":
        pass
    
    try:
        should_rotate = api_key_rotation_service.should_rotate(key_name, max_age_days=90)
        
        rotation_history = api_key_rotation_service.rotation_history.get(key_name)
        
        return {
            "key_name": key_name,
            "should_rotate": should_rotate,
            "last_rotation": rotation_history.isoformat() if rotation_history else None,
            "max_age_days": 90
        }
    except Exception as e:
        logger.error(f"获取轮换状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")




