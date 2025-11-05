from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.schemas import ChatRequest
from app.utils.auth import get_current_user
from app.db.database import get_db
from app.db.models import Conversation, Message
from app.services.openai_service import openai_service
from app.services.qdrant_service import qdrant_service
from app.services.token_usage_service import token_usage_service
from app.middleware.rate_limit import limiter
from app.core.constants import RateLimitConfig, TokenLimitConfig, SearchConfig, ProcessingConfig
from app.core.config import settings
from typing import List
import logging
import uuid
import json

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/stream")
@limiter.limit(RateLimitConfig.CHAT_RATE_LIMIT)
async def stream_answer(
    request: Request,
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = current_user.get("user_id")
        
        if user_id:
            estimated_tokens = len(chat_request.question) // 4
            estimated_tokens += (chat_request.max_tokens or 1000)
            
            allowed, error_msg = await token_usage_service.check_token_limit(
                db, user_id, estimated_tokens
            )
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail=error_msg or TokenLimitConfig.TOKEN_LIMIT_EXCEEDED_MESSAGE
                )
        conversation_id_str = chat_request.conversation_id or str(uuid.uuid4())
        
        conversation = None
        if conversation_id_str and user_id:
            result = await db.execute(
                select(Conversation).where(Conversation.conversation_id == conversation_id_str)
            )
            conversation = result.scalar_one_or_none()
        
        if not conversation and user_id:
            conversation = Conversation(
                conversation_id=conversation_id_str,
                user_id=user_id,
                title=chat_request.question[:50] if chat_request.question else None
            )
            db.add(conversation)
            await db.flush()
        
        if user_id:
            user_message = Message(
                conversation_id=conversation.id if conversation else None,
                role="user",
                content=chat_request.question
            )
            db.add(user_message)
            await db.flush()
        
        embedding_token_usage_stream = None
        question_embeddings, embedding_token_usage_stream = openai_service.generate_embeddings([chat_request.question])
        question_embedding = question_embeddings[0]
        
        if user_id and embedding_token_usage_stream:
            await token_usage_service.record_usage(
                db=db,
                user_id=user_id,
                prompt_tokens=embedding_token_usage_stream.get('prompt_tokens', 0),
                completion_tokens=embedding_token_usage_stream.get('completion_tokens', 0),
                endpoint="chat/stream/embedding"
            )
        
        from app.core.constants import QdrantConfig, SearchConfig, ProcessingConfig, AIConfig
        
        relevant_docs = []
        try:
            question_length = len(chat_request.question.strip())
            if question_length <= 10:
                limit = 5
                score_threshold = 0.6
            elif question_length <= 50:
                limit = 8
                score_threshold = 0.55
            elif question_length <= SearchConfig.SHORT_QUERY_THRESHOLD:
                limit = SearchConfig.SHORT_QUERY_LIMIT
                score_threshold = SearchConfig.SHORT_QUERY_THRESHOLD_SCORE
            else:
                limit = SearchConfig.NORMAL_QUERY_LIMIT
                score_threshold = SearchConfig.NORMAL_QUERY_THRESHOLD_SCORE
            
            relevant_docs = qdrant_service.search(
                query_embedding=question_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_text=chat_request.question
            )
            
            if relevant_docs:
                relevant_docs = openai_service.optimize_context_for_speed(
                    documents=relevant_docs,
                    max_tokens=2500
            )
            
            if not relevant_docs:
                relevant_docs = qdrant_service.search(
                    query_embedding=question_embedding,
                    limit=SearchConfig.FALLBACK_LIMIT,
                    score_threshold=SearchConfig.FALLBACK_THRESHOLD_SCORE,
                    query_text=chat_request.question
                )
                if relevant_docs:
                    relevant_docs = openai_service.optimize_context_for_speed(
                        documents=relevant_docs,
                        max_tokens=2500
                )
        except Exception as e:
            logger.warning(f"向量检索失败: {e}")
        
        full_answer = ""
        sources = []
        token_usage = None
        
        async def generate():
            nonlocal full_answer, token_usage
            
            if not relevant_docs:
                # 根据用户语言返回对应提示
                if chat_request.locale == 'en-US':
                    error_msg = "Sorry, no relevant information found in the knowledge base. Please upload relevant documents first."
                else:
                    error_msg = "抱歉，知识库中没有找到相关信息。请先上传相关文档到知识库。"
                full_answer = error_msg
                yield f"data: {json.dumps({'content': error_msg, 'done': True}, ensure_ascii=False)}\n\n"
                return
            
            try:
                stream_gen = openai_service.stream_answer(
                    question=chat_request.question,
                    context=relevant_docs,
                    temperature=chat_request.temperature or AIConfig.DEFAULT_TEMPERATURE,
                    max_tokens=chat_request.max_tokens or AIConfig.DEFAULT_MAX_TOKENS
                )
                
                async for chunk_data in stream_gen:
                    chunk_content, chunk_token_usage = chunk_data
                    if chunk_content is not None:
                        full_answer += chunk_content
                        yield f"data: {json.dumps({'content': chunk_content, 'done': False}, ensure_ascii=False)}\n\n"
                    elif chunk_token_usage is not None:
                        token_usage = chunk_token_usage
                
                if token_usage is None:
                    estimated_prompt = len(chat_request.question + str(relevant_docs)) // 3
                    estimated_completion = len(full_answer) // 3
                    token_usage = {
                        'prompt_tokens': estimated_prompt,
                        'completion_tokens': estimated_completion,
                        'total_tokens': estimated_prompt + estimated_completion
                    }
                
            except Exception as e:
                logger.error(f"流式生成失败: {e}", exc_info=True)
                error_msg = f"生成回答时出错: {str(e)}"
                full_answer = error_msg
                yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True}, ensure_ascii=False)}\n\n"
                return
            
            seen_filenames = set()
            for doc in relevant_docs[:ProcessingConfig.MAX_CONTEXT_DOCS]:
                metadata = doc.get("metadata", {})
                filename = metadata.get("filename", "未知文档")
                
                if filename not in seen_filenames and len(sources) < 2:
                    seen_filenames.add(filename)
                    sources.append({
                        "content": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"],
                        "metadata": metadata
                    })
            
            yield f"data: {json.dumps({'content': '', 'done': True, 'sources': sources, 'conversation_id': conversation_id_str}, ensure_ascii=False)}\n\n"
            
            if user_id and conversation and full_answer:
                try:
                    assistant_message = Message(
                        conversation_id=conversation.id,
                        role="assistant",
                        content=full_answer,
                        sources=json.dumps(sources, ensure_ascii=False) if sources else None
                    )
                    db.add(assistant_message)
                    
                    if not conversation.title and chat_request.question:
                        conversation.title = chat_request.question[:50]
                    
                    await db.commit()
                    
                    if token_usage:
                        await token_usage_service.record_usage(
                            db=db,
                            user_id=user_id,
                            prompt_tokens=token_usage.get('prompt_tokens', 0),
                            completion_tokens=token_usage.get('completion_tokens', 0),
                            endpoint="chat/stream"
                        )
                except Exception as e:
                    logger.error(f"保存流式响应到数据库失败: {e}", exc_info=True)
                    await db.rollback()
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    except Exception as e:
        logger.error(f"流式问答失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

