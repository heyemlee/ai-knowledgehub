import os
import uuid
from typing import BinaryIO, Optional
from pathlib import Path
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LocalStorageService:
    def __init__(self):
        self.storage_dir = Path(settings.LOCAL_STORAGE_PATH)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"本地存储目录初始化: {self.storage_dir}")

    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到本地存储
        
        Args:
            file_obj: 文件对象
            filename: 文件名
            content_type: 文件类型（可选）
            
        Returns:
            file_id: 生成的文件ID
        """
        try:
            file_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            file_path = self.storage_dir / storage_filename

            with open(file_path, 'wb') as f:
                f.write(file_obj.read())

            logger.info(f"文件上传成功: {storage_filename}")
            return file_id

        except Exception as e:
            logger.error(f"文件上传失败: {str(e)}")
            raise

    def download_file(self, file_id: str, original_filename: str) -> bytes:
        """
        从本地存储下载文件
        
        Args:
            file_id: 文件ID
            original_filename: 原始文件名（用于获取扩展名）
            
        Returns:
            文件内容（字节）
        """
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            file_path = self.storage_dir / storage_filename

            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {storage_filename}")

            with open(file_path, 'rb') as f:
                content = f.read()

            logger.info(f"文件下载成功: {storage_filename}")
            return content

        except Exception as e:
            logger.error(f"文件下载失败: {str(e)}")
            raise

    def delete_file(self, file_id: str, original_filename: str) -> bool:
        """
        从本地存储删除文件
        
        Args:
            file_id: 文件ID
            original_filename: 原始文件名（用于获取扩展名）
            
        Returns:
            是否删除成功
        """
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            file_path = self.storage_dir / storage_filename

            if file_path.exists():
                file_path.unlink()
                logger.info(f"文件删除成功: {storage_filename}")
                return True
            else:
                logger.warning(f"文件不存在，无需删除: {storage_filename}")
                return False

        except Exception as e:
            logger.error(f"文件删除失败: {str(e)}")
            raise

    def file_exists(self, file_id: str, original_filename: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_id: 文件ID
            original_filename: 原始文件名（用于获取扩展名）
            
        Returns:
            文件是否存在
        """
        file_extension = Path(original_filename).suffix
        storage_filename = f"{file_id}{file_extension}"
        file_path = self.storage_dir / storage_filename
        return file_path.exists()

    def get_file_size(self, file_id: str, original_filename: str) -> int:
        """
        获取文件大小
        
        Args:
            file_id: 文件ID
            original_filename: 原始文件名（用于获取扩展名）
            
        Returns:
            文件大小（字节）
        """
        file_extension = Path(original_filename).suffix
        storage_filename = f"{file_id}{file_extension}"
        file_path = self.storage_dir / storage_filename
        
        if file_path.exists():
            return file_path.stat().st_size
        return 0


storage_service = LocalStorageService()
