"""
问答 API 路由
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.models.schemas import ChatRequest, ChatResponse
from app.utils.auth import get_current_user
from app.services.openai_service import openai_service
from app.services.qdrant_service import qdrant_service
import logging
import uuid

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=ChatResponse)
async def ask_question(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    问答接口（RAG检索 + AI生成）
    
    Args:
        request: 问答请求
        current_user: 当前用户
        
    Returns:
        AI生成的回答
    """
    try:
        # 1. 生成问题向量
        question_embeddings = openai_service.generate_embeddings([request.question])
        question_embedding = question_embeddings[0]
        
        # 2. 向量检索相关文档
        relevant_docs = qdrant_service.search(
            query_embedding=question_embedding,
            limit=5,
            score_threshold=0.7
        )
        
        if not relevant_docs:
            return ChatResponse(
                answer="抱歉，知识库中没有找到相关信息。",
                sources=[],
                conversation_id=request.conversation_id or str(uuid.uuid4())
            )
        
        # 3. 调用 OpenAI 生成回答
        answer = openai_service.generate_answer(
            question=request.question,
            context=relevant_docs,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens or 1000
        )
        
        # 4. 返回结果
        return ChatResponse(
            answer=answer,
            sources=[
                {
                    "content": doc["content"][:200] + "...",
                    "metadata": doc["metadata"],
                    "score": doc["score"]
                }
                for doc in relevant_docs
            ],
            conversation_id=request.conversation_id or str(uuid.uuid4())
        )
    
    except Exception as e:
        logger.error(f"问答处理失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")


@router.post("/stream")
async def stream_answer(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    流式问答接口（实时返回）
    """
    try:
        # 1. 生成问题向量
        question_embeddings = openai_service.generate_embeddings([request.question])
        question_embedding = question_embeddings[0]
        
        # 2. 向量检索
        relevant_docs = qdrant_service.search(
            query_embedding=question_embedding,
            limit=5,
            score_threshold=0.7
        )
        
        if not relevant_docs:
            async def empty_response():
                yield "抱歉，知识库中没有找到相关信息。"
            return StreamingResponse(empty_response(), media_type="text/plain")
        
        # 3. 流式生成回答
        async def generate():
            async for chunk in openai_service.stream_answer(
                question=request.question,
                context=relevant_docs,
                temperature=request.temperature or 0.7,
                max_tokens=request.max_tokens or 1000
            ):
                yield chunk
        
        return StreamingResponse(generate(), media_type="text/event-stream")
    
    except Exception as e:
        logger.error(f"流式问答失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

