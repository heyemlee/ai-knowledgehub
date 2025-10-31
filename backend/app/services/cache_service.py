"""
缓存服务
支持内存缓存和 Redis（可选）
"""
import hashlib
import json
import time
from typing import Optional, Any, Dict, List
from functools import wraps
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """缓存服务"""
    
    def __init__(self):
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._redis_client = None
        self._use_redis = False
        self._init_redis()
    
    def _init_redis(self):
        """初始化 Redis 客户端（如果可用）"""
        try:
            redis_url = getattr(settings, 'REDIS_URL', None)
            if redis_url and redis_url.strip():
                try:
                    import redis
                    self._redis_client = redis.from_url(redis_url, decode_responses=True)
                    # 测试连接
                    self._redis_client.ping()
                    self._use_redis = True
                    logger.info("Redis 缓存已启用")
                except ImportError:
                    logger.warning("Redis 库未安装，使用内存缓存。安装: pip install redis")
                    self._use_redis = False
            else:
                logger.info("Redis 未配置，使用内存缓存")
        except Exception as e:
            logger.warning(f"Redis 初始化失败，使用内存缓存: {e}")
            self._use_redis = False
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 将参数序列化为字符串
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        # 使用 hash 生成固定长度的键
        key_hash = hashlib.sha256(key_str.encode('utf-8')).hexdigest()
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            if self._use_redis and self._redis_client:
                cached = self._redis_client.get(key)
                if cached:
                    data = json.loads(cached)
                    # 检查是否过期
                    if data.get('expires_at', 0) > time.time():
                        return data.get('value')
                    else:
                        # 过期，删除
                        self._redis_client.delete(key)
                return None
            else:
                # 内存缓存
                if key in self._memory_cache:
                    cached = self._memory_cache[key]
                    if cached.get('expires_at', 0) > time.time():
                        return cached.get('value')
                    else:
                        # 过期，删除
                        del self._memory_cache[key]
                return None
        except Exception as e:
            logger.warning(f"获取缓存失败: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值（必须是可序列化的）
            ttl: 过期时间（秒），默认 1 小时
        """
        try:
            expires_at = time.time() + ttl
            cache_data = {
                'value': value,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            if self._use_redis and self._redis_client:
                self._redis_client.setex(
                    key,
                    ttl,
                    json.dumps(cache_data, ensure_ascii=False)
                )
            else:
                # 内存缓存
                # 限制内存缓存大小（最多保留 1000 个条目）
                if len(self._memory_cache) >= 1000:
                    # 删除最旧的条目
                    oldest_key = min(
                        self._memory_cache.items(),
                        key=lambda x: x[1].get('created_at', 0)
                    )[0]
                    del self._memory_cache[oldest_key]
                
                self._memory_cache[key] = cache_data
        except Exception as e:
            logger.warning(f"设置缓存失败: {e}")
    
    def delete(self, key: str):
        """删除缓存"""
        try:
            if self._use_redis and self._redis_client:
                self._redis_client.delete(key)
            else:
                self._memory_cache.pop(key, None)
        except Exception as e:
            logger.warning(f"删除缓存失败: {e}")
    
    def clear(self, prefix: str = None):
        """清空缓存"""
        try:
            if self._use_redis and self._redis_client:
                if prefix:
                    # 删除指定前缀的所有键
                    keys = self._redis_client.keys(f"{prefix}:*")
                    if keys:
                        self._redis_client.delete(*keys)
                else:
                    # 清空所有（谨慎使用）
                    self._redis_client.flushdb()
            else:
                if prefix:
                    # 删除指定前缀的所有键
                    keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(prefix + ":")]
                    for k in keys_to_delete:
                        del self._memory_cache[k]
                else:
                    self._memory_cache.clear()
        except Exception as e:
            logger.warning(f"清空缓存失败: {e}")
    
    def cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键的便捷方法"""
        return self._generate_key(prefix, *args, **kwargs)


# 全局缓存服务实例
_cache_service_instance = None

def get_cache_service() -> CacheService:
    """获取缓存服务实例（单例模式）"""
    global _cache_service_instance
    if _cache_service_instance is None:
        _cache_service_instance = CacheService()
    return _cache_service_instance

cache_service = get_cache_service()


def cached(prefix: str, ttl: int = 3600):
    """
    缓存装饰器
    
    Args:
        prefix: 缓存键前缀
        ttl: 过期时间（秒）
    
    Usage:
        @cached("embedding", ttl=86400)  # 24小时
        def generate_embeddings(texts: List[str]):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_service._generate_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key[:50]}...")
                return cached_value
            
            # 缓存未命中，执行函数
            result = func(*args, **kwargs)
            
            # 保存到缓存
            if result is not None:
                cache_service.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


async def async_cached(prefix: str, ttl: int = 3600):
    """
    异步缓存装饰器
    
    Args:
        prefix: 缓存键前缀
        ttl: 过期时间（秒）
    
    Usage:
        @async_cached("search", ttl=3600)
        async def search(query_embedding, limit):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = cache_service._generate_key(prefix, *args, **kwargs)
            
            # 尝试从缓存获取
            cached_value = cache_service.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key[:50]}...")
                return cached_value
            
            # 缓存未命中，执行函数
            result = await func(*args, **kwargs)
            
            # 保存到缓存
            if result is not None:
                cache_service.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator

