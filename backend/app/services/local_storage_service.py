import os
import uuid
from typing import BinaryIO, Optional
from pathlib import Path
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


import os
import uuid
from typing import BinaryIO, Optional
from pathlib import Path
from app.core.config import settings
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BaseStorageService:
    def upload_file(self, file_obj: BinaryIO, filename: str, content_type: Optional[str] = None) -> str:
        raise NotImplementedError

    def download_file(self, file_id: str, original_filename: str) -> bytes:
        raise NotImplementedError

    def delete_file(self, file_id: str, original_filename: str) -> bool:
        raise NotImplementedError

    def file_exists(self, file_id: str, original_filename: str) -> bool:
        raise NotImplementedError

    def get_file_size(self, file_id: str, original_filename: str) -> int:
        raise NotImplementedError


class LocalStorageService(BaseStorageService):
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
        try:
            file_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            file_path = self.storage_dir / storage_filename

            with open(file_path, 'wb') as f:
                f.write(file_obj.read())

            logger.info(f"文件上传成功(Local): {storage_filename}")
            return file_id

        except Exception as e:
            logger.error(f"文件上传失败(Local): {str(e)}")
            raise

    def download_file(self, file_id: str, original_filename: str) -> bytes:
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            file_path = self.storage_dir / storage_filename

            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {storage_filename}")

            with open(file_path, 'rb') as f:
                content = f.read()

            logger.info(f"文件下载成功(Local): {storage_filename}")
            return content

        except Exception as e:
            logger.error(f"文件下载失败(Local): {str(e)}")
            raise

    def delete_file(self, file_id: str, original_filename: str) -> bool:
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            file_path = self.storage_dir / storage_filename

            if file_path.exists():
                file_path.unlink()
                logger.info(f"文件删除成功(Local): {storage_filename}")
                return True
            else:
                logger.warning(f"文件不存在，无需删除(Local): {storage_filename}")
                return False

        except Exception as e:
            logger.error(f"文件删除失败(Local): {str(e)}")
            raise

    def file_exists(self, file_id: str, original_filename: str) -> bool:
        file_extension = Path(original_filename).suffix
        storage_filename = f"{file_id}{file_extension}"
        file_path = self.storage_dir / storage_filename
        return file_path.exists()

    def get_file_size(self, file_id: str, original_filename: str) -> int:
        file_extension = Path(original_filename).suffix
        storage_filename = f"{file_id}{file_extension}"
        file_path = self.storage_dir / storage_filename
        
        if file_path.exists():
            return file_path.stat().st_size
        return 0


class S3StorageService(BaseStorageService):
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.AWS_REGION
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME 未配置")
            
        # 如果配置了 AK/SK，则使用显式凭证
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
            logger.info("使用显式 AK/SK 初始化 S3 客户端")
        else:
            # 否则使用默认凭证链（支持 ECS Task Role / IAM Role）
            self.s3_client = boto3.client(
                's3',
                region_name=self.region
            )
            logger.info("使用默认凭证链(IAM Role) 初始化 S3 客户端")
            
        logger.info(f"S3 存储服务初始化: bucket={self.bucket_name}, region={self.region}")

    def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: Optional[str] = None
    ) -> str:
        try:
            file_id = str(uuid.uuid4())
            file_extension = Path(filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type

            # 重置文件指针
            file_obj.seek(0)
            
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                storage_filename,
                ExtraArgs=extra_args
            )

            logger.info(f"文件上传成功(S3): {storage_filename}")
            return file_id

        except Exception as e:
            logger.error(f"文件上传失败(S3): {str(e)}")
            raise

    def download_file(self, file_id: str, original_filename: str) -> bytes:
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=storage_filename
            )
            
            content = response['Body'].read()
            logger.info(f"文件下载成功(S3): {storage_filename}")
            return content

        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"文件不存在(S3): {storage_filename}")
        except Exception as e:
            logger.error(f"文件下载失败(S3): {str(e)}")
            raise

    def delete_file(self, file_id: str, original_filename: str) -> bool:
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=storage_filename
            )
            
            logger.info(f"文件删除成功(S3): {storage_filename}")
            return True

        except Exception as e:
            logger.error(f"文件删除失败(S3): {str(e)}")
            raise

    def file_exists(self, file_id: str, original_filename: str) -> bool:
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=storage_filename
            )
            return True
        except ClientError:
            return False

    def get_file_size(self, file_id: str, original_filename: str) -> int:
        try:
            file_extension = Path(original_filename).suffix
            storage_filename = f"{file_id}{file_extension}"
            
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=storage_filename
            )
            return response['ContentLength']
        except Exception:
            return 0


# 工厂方法
def get_storage_service() -> BaseStorageService:
    if settings.STORAGE_TYPE == "s3":
        return S3StorageService()
    return LocalStorageService()

# 全局实例
storage_service = get_storage_service()

