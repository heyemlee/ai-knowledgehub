"""
Token 使用量追踪服务
记录和管理 OpenAI API token 使用量
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.db.models import TokenUsage, User
from app.core.constants import TokenLimitConfig
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TokenUsageService:
    """Token 使用量服务"""
    
    @staticmethod
    async def record_usage(
        db: AsyncSession,
        user_id: int,
        prompt_tokens: int,
        completion_tokens: int,
        endpoint: Optional[str] = None
    ):
        """
        记录 token 使用量
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            prompt_tokens: 输入 token 数
            completion_tokens: 输出 token 数
            endpoint: API 端点名称
        """
        try:
            total_tokens = prompt_tokens + completion_tokens
            
            # 使用 UTC 时间的日期（用于按日统计）
            usage_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            usage_record = TokenUsage(
                user_id=user_id,
                usage_date=usage_date,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                endpoint=endpoint
            )
            
            db.add(usage_record)
            await db.commit()
            
            logger.info(
                f"记录 Token 使用量: 用户={user_id}, "
                f"prompt={prompt_tokens}, completion={completion_tokens}, "
                f"total={total_tokens}, endpoint={endpoint}"
            )
        except Exception as e:
            logger.error(f"记录 Token 使用量失败: {e}", exc_info=True)
            await db.rollback()
            # 不抛出异常，避免影响主流程
    
    @staticmethod
    async def get_daily_usage(
        db: AsyncSession,
        user_id: int,
        date: Optional[datetime] = None
    ) -> int:
        """
        获取用户指定日期的 token 使用量
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            date: 日期（默认为今天）
            
        Returns:
            总 token 数
        """
        if date is None:
            date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        try:
            result = await db.execute(
                select(func.sum(TokenUsage.total_tokens))
                .where(
                    and_(
                        TokenUsage.user_id == user_id,
                        TokenUsage.usage_date == date
                    )
                )
            )
            total = result.scalar() or 0
            return int(total)
        except Exception as e:
            logger.error(f"获取每日 Token 使用量失败: {e}", exc_info=True)
            return 0
    
    @staticmethod
    async def get_monthly_usage(
        db: AsyncSession,
        user_id: int,
        year: Optional[int] = None,
        month: Optional[int] = None
    ) -> int:
        """
        获取用户指定月份的 token 使用量
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            year: 年份（默认为当前年份）
            month: 月份（默认为当前月份）
            
        Returns:
            总 token 数
        """
        if year is None or month is None:
            now = datetime.utcnow()
            year = now.year
            month = now.month
        
        # 计算月份的开始和结束日期
        start_date = datetime(year, month, 1).replace(hour=0, minute=0, second=0, microsecond=0)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        try:
            result = await db.execute(
                select(func.sum(TokenUsage.total_tokens))
                .where(
                    and_(
                        TokenUsage.user_id == user_id,
                        TokenUsage.usage_date >= start_date,
                        TokenUsage.usage_date < end_date
                    )
                )
            )
            total = result.scalar() or 0
            return int(total)
        except Exception as e:
            logger.error(f"获取每月 Token 使用量失败: {e}", exc_info=True)
            return 0
    
    @staticmethod
    async def check_token_limit(
        db: AsyncSession,
        user_id: int,
        estimated_tokens: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """
        检查用户是否超过 token 限制
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            estimated_tokens: 本次请求预估的 token 数（用于提前检查）
            
        Returns:
            (是否允许, 错误消息)
        """
        try:
            # 检查单次请求限制
            if estimated_tokens > TokenLimitConfig.MAX_TOKENS_PER_REQUEST:
                return False, f"单次请求预估 token 数 ({estimated_tokens}) 超过限制 ({TokenLimitConfig.MAX_TOKENS_PER_REQUEST})"
            
            # 检查每日限制
            daily_usage = await TokenUsageService.get_daily_usage(db, user_id)
            if daily_usage + estimated_tokens > TokenLimitConfig.DAILY_TOKEN_LIMIT_PER_USER:
                remaining = TokenLimitConfig.DAILY_TOKEN_LIMIT_PER_USER - daily_usage
                return False, (
                    f"已达到每日 Token 使用量限制。"
                    f"今日已使用: {daily_usage}/{TokenLimitConfig.DAILY_TOKEN_LIMIT_PER_USER}, "
                    f"剩余: {remaining}。请明天再试。"
                )
            
            # 检查每月限制
            monthly_usage = await TokenUsageService.get_monthly_usage(db, user_id)
            if monthly_usage + estimated_tokens > TokenLimitConfig.MONTHLY_TOKEN_LIMIT_PER_USER:
                remaining = TokenLimitConfig.MONTHLY_TOKEN_LIMIT_PER_USER - monthly_usage
                return False, (
                    f"已达到每月 Token 使用量限制。"
                    f"本月已使用: {monthly_usage}/{TokenLimitConfig.MONTHLY_TOKEN_LIMIT_PER_USER}, "
                    f"剩余: {remaining}。请下个月再试或联系管理员。"
                )
            
            return True, None
            
        except Exception as e:
            logger.error(f"检查 Token 限制失败: {e}", exc_info=True)
            # 发生错误时允许请求，避免影响服务可用性
            return True, None
    
    @staticmethod
    async def get_usage_stats(
        db: AsyncSession,
        user_id: int
    ) -> dict:
        """
        获取用户 token 使用统计
        
        Args:
            db: 数据库会话
            user_id: 用户ID
            
        Returns:
            统计信息字典
        """
        try:
            daily_usage = await TokenUsageService.get_daily_usage(db, user_id)
            monthly_usage = await TokenUsageService.get_monthly_usage(db, user_id)
            
            return {
                "daily_usage": daily_usage,
                "daily_limit": TokenLimitConfig.DAILY_TOKEN_LIMIT_PER_USER,
                "daily_remaining": max(0, TokenLimitConfig.DAILY_TOKEN_LIMIT_PER_USER - daily_usage),
                "monthly_usage": monthly_usage,
                "monthly_limit": TokenLimitConfig.MONTHLY_TOKEN_LIMIT_PER_USER,
                "monthly_remaining": max(0, TokenLimitConfig.MONTHLY_TOKEN_LIMIT_PER_USER - monthly_usage),
            }
        except Exception as e:
            logger.error(f"获取 Token 使用统计失败: {e}", exc_info=True)
            return {
                "daily_usage": 0,
                "daily_limit": TokenLimitConfig.DAILY_TOKEN_LIMIT_PER_USER,
                "daily_remaining": TokenLimitConfig.DAILY_TOKEN_LIMIT_PER_USER,
                "monthly_usage": 0,
                "monthly_limit": TokenLimitConfig.MONTHLY_TOKEN_LIMIT_PER_USER,
                "monthly_remaining": TokenLimitConfig.MONTHLY_TOKEN_LIMIT_PER_USER,
            }


token_usage_service = TokenUsageService()


