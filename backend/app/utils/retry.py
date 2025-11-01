"""
重试机制工具模块
提供指数退避重试装饰器和重试配置
"""
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception,
    before_sleep_log,
    after_log,
)
from openai import RateLimitError, APIConnectionError, APIError, APITimeoutError
from typing import Type, Tuple
import logging

logger = logging.getLogger(__name__)


def is_retryable_exception(exception: Exception) -> bool:
    """
    判断异常是否可重试
    
    Args:
        exception: 异常对象
        
    Returns:
        是否可重试
    """
    # OpenAI 可重试的异常
    if isinstance(exception, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    
    # APIError 需要根据状态码判断
    if isinstance(exception, APIError):
        # 5xx 服务器错误可重试
        if hasattr(exception, 'status_code') and exception.status_code:
            status_code = exception.status_code
            if 500 <= status_code < 600:
                return True
            # 429 限流错误可重试
            if status_code == 429:
                return True
    
    # 网络连接相关的错误
    error_msg = str(exception).lower()
    retryable_keywords = [
        'connection',
        'timeout',
        'network',
        'temporary',
        'unavailable',
        'service unavailable',
        'rate limit',
        'too many requests',
    ]
    
    if any(keyword in error_msg for keyword in retryable_keywords):
        return True
    
    return False


def is_qdrant_retryable_exception(exception: Exception) -> bool:
    """
    判断 Qdrant 异常是否可重试
    
    Args:
        exception: 异常对象
        
    Returns:
        是否可重试
    """
    error_msg = str(exception).lower()
    error_type = type(exception).__name__.lower()
    
    # 连接相关的错误
    retryable_keywords = [
        'connection',
        'timeout',
        'network',
        'temporary',
        'unavailable',
        'service unavailable',
        'broken pipe',
        'connection reset',
        'connection refused',
    ]
    
    # 检查异常类型
    retryable_types = [
        'connectionerror',
        'timeouterror',
        'httperror',
        'requests.exceptions',
    ]
    
    if any(keyword in error_msg for keyword in retryable_keywords):
        return True
    
    if any(retry_type in error_type for retry_type in retryable_types):
        return True
    
    return False


# OpenAI API 重试配置
openai_retry = retry(
    stop=stop_after_attempt(3),  # 最多重试 3 次
    wait=wait_exponential(
        multiplier=1,  # 初始等待时间倍数
        min=2,  # 最小等待时间（秒）
        max=60  # 最大等待时间（秒）
    ),
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO),
    reraise=True,  # 重试失败后重新抛出异常
)


# Qdrant 连接重试配置
qdrant_retry = retry(
    stop=stop_after_attempt(5),  # 最多重试 5 次（连接问题可能需要更多重试）
    wait=wait_exponential(
        multiplier=1,
        min=1,  # 连接重试初始等待时间稍短
        max=30  # 最大等待时间
    ),
    retry=retry_if_exception(is_qdrant_retryable_exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO),
    reraise=True,
)


# Qdrant 操作重试配置（搜索、插入等）
qdrant_operation_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=20
    ),
    retry=retry_if_exception(is_qdrant_retryable_exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO),
    reraise=True,
)









