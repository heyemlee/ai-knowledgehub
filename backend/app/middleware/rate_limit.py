"""
API 限流中间件
使用 slowapi 实现请求频率限制
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.core.config import settings
from app.core.constants import RateLimitConfig
import logging

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    获取用户标识符（用于限流）
    
    优先使用用户 ID，其次使用 IP 地址
    """
    # 尝试从 JWT token 中获取用户 ID
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"
    
    # 尝试从 Authorization header 解析（简化处理）
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        # 这里可以解析 JWT 获取 user_id，但为了简化，先使用 IP
        pass
    
    # 使用 IP 地址作为标识符
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[RateLimitConfig.GLOBAL_RATE_LIMIT],
    storage_uri="memory://",  # 使用内存存储（生产环境建议使用 Redis）
    headers_enabled=False,  # 禁用以兼容 FastAPI 的 response_model
)

