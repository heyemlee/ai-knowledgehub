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
    if isinstance(exception, (RateLimitError, APIConnectionError, APITimeoutError)):
        return True
    
    if isinstance(exception, APIError):
        if hasattr(exception, 'status_code') and exception.status_code:
            status_code = exception.status_code
            if 500 <= status_code < 600:
                return True
            if status_code == 429:
                return True
    
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
    error_msg = str(exception).lower()
    error_type = type(exception).__name__.lower()
    
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


openai_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(
        multiplier=1,
        min=2,
        max=60
    ),
    retry=retry_if_exception(is_retryable_exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO),
    reraise=True,
)


qdrant_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(
        multiplier=1,
        min=1,
        max=30
    ),
    retry=retry_if_exception(is_qdrant_retryable_exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    after=after_log(logger, logging.INFO),
    reraise=True,
)


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
