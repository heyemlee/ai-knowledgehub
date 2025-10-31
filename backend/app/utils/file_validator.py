"""
文件验证工具
"""
from fastapi import HTTPException, UploadFile
from app.core.constants import FileValidationConfig
import os
import logging

logger = logging.getLogger(__name__)


def validate_file(file: UploadFile) -> tuple[str, int]:
    """
    验证上传的文件
    
    Args:
        file: FastAPI UploadFile 对象
        
    Returns:
        (filename, file_size) 元组
        
    Raises:
        HTTPException: 如果文件验证失败
    """
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="文件名不能为空"
        )
    
    filename = file.filename
    file_extension = os.path.splitext(filename)[1].lower()
    
    if file_extension not in FileValidationConfig.ALLOWED_EXTENSIONS:
        allowed_exts = ', '.join(FileValidationConfig.ALLOWED_EXTENSIONS)
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式。允许的格式: {allowed_exts}"
        )
    
    if file.content_type:
        content_type = file.content_type.lower()
        expected_mime = FileValidationConfig.EXTENSION_MIME_MAP.get(file_extension)
        
        if expected_mime and content_type != expected_mime.lower():
            logger.warning(
                f"文件扩展名 ({file_extension}) 与 MIME 类型 ({content_type}) 不匹配。"
                f"期望的 MIME 类型: {expected_mime}"
            )
    
    return filename, file_extension


def validate_file_size(file_size: int) -> None:
    """
    验证文件大小
    
    Args:
        file_size: 文件大小（字节）
        
    Raises:
        HTTPException: 如果文件超过大小限制
    """
    max_size = FileValidationConfig.MAX_FILE_SIZE
    max_size_mb = max_size / (1024 * 1024)
    
    if file_size > max_size:
        file_size_mb = file_size / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"文件大小 ({file_size_mb:.2f} MB) 超过限制 ({max_size_mb:.0f} MB)"
        )
    
    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="文件不能为空"
        )


