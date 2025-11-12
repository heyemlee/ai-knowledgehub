"""
API Key 加密存储服务
使用 Fernet 对称加密保护敏感密钥
"""
import os
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)


class APIKeyManager:
    """API Key 加密管理服务"""
    
    def __init__(self, master_key: Optional[str] = None):
        """
        初始化 API Key 管理器
        
        Args:
            master_key: 主密钥（用于生成加密密钥）。如果为None，将从环境变量或生成新密钥
        """
        self.master_key = master_key or os.getenv("API_KEY_ENCRYPTION_KEY")
        
        # 检查是否在生产环境
        from app.core.config import settings
        
        if not self.master_key:
            if settings.MODE == "production":
                raise ValueError(
                    "生产环境必须设置 API_KEY_ENCRYPTION_KEY 环境变量。"
                    "不允许使用默认密钥。"
                )
            # 开发环境使用默认密钥（仅用于开发）
            logger.warning(
                "⚠️  安全警告：未找到 API_KEY_ENCRYPTION_KEY，将使用默认密钥（仅用于开发环境）。"
                "生产环境必须设置安全的主密钥。"
            )
            self.master_key = "default-development-key-change-in-production"
        
        # 生成加密密钥
        self.fernet = self._generate_fernet(self.master_key)
    
    def _generate_fernet(self, password: str) -> Fernet:
        """
        从密码生成 Fernet 密钥
        
        Args:
            password: 密码字符串
            
        Returns:
            Fernet 实例
        """
        # 使用固定的盐（在生产环境中应该存储在安全的地方）
        # 注意：生产环境应该从环境变量读取盐值
        salt_env = os.getenv("API_KEY_ENCRYPTION_SALT")
        if salt_env:
            salt = salt_env.encode()
        else:
            from app.core.config import settings
            if settings.MODE == "production":
                logger.warning(
                    "⚠️  生产环境建议设置 API_KEY_ENCRYPTION_SALT 环境变量以提高安全性"
                )
            salt = b'knowledgehub_salt_2024'  # 默认盐值（仅用于开发环境）
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def encrypt_key(self, api_key: str) -> str:
        """
        加密 API Key
        
        Args:
            api_key: 原始 API Key
            
        Returns:
            加密后的 API Key（Base64编码）
        """
        if not api_key:
            raise ValueError("API Key 不能为空")
        
        encrypted = self.fernet.encrypt(api_key.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_key(self, encrypted_key: str) -> str:
        """
        解密 API Key
        
        Args:
            encrypted_key: 加密后的 API Key（Base64编码）
            
        Returns:
            解密后的原始 API Key
        """
        if not encrypted_key:
            raise ValueError("加密的 API Key 不能为空")
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_key.encode())
            decrypted = self.fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"解密 API Key 失败: {e}")
            raise ValueError(f"解密失败: {str(e)}")
    
    def rotate_key(self, old_encrypted_key: str, new_api_key: str) -> str:
        """
        轮换 API Key
        
        Args:
            old_encrypted_key: 旧的加密 API Key
            new_api_key: 新的原始 API Key
            
        Returns:
            新的加密 API Key
        """
        # 验证旧密钥（可选）
        try:
            old_key = self.decrypt_key(old_encrypted_key)
            logger.info("旧 API Key 验证成功")
        except Exception as e:
            logger.warning(f"无法验证旧 API Key: {e}")
        
        # 加密新密钥
        return self.encrypt_key(new_api_key)


class APIKeyRotationService:
    """API Key 轮换服务"""
    
    def __init__(self, key_manager: APIKeyManager):
        """
        初始化轮换服务
        
        Args:
            key_manager: API Key 管理器实例
        """
        self.key_manager = key_manager
        self.rotation_history: Dict[str, datetime] = {}  # 轮换历史记录
    
    def should_rotate(self, key_name: str, max_age_days: int = 90) -> bool:
        """
        检查是否应该轮换密钥
        
        Args:
            key_name: 密钥名称
            max_age_days: 最大有效期（天）
            
        Returns:
            如果应该轮换返回 True
        """
        if key_name not in self.rotation_history:
            return False
        
        last_rotation = self.rotation_history[key_name]
        age = datetime.utcnow() - last_rotation
        
        return age.days >= max_age_days
    
    def record_rotation(self, key_name: str):
        """
        记录密钥轮换
        
        Args:
            key_name: 密钥名称
        """
        self.rotation_history[key_name] = datetime.utcnow()
        logger.info(f"记录密钥轮换: {key_name} at {datetime.utcnow()}")
    
    def rotate_key(self, key_name: str, old_encrypted_key: str, new_api_key: str) -> str:
        """
        执行密钥轮换
        
        Args:
            key_name: 密钥名称
            old_encrypted_key: 旧的加密密钥
            new_api_key: 新的原始 API Key
            
        Returns:
            新的加密 API Key
        """
        new_encrypted = self.key_manager.rotate_key(old_encrypted_key, new_api_key)
        self.record_rotation(key_name)
        logger.info(f"成功轮换密钥: {key_name}")
        return new_encrypted


# 全局实例
api_key_manager = APIKeyManager()
api_key_rotation_service = APIKeyRotationService(api_key_manager)

