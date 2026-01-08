"""
批量图片上传 API - 支持 ZIP + CSV 批量上传
"""
import zipfile
import csv
import io
import os
import tempfile
import uuid
import logging
from typing import Optional, Dict, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Image, ImageTag
from app.api.auth import get_current_admin_user
from app.services.image_storage_service import storage_service
from app.middleware.rate_limit import limiter
from app.models.schemas import BatchUploadResponse, BatchUploadResult
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

router = APIRouter()

# 配置
MAX_ZIP_SIZE = 100 * 1024 * 1024  # 100MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB per image
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_IMAGE_MIMETYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp'
}


def parse_csv_metadata(csv_content: str) -> Dict[str, str]:
    """
    解析 CSV 元数据文件
    
    CSV 格式:
    filename,description
    image1.jpg,这是第一张图片的描述
    image2.png,这是第二张图片的描述
    
    Returns:
        Dict[str, str]: {filename: description}
    """
    metadata = {}
    
    try:
        # 尝试检测编码
        for encoding in ['utf-8', 'utf-8-sig', 'gbk', 'gb2312']:
            try:
                if isinstance(csv_content, bytes):
                    content = csv_content.decode(encoding)
                else:
                    content = csv_content
                break
            except UnicodeDecodeError:
                continue
        else:
            content = csv_content.decode('utf-8', errors='ignore') if isinstance(csv_content, bytes) else csv_content
        
        reader = csv.DictReader(io.StringIO(content))
        
        # 检查必要的列
        if reader.fieldnames is None:
            logger.warning("CSV 文件为空或格式错误")
            return metadata
        
        # 支持多种列名格式
        filename_col = None
        description_col = None
        
        for col in reader.fieldnames:
            col_lower = col.lower().strip()
            if col_lower in ['filename', 'file_name', 'file', '文件名', '文件']:
                filename_col = col
            elif col_lower in ['description', 'desc', '描述', '说明']:
                description_col = col
        
        if not filename_col:
            logger.warning(f"CSV 缺少 filename 列，可用列: {reader.fieldnames}")
            return metadata
        
        if not description_col:
            logger.warning(f"CSV 缺少 description 列，可用列: {reader.fieldnames}")
            return metadata
        
        for row in reader:
            filename = row.get(filename_col, '').strip()
            description = row.get(description_col, '').strip()
            
            if filename:
                metadata[filename] = description
                logger.debug(f"解析元数据: {filename} -> {description[:50]}...")
        
        logger.info(f"成功解析 {len(metadata)} 条元数据")
        
    except Exception as e:
        logger.error(f"解析 CSV 失败: {e}", exc_info=True)
    
    return metadata


def generate_description_from_filename(filename: str) -> str:
    """
    从文件名生成描述（备用方案）
    
    示例:
    - "产品A-红色款.jpg" -> "产品A 红色款"
    - "warehouse_plywood_stack.png" -> "warehouse plywood stack"
    """
    # 去掉扩展名
    name = Path(filename).stem
    
    # 替换分隔符为空格
    name = name.replace('-', ' ').replace('_', ' ')
    
    # 清理多余空格
    name = ' '.join(name.split())
    
    return name if name else filename


def create_thumbnail(image_data: bytes, max_size: tuple = (400, 400)) -> Optional[bytes]:
    """创建缩略图"""
    try:
        img = PILImage.open(io.BytesIO(image_data))
        original_width, original_height = img.size
        
        # 如果原图足够小，不生成缩略图
        file_size_kb = len(image_data) / 1024
        if (original_width <= max_size[0] and original_height <= max_size[1]) or file_size_kb < 100:
            return None
        
        # 生成缩略图
        img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
        
        output = io.BytesIO()
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(output, format='JPEG', quality=85)
        
        return output.getvalue()
    except Exception as e:
        logger.warning(f"创建缩略图失败: {e}")
        return None


@router.post("/batch", response_model=BatchUploadResponse)
@limiter.limit("5/minute")
async def batch_upload_images(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    批量上传图片（ZIP + CSV）
    
    上传一个 ZIP 文件，包含:
    - images.csv (可选): 元数据文件，格式为 filename,description
    - 图片文件: jpg, jpeg, png, gif, webp
    
    如果图片不在 CSV 中，将使用文件名作为描述。
    """
    results: List[BatchUploadResult] = []
    
    try:
        # 1. 验证文件类型
        if not file.filename or not file.filename.lower().endswith('.zip'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请上传 ZIP 文件"
            )
        
        # 2. 读取 ZIP 内容
        zip_content = await file.read()
        
        if len(zip_content) > MAX_ZIP_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ZIP 文件大小不能超过 {MAX_ZIP_SIZE // 1024 // 1024}MB"
            )
        
        # 3. 解析 ZIP
        try:
            zip_buffer = io.BytesIO(zip_content)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                # 检查是否有损坏
                bad_file = zip_file.testzip()
                if bad_file:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"ZIP 文件损坏: {bad_file}"
                    )
                
                # 4. 读取 CSV 元数据（如果存在）
                metadata: Dict[str, str] = {}
                csv_files = [n for n in zip_file.namelist() if n.lower().endswith('.csv')]
                
                if csv_files:
                    csv_filename = csv_files[0]  # 使用第一个 CSV 文件
                    logger.info(f"找到 CSV 元数据文件: {csv_filename}")
                    csv_content = zip_file.read(csv_filename)
                    metadata = parse_csv_metadata(csv_content)
                else:
                    logger.info("未找到 CSV 元数据文件，将使用文件名作为描述")
                
                # 5. 处理所有图片文件
                user_id = current_user.get("user_id")
                
                for item in zip_file.namelist():
                    # 跳过目录和非图片文件
                    if item.endswith('/') or item.startswith('__MACOSX'):
                        continue
                    
                    # 获取纯文件名（用于 CSV 匹配）
                    pure_filename = os.path.basename(item)
                    file_ext = Path(pure_filename).suffix.lower()
                    
                    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
                        logger.debug(f"跳过非图片文件: {item}")
                        continue
                    
                    try:
                        # 读取图片内容
                        image_data = zip_file.read(item)
                        
                        if len(image_data) > MAX_IMAGE_SIZE:
                            results.append(BatchUploadResult(
                                filename=pure_filename,
                                success=False,
                                error=f"图片大小超过 {MAX_IMAGE_SIZE // 1024 // 1024}MB"
                            ))
                            continue
                        
                        # 获取描述
                        description = metadata.get(pure_filename)
                        if not description:
                            description = generate_description_from_filename(pure_filename)
                            logger.info(f"使用文件名生成描述: {pure_filename} -> {description}")
                        
                        # 生成文件 ID
                        file_id = str(uuid.uuid4())
                        stored_filename = f"{file_id}{file_ext}"
                        mime_type = ALLOWED_IMAGE_MIMETYPES.get(file_ext, 'image/jpeg')
                        
                        # 保存原图
                        storage_path = await storage_service.save_file(
                            image_data,
                            stored_filename,
                            mime_type
                        )
                        
                        # 创建缩略图（可选）
                        thumbnail_path = None
                        thumbnail_data = create_thumbnail(image_data)
                        if thumbnail_data:
                            thumbnail_filename = f"{file_id}_thumb.jpg"
                            thumbnail_path = await storage_service.save_file(
                                thumbnail_data,
                                thumbnail_filename,
                                "image/jpeg"
                            )
                        
                        # 创建数据库记录
                        new_image = Image(
                            file_id=file_id,
                            filename=stored_filename,
                            original_filename=pure_filename,
                            file_size=len(image_data),
                            mime_type=mime_type,
                            storage_path=storage_path,
                            thumbnail_path=thumbnail_path,
                            description=description,
                            alt_text=description[:500] if description else None,
                            user_id=user_id
                        )
                        
                        db.add(new_image)
                        await db.flush()
                        
                        results.append(BatchUploadResult(
                            filename=pure_filename,
                            success=True,
                            image_id=new_image.id
                        ))
                        
                        logger.info(f"成功处理图片: {pure_filename}, ID: {new_image.id}")
                        
                    except Exception as e:
                        logger.error(f"处理图片失败 {item}: {e}")
                        results.append(BatchUploadResult(
                            filename=pure_filename,
                            success=False,
                            error=str(e)
                        ))
                
                # 提交所有更改
                await db.commit()
                
        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的 ZIP 文件"
            )
        
        # 6. 统计结果
        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        
        logger.info(f"批量上传完成: 总数 {len(results)}, 成功 {success_count}, 失败 {failed_count}")
        
        return BatchUploadResponse(
            total=len(results),
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"批量上传失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量上传失败: {str(e)}"
        )


@router.get("/batch/template")
async def download_csv_template():
    """
    下载 CSV 模板文件
    """
    template_content = """filename,description
example1.jpg,这是第一张图片的描述，包含关键词方便搜索匹配
example2.png,这是第二张图片的描述
example3.webp,产品A展示图，18mm厚度胶合板正面图
"""
    
    return Response(
        content=template_content.encode('utf-8-sig'),  # 使用 BOM 确保 Excel 正确显示中文
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=images_template.csv"
        }
    )
