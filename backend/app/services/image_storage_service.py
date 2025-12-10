"""
图片存储服务 - 适配器
为图片管理提供统一的存储接口，支持 S3 和本地存储
"""
import io
from typing import Optional
from pathlib import Path
from app.services.local_storage_service import storage_service as base_storage_service, S3StorageService, LocalStorageService
import logging

logger = logging.getLogger(__name__)


class ImageStorageService:
    """图片存储服务适配器 - 支持 S3 和本地存储"""
    
    def __init__(self):
        self.base_service = base_storage_service
        self.is_s3 = isinstance(self.base_service, S3StorageService)
        logger.info(f"图片存储服务初始化完成 (类型: {'S3' if self.is_s3 else 'Local'})")
    
    async def save_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        保存文件
        
        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            content_type: MIME 类型
            
        Returns:
            存储路径
        """
        try:
            # 将字节内容转换为 BinaryIO
            file_obj = io.BytesIO(file_content)
            
            # 调用底层存储服务的 upload_file 方法
            file_id = self.base_service.upload_file(
                file_obj,
                filename,
                content_type
            )
            
            # 返回存储路径（使用文件名作为路径）
            file_extension = Path(filename).suffix
            storage_path = f"{file_id}{file_extension}"
            
            logger.info(f"文件保存成功: {storage_path}")
            return storage_path
            
        except Exception as e:
            logger.error(f"文件保存失败: {e}", exc_info=True)
            raise
    
    async def get_file(self, storage_path: str) -> Optional[bytes]:
        """
        获取文件内容
        
        Args:
            storage_path: 存储路径
            
        Returns:
            文件内容（字节）
        """
        try:
            # 从存储路径提取 file_id
            file_id = Path(storage_path).stem
            original_filename = storage_path
            
            # 调用底层存储服务的 download_file 方法
            content = self.base_service.download_file(file_id, original_filename)
            
            logger.info(f"文件获取成功: {storage_path}")
            return content
            
        except FileNotFoundError:
            logger.warning(f"文件不存在: {storage_path}")
            return None
        except Exception as e:
            logger.error(f"文件获取失败: {e}", exc_info=True)
            raise
    
    async def delete_file(self, storage_path: str) -> bool:
        """
        删除文件
        
        Args:
            storage_path: 存储路径
            
        Returns:
            是否删除成功
        """
        try:
            # 从存储路径提取 file_id
            file_id = Path(storage_path).stem
            original_filename = storage_path
            
            # 调用底层存储服务的 delete_file 方法
            result = self.base_service.delete_file(file_id, original_filename)
            
            logger.info(f"文件删除成功: {storage_path}")
            return result
            
        except Exception as e:
            logger.error(f"文件删除失败: {e}", exc_info=True)
            return False
    
    async def file_exists(self, storage_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            storage_path: 存储路径
            
        Returns:
            文件是否存在
        """
        try:
            file_id = Path(storage_path).stem
            original_filename = storage_path
            
            return self.base_service.file_exists(file_id, original_filename)
            
        except Exception as e:
            logger.error(f"检查文件存在性失败: {e}", exc_info=True)
            return False


# 全局实例
storage_service = ImageStorageService()
