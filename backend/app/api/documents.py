"""
文档管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.schemas import DocumentUpload, DocumentMetadata
from app.utils.auth import get_current_user
from app.db.database import get_db
from app.db.models import Document, User
from app.services.local_storage_service import storage_service
from app.services.openai_service import openai_service
from app.services.qdrant_service import qdrant_service
from app.services.token_usage_service import token_usage_service
from app.utils.document_parser import DocumentParser
from app.utils.file_validator import validate_file, validate_file_size
from app.utils.sanitizer import InputSanitizer
from app.middleware.rate_limit import limiter
from app.core.constants import RateLimitConfig
from app.core.config import settings
from typing import List
from datetime import datetime
from io import BytesIO
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()
parser = DocumentParser()


@router.post("/upload", response_model=DocumentUpload)
@limiter.limit(RateLimitConfig.UPLOAD_RATE_LIMIT)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """上传文档并处理（支持 PDF, DOCX, XLSX, TXT，最大 50MB）"""
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        filename, file_extension = validate_file(file)
        
        try:
            filename = InputSanitizer.sanitize_filename(filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"文件名验证失败: {str(e)}")
        
        file_content = await file.read()
        file_size = len(file_content)
        
        validate_file_size(file_size)
        
        from io import BytesIO
        file_obj = BytesIO(file_content)
        file_id = storage_service.upload_file(
            file_obj=file_obj,
            filename=filename,
            content_type=file.content_type
        )
        
        texts = []
        if file_extension == '.pdf':
            texts = parser.parse_pdf(file_content)
        elif file_extension in ['.docx', '.doc']:
            texts = parser.parse_docx(file_content)
        elif file_extension in ['.xlsx', '.xls']:
            texts = parser.parse_excel(file_content)
        elif file_extension == '.txt':
            texts = parser.parse_text(file_content)
        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {file_extension}")
        
        from app.core.constants import DocumentParserConfig
        chunks = parser.chunk_text(
            texts, 
            chunk_size=DocumentParserConfig.DEFAULT_CHUNK_SIZE, 
            overlap=DocumentParserConfig.DEFAULT_OVERLAP
        )
        
        embeddings, embedding_token_usage = openai_service.generate_embeddings(chunks)
        
        if user_id and embedding_token_usage:
            await token_usage_service.record_usage(
                db=db,
                user_id=user_id,
                prompt_tokens=embedding_token_usage.get('prompt_tokens', 0),
                completion_tokens=embedding_token_usage.get('completion_tokens', 0),
                endpoint="documents/upload/embedding"
            )
        
        metadata_list = [
            {
                "file_id": file_id,
                "filename": filename,
                "file_type": file.content_type,
                "file_size": file_size,
                "chunk_index": i,
                "upload_time": datetime.utcnow().isoformat()
            }
            for i in range(len(chunks))
        ]
        
        qdrant_service.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadata=metadata_list
        )
        
        db_document = Document(
            file_id=file_id,
            filename=filename,
            file_type=file.content_type,
            file_size=file_size,
            user_id=user_id,
            status="completed",
            chunks_count=len(chunks)
        )
        
        db.add(db_document)
        await db.commit()
        await db.refresh(db_document)
        
        logger.info(f"文档处理完成: {file_id}, 块数: {len(chunks)}")
        
        return DocumentUpload(
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            upload_time=db_document.created_at,
            status="completed"
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"文档解析失败: {e}")
        raise HTTPException(status_code=400, detail=f"文档解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"文档上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.get("/list", response_model=List[DocumentMetadata])
@limiter.limit(RateLimitConfig.DOCUMENT_RATE_LIMIT)
async def list_documents(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取文档列表
    """
    try:
        user_id = current_user.get("user_id")
        
        result = await db.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        documents = result.scalars().all()
        
        result_list = [
            DocumentMetadata(
                file_id=doc.file_id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                upload_time=doc.created_at,
                chunks_count=doc.chunks_count,
                status=doc.status
            )
            for doc in documents
        ]
        
        logger.info(f"返回 {len(result_list)} 个文档")
        return result_list
        
    except Exception as e:
        logger.error(f"获取文档列表失败: {e}", exc_info=True)
        if settings.MODE == "development":
            logger.warning("获取文档列表失败，返回空列表")
            return []
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/{file_id}/preview")
async def preview_document(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    预览文档
    
    支持的文件类型：
    - PDF: 返回 PDF 文件的二进制流
    - TXT: 返回文本内容
    - 其他: 返回文件下载
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        if not file_id or len(file_id) > 255:
            raise HTTPException(status_code=400, detail="无效的文件ID")
        
        result = await db.execute(
            select(Document).where(
                Document.file_id == file_id,
                Document.user_id == user_id
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        try:
            file_content = storage_service.download_file(file_id, document.filename)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        
        file_extension = document.filename.split('.')[-1].lower() if '.' in document.filename else ''
        
        if file_extension == 'pdf':
            return Response(
                content=file_content,
                media_type='application/pdf',
                headers={
                    'Content-Disposition': f'inline; filename="{document.filename}"',
                    'Cache-Control': 'public, max-age=3600'
                }
            )
        elif file_extension == 'txt':
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = file_content.decode('gbk')
                except:
                    text_content = file_content.decode('utf-8', errors='ignore')
            
            return Response(
                content=text_content,
                media_type='text/plain; charset=utf-8',
                headers={
                    'Content-Disposition': f'inline; filename="{document.filename}"'
                }
            )
        else:
            return Response(
                content=file_content,
                media_type=document.file_type or 'application/octet-stream',
                headers={
                    'Content-Disposition': f'attachment; filename="{document.filename}"'
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"预览文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"预览文档失败: {str(e)}")


@router.get("/{file_id}/download")
async def download_document(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    下载文档
    """
    try:
        user_id = current_user.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="无法获取用户ID")
        
        if not file_id or len(file_id) > 255:
            raise HTTPException(status_code=400, detail="无效的文件ID")
        
        result = await db.execute(
            select(Document).where(
                Document.file_id == file_id,
                Document.user_id == user_id
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        try:
            file_content = storage_service.download_file(file_id, document.filename)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        
        return Response(
            content=file_content,
            media_type=document.file_type or 'application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{document.filename}"'
            }
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载文档失败: {str(e)}")


@router.delete("/{file_id}")
async def delete_document(
    file_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除文档
    """
    try:
        user_id = current_user.get("user_id")
        
        result = await db.execute(
            select(Document).where(
                Document.file_id == file_id,
                Document.user_id == user_id
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        storage_service.delete_file(file_id, document.filename)
        qdrant_service.delete_documents(file_id)
        
        db.delete(document)
        await db.commit()
        
        return {"message": "文档删除成功", "file_id": file_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

