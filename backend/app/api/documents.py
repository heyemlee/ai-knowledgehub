"""
文档管理 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from app.models.schemas import DocumentUpload, DocumentMetadata
from app.utils.auth import get_current_user
from app.services.s3_service import s3_service
from app.services.openai_service import openai_service
from app.services.qdrant_service import qdrant_service
from app.utils.document_parser import DocumentParser
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()
parser = DocumentParser()


@router.post("/upload", response_model=DocumentUpload)
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    上传文档并处理
    
    支持格式：PDF, DOCX, XLSX
    """
    try:
        # 1. 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 2. 上传到 S3
        from io import BytesIO
        file_obj = BytesIO(file_content)
        file_id = s3_service.upload_file(
            file_obj=file_obj,
            filename=file.filename,
            content_type=file.content_type
        )
        
        # 3. 解析文档
        texts = []
        if file.filename.endswith('.pdf'):
            texts = parser.parse_pdf(file_content)
        elif file.filename.endswith(('.docx', '.doc')):
            texts = parser.parse_docx(file_content)
        elif file.filename.endswith(('.xlsx', '.xls')):
            texts = parser.parse_excel(file_content)
        else:
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        # 4. 文本切块
        chunks = parser.chunk_text(texts, chunk_size=1000, overlap=200)
        
        # 5. 生成向量
        embeddings = openai_service.generate_embeddings(chunks)
        
        # 6. 构建元数据
        metadata_list = [
            {
                "file_id": file_id,
                "filename": file.filename,
                "file_type": file.content_type,
                "chunk_index": i,
                "upload_time": datetime.utcnow().isoformat()
            }
            for i in range(len(chunks))
        ]
        
        # 7. 存入向量数据库
        qdrant_service.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadata=metadata_list
        )
        
        logger.info(f"文档处理完成: {file_id}, 块数: {len(chunks)}")
        
        return DocumentUpload(
            file_id=file_id,
            filename=file.filename,
            file_size=file_size,
            upload_time=datetime.utcnow(),
            status="completed"
        )
    
    except Exception as e:
        logger.error(f"文档上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


@router.get("/list")
async def list_documents(
    current_user: dict = Depends(get_current_user)
):
    """
    获取文档列表（简化版）
    """
    # TODO: 实现文档列表查询
    return {"documents": []}


@router.delete("/{file_id}")
async def delete_document(
    file_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    删除文档
    """
    try:
        # 删除 S3 文件
        s3_service.delete_file(file_id)
        
        # 删除向量数据库中的文档
        qdrant_service.delete_documents(file_id)
        
        return {"message": "文档删除成功", "file_id": file_id}
    except Exception as e:
        logger.error(f"文档删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

