"""
AWS S3 服务封装
"""
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
from typing import BinaryIO, Optional
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class S3Service:
    """AWS S3 服务"""
    
    def __init__(self):
        self._s3_client = None
        self.bucket_name = settings.S3_BUCKET_NAME
    
    @property
    def s3_client(self):
        """懒加载 S3 客户端"""
        if self._s3_client is None:
            if not settings.AWS_ACCESS_KEY_ID or not settings.AWS_SECRET_ACCESS_KEY:
                raise ValueError(
                    "AWS 配置未设置。请在 .env 文件中配置 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY"
                )
            self._s3_client = boto3.client(
                's3',
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        return self._s3_client
    
    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        上传文件到 S3
        
        Args:
            file_obj: 文件对象
            filename: 文件名
            content_type: 文件类型
            
        Returns:
            文件ID（S3 key）
        """
        try:
            file_id = str(uuid.uuid4())
            s3_key = f"documents/{file_id}/{filename}"
            
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"文件上传成功: {s3_key}")
            return file_id
        except ClientError as e:
            logger.error(f"S3 上传失败: {e}")
            raise
    
    def download_file(self, file_id: str, filename: str) -> bytes:
        """
        从 S3 下载文件
        
        Args:
            file_id: 文件ID
            filename: 文件名（用于构建 S3 key）
            
        Returns:
            文件内容（字节）
        """
        try:
            s3_key = f"documents/{file_id}/{filename}"
            
            from io import BytesIO
            file_obj = BytesIO()
            
            self.s3_client.download_fileobj(
                self.bucket_name,
                s3_key,
                file_obj
            )
            
            file_obj.seek(0)
            file_content = file_obj.read()
            
            logger.info(f"文件下载成功: {s3_key}, 大小: {len(file_content)} 字节")
            return file_content
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.error(f"S3 文件不存在: {s3_key}")
                raise ValueError(f"文件不存在: {filename}")
            logger.error(f"S3 下载失败: {e}")
            raise
    
    def delete_file(self, file_id: str, filename: str):
        """
        删除 S3 文件
        
        Args:
            file_id: 文件ID
            filename: 文件名（用于构建 S3 key）
        """
        try:
            s3_key = f"documents/{file_id}/{filename}"
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            logger.info(f"文件删除成功: {s3_key}")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchKey':
                logger.warning(f"S3 文件不存在，跳过删除: {s3_key}")
                return
            logger.error(f"S3 删除失败: {e}")
            raise


# 全局实例
s3_service = S3Service()

