"""
OpenAI 服务封装
"""
from openai import OpenAI
from app.core.config import settings
from app.core.constants import AIConfig, CacheConfig
from app.services.prompts import Prompts
from app.services.cache_service import cache_service
from app.utils.retry import openai_retry
from app.utils.language_detector import detect_language
from typing import List, Dict, Tuple, Optional, Literal
import logging

logger = logging.getLogger(__name__)


class OpenAIService:
    """OpenAI API 服务"""
    
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            if settings.MODE == "production":
                raise ValueError(
                    "生产环境必须设置 OPENAI_API_KEY 环境变量。"
                    "不允许使用占位符密钥。"
                )
            logger.warning(
                "⚠️  安全警告：OpenAI API Key 未配置，使用占位符（仅用于开发环境）。"
                "生产环境必须设置有效的 API Key。"
            )
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY or "dummy-key")
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
    
    @openai_retry
    def _generate_embeddings_internal(self, texts: List[str]):
        """
        内部方法：调用 OpenAI API 生成嵌入向量（带重试）
        """
        # text-embedding-3-large 默认生成 3072 维向量
        # 如果 Qdrant 集合是 1536 维，需要使用 text-embedding-3-small 或重新创建集合为 3072 维
        return self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
    
    def generate_embeddings(self, texts: List[str]) -> Tuple[List[List[float]], Optional[Dict]]:
        """
        生成文本向量嵌入（带缓存）
        
        Args:
            texts: 文本列表
            
        Returns:
            (向量列表, token使用量字典) 元组
        """
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API Key 未配置。请在 .env 文件中设置 OPENAI_API_KEY")
        
        if not CacheConfig.ENABLE_CACHE:
            return self._generate_embeddings_without_cache(texts)
        
        cached_results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            cache_key = cache_service.cache_key(
                CacheConfig.EMBEDDING_CACHE_PREFIX,
                text,
                model=self.embedding_model
            )
            cached_result = cache_service.get(cache_key)
            if cached_result is not None:
                cached_results.append((i, cached_result))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        new_embeddings = []
        new_token_usage = None
        if uncached_texts:
            try:
                response = self._generate_embeddings_internal(uncached_texts)
                
                new_embeddings = [item.embedding for item in response.data]
                
                if new_embeddings:
                    actual_dim = len(new_embeddings[0])
                    logger.info(f"生成的向量维度: {actual_dim}")
                
                if hasattr(response, 'usage') and response.usage:
                    new_token_usage = {
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': 0,  # embedding API 没有 completion tokens
                        'total_tokens': response.usage.total_tokens
                    }
                
                for text, embedding in zip(uncached_texts, new_embeddings):
                    cache_key = cache_service.cache_key(
                        CacheConfig.EMBEDDING_CACHE_PREFIX,
                        text,
                        model=self.embedding_model
                    )
                    cache_service.set(
                        cache_key,
                        embedding,
                        ttl=CacheConfig.EMBEDDING_CACHE_TTL
                    )
                
                logger.debug(f"缓存了 {len(new_embeddings)} 个新的embeddings，命中 {len(cached_results)} 个缓存")
            except Exception as e:
                error_msg = str(e)
                if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                    raise ValueError(f"OpenAI API 认证失败: {error_msg}。请检查 API Key 是否正确。")
                logger.error(f"生成嵌入向量失败: {e}", exc_info=True)
                raise
        
        all_embeddings = [None] * len(texts)
        for i, embedding in cached_results:
            all_embeddings[i] = embedding
        for idx, embedding in zip(uncached_indices, new_embeddings):
            all_embeddings[idx] = embedding
        
        return all_embeddings, new_token_usage
    
    def _generate_embeddings_without_cache(self, texts: List[str]) -> Tuple[List[List[float]], Optional[Dict]]:
        """
        生成文本向量嵌入（不使用缓存）
        """
        try:
            response = self._generate_embeddings_internal(texts)
            
            embeddings = [item.embedding for item in response.data]
            
            if embeddings:
                actual_dim = len(embeddings[0])
                logger.info(f"生成的向量维度: {actual_dim}")
            
            token_usage = None
            if hasattr(response, 'usage') and response.usage:
                token_usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': 0,
                    'total_tokens': response.usage.total_tokens
                }
            
            return embeddings, token_usage
        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise ValueError(f"OpenAI API 认证失败: {error_msg}。请检查 API Key 是否正确。")
            logger.error(f"生成嵌入向量失败: {e}", exc_info=True)
            raise
    
    @openai_retry
    def _extract_keywords_internal(self, prompt: str, system_prompt: str):
        """
        内部方法：调用 OpenAI API 提取关键词（带重试）
        
        Args:
            prompt: 用户提示
            system_prompt: 系统提示
        """
        return self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=AIConfig.KEYWORD_EXTRACTION_TEMPERATURE,
            max_tokens=AIConfig.KEYWORD_EXTRACTION_MAX_TOKENS
        )
    
    def extract_keywords(self, question: str, max_keywords: int = AIConfig.KEYWORD_EXTRACTION_MAX_KEYWORDS) -> Tuple[List[str], Optional[Dict]]:
        """
        使用AI从问题中提取关键词
        
        Args:
            question: 用户问题
            max_keywords: 最多返回的关键词数量
            
        Returns:
            (关键词列表, token使用量字典) 元组
        """
        if not question or not question.strip():
            return [], None
        
        if not settings.OPENAI_API_KEY:
            return [question.strip()], None
        
        try:
            # 检测语言
            language = detect_language(question)
            logger.debug(f"检测到问题语言: {language}")
            
            # 根据语言获取相应的prompt
            prompt = Prompts.get_keyword_extraction_prompt(question, language=language)
            system_prompt = Prompts.get_keyword_extraction_system(language=language)
            response = self._extract_keywords_internal(prompt, system_prompt)
            
            keywords_text = response.choices[0].message.content.strip()
            keywords = [k.strip() for k in keywords_text.split(',') if k.strip()]
            
            if not keywords:
                keywords = [question.strip()]
            
            logger.info(f"AI提取的关键词: {keywords}")
            
            token_usage = None
            if hasattr(response, 'usage') and response.usage:
                token_usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            
            return keywords[:max_keywords], token_usage
            
        except Exception as e:
            logger.warning(f"AI关键词提取失败，使用原问题: {e}")
            return [question.strip()], None
    
    @openai_retry
    def _generate_answer_internal(self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int):
        """
        内部方法：调用 OpenAI API 生成回答（带重试）
        """
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def generate_answer(
        self,
        question: str,
        context: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Tuple[str, Optional[Dict]]:
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
        # 检测语言以确定格式
        language = detect_language(question)
        logger.debug(f"检测到问题语言: {language}")
        
        context_parts = []
        for i, ctx in enumerate(context):
            score = ctx.get('score', 0.0)
            content = ctx['content']
            metadata = ctx.get('metadata', {})
            filename = metadata.get('filename', '未知文档')
            
            if language == 'zh':
                context_parts.append(
                    f"【文档片段 {i+1}】（来源: {filename}, 相关度: {score:.1%}）\n{content}"
                )
            else:
                context_parts.append(
                    f"[Document Fragment {i+1}] (Source: {filename}, Relevance: {score:.1%})\n{content}"
                )
        
        context_text = "\n\n".join(context_parts)
        
        core_keywords, _ = self.extract_keywords(question, max_keywords=1)
        
        system_prompt = Prompts.get_answer_generation_system(language=language)
        user_prompt = Prompts.get_answer_generation_prompt(
            question=question,
            context_text=context_text,
            context_count=len(context),
            core_keywords=core_keywords if core_keywords else None,
            language=language
        )
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API Key 未配置。请在 .env 文件中设置 OPENAI_API_KEY")
        
        try:
            response = self._generate_answer_internal(system_prompt, user_prompt, temperature, max_tokens)
            
            token_usage = None
            if hasattr(response, 'usage') and response.usage:
                token_usage = {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            
            answer = response.choices[0].message.content
            return answer, token_usage
        except Exception as e:
            error_msg = str(e)
            if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
                raise ValueError(f"OpenAI API 认证失败: {error_msg}。请检查 API Key 是否正确。")
            logger.error(f"生成回答失败: {e}", exc_info=True)
            raise
    
    @openai_retry
    def _stream_answer_internal(self, system_prompt: str, user_prompt: str, temperature: float, max_tokens: int):
        """
        内部方法：调用 OpenAI API 流式生成回答（带重试）
        """
        # 使用 stream_options 来包含 usage 信息（需要 OpenAI SDK >= 1.12.0）
        return self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            stream_options={"include_usage": True}  # 启用 usage 信息在流式响应中
        )
    
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
            (content, token_usage) 元组，其中 content 是文本片段，token_usage 是字典或 None
        """
        language = detect_language(question)
        logger.debug(f"检测到问题语言: {language}")
        
        context_parts = []
        for i, ctx in enumerate(context):
            score = ctx.get('score', 0.0)
            content = ctx['content']
            metadata = ctx.get('metadata', {})
            filename = metadata.get('filename', '未知文档')
            
            if language == 'zh':
                context_parts.append(
                    f"【文档片段 {i+1}】（来源: {filename}, 相关度: {score:.1%}）\n{content}"
                )
            else:
                context_parts.append(
                    f"[Document Fragment {i+1}] (Source: {filename}, Relevance: {score:.1%})\n{content}"
                )
        
        context_text = "\n\n".join(context_parts)
        
        core_keywords, _ = self.extract_keywords(question, max_keywords=1)
        
        system_prompt = Prompts.get_stream_answer_system(language=language)
        user_prompt = Prompts.get_stream_answer_prompt(
            question=question,
            context_text=context_text,
            core_keywords=core_keywords if core_keywords else None,
            language=language
        )
        
        try:
            stream = self._stream_answer_internal(system_prompt, user_prompt, temperature, max_tokens)
            
            prompt_tokens = 0
            completion_tokens = 0
            last_chunk = None
            full_answer_text = ""
            estimated_prompt_tokens = len(system_prompt + user_prompt) // 3
            
            for chunk in stream:
                last_chunk = chunk
                
                if hasattr(chunk, 'choices') and chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    
                    if hasattr(choice, 'delta') and choice.delta and hasattr(choice.delta, 'content') and choice.delta.content:
                        content = choice.delta.content
                        full_answer_text += content
                        yield (content, None)
                    
                    if hasattr(choice, 'finish_reason') and choice.finish_reason is not None:
                        if hasattr(chunk, 'usage') and chunk.usage:
                            prompt_tokens = chunk.usage.prompt_tokens or estimated_prompt_tokens
                            completion_tokens = chunk.usage.completion_tokens or 0
                
                if hasattr(chunk, 'usage') and chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens or estimated_prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens or 0
            
            if last_chunk and hasattr(last_chunk, 'usage') and last_chunk.usage:
                prompt_tokens = last_chunk.usage.prompt_tokens or estimated_prompt_tokens
                completion_tokens = last_chunk.usage.completion_tokens or 0
            else:
                logger.warning("无法从流式响应获取 usage 信息，使用估算值")
                prompt_tokens = estimated_prompt_tokens
                completion_tokens = len(full_answer_text) // 3
            
            token_usage = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens
            }
            yield (None, token_usage)
            
        except Exception as e:
            logger.error(f"流式生成回答失败: {e}")
            raise

openai_service = OpenAIService()

