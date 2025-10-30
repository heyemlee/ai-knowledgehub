"""
OpenAI 服务封装
"""
from openai import OpenAI
from app.core.config import settings
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI API 服务"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本向量嵌入
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            raise
    
    def generate_answer(
        self,
        question: str,
        context: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """
        基于上下文生成回答
        
        Args:
            question: 用户问题
            context: 检索到的上下文文档列表，每个包含 content 和 metadata
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            AI生成的回答
        """
        # 构建上下文
        context_text = "\n\n".join([
            f"文档片段 {i+1}:\n{ctx['content']}"
            for i, ctx in enumerate(context)
        ])
        
        system_prompt = """你是一个专业的企业知识库助手。请根据提供的文档内容回答用户的问题。
如果文档中没有相关信息，请诚实告知用户。
回答要准确、专业、简洁。"""
        
        user_prompt = f"""基于以下文档内容回答问题：

{context_text}

问题：{question}

请提供详细的回答："""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            raise
    
    async def stream_answer(
        self,
        question: str,
        context: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ):
        """
        流式生成回答（用于实时显示）
        
        Args:
            question: 用户问题
            context: 检索到的上下文
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            回答文本片段
        """
        context_text = "\n\n".join([
            f"文档片段 {i+1}:\n{ctx['content']}"
            for i, ctx in enumerate(context)
        ])
        
        system_prompt = """你是一个专业的企业知识库助手。请根据提供的文档内容回答用户的问题。
如果文档中没有相关信息，请诚实告知用户。
回答要准确、专业、简洁。"""
        
        user_prompt = f"""基于以下文档内容回答问题：

{context_text}

问题：{question}

请提供详细的回答："""
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"流式生成回答失败: {e}")
            raise


# 全局实例
openai_service = OpenAIService()

