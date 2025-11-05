"""
API 监控中间件
记录请求统计、响应时间、错误率等
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from typing import Dict
from collections import defaultdict
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """API 监控中间件"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = defaultdict(int)
        self.error_count = defaultdict(int)
        self.response_times = defaultdict(list)
        self.endpoint_stats = defaultdict(lambda: {
            "count": 0,
            "errors": 0,
            "total_time": 0.0,
            "min_time": float("inf"),
        })
        self.window_start = datetime.now()
        self.window_duration = timedelta(minutes=1)  # 统计窗口：1分钟
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并记录统计信息"""
        start_time = time.time()
        path = request.url.path
        method = request.method
        
        # 跳过健康检查和文档路径
        if path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # 记录请求
        self.request_count[f"{method}:{path}"] += 1
        
        # 执行请求
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 记录响应时间
            self.response_times[f"{method}:{path}"].append(process_time)
            if len(self.response_times[f"{method}:{path}"]) > 100:
                self.response_times[f"{method}:{path}"].pop(0)
            
            # 更新端点统计
            endpoint_key = f"{method}:{path}"
            stats = self.endpoint_stats[endpoint_key]
            stats["count"] += 1
            stats["total_time"] += process_time
            stats["min_time"] = min(stats["min_time"], process_time)
            
            # 记录错误
            if response.status_code >= 400:
                self.error_count[f"{method}:{path}"] += 1
                stats["errors"] += 1
                
                logger.warning(
                    f"请求失败: {method} {path} - "
                    f"状态码: {response.status_code}, "
                    f"响应时间: {process_time:.3f}s"
                )
            
            # 添加响应头
            response.headers["X-Process-Time"] = f"{process_time:.3f}"
            
            # 定期记录统计信息
            now = datetime.now()
            if now - self.window_start >= self.window_duration:
                self._log_statistics()
                self._reset_counters()
                self.window_start = now
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            self.error_count[f"{method}:{path}"] += 1
            
            endpoint_key = f"{method}:{path}"
            if endpoint_key in self.endpoint_stats:
                self.endpoint_stats[endpoint_key]["errors"] += 1
            
            logger.error(
                f"请求异常: {method} {path} - "
                f"错误: {str(e)}, "
                f"响应时间: {process_time:.3f}s",
                exc_info=True
            )
            raise
    
    def _log_statistics(self):
        """记录统计信息"""
        logger.info("=== API 统计信息 ===")
        
        # 总请求数
        total_requests = sum(self.request_count.values())
        total_errors = sum(self.error_count.values())
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        logger.info(f"总请求数: {total_requests}")
        logger.info(f"总错误数: {total_errors}")
        logger.info(f"错误率: {error_rate:.2f}%")
        
        # 端点统计
        logger.info("端点统计:")
        for endpoint, stats in sorted(
            self.endpoint_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:10]:  # 只显示前 10 个
            avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
            endpoint_error_rate = (
                stats["errors"] / stats["count"] * 100
                if stats["count"] > 0
                else 0
            )
            
            logger.info(
                f"  {endpoint}: "
                f"请求数={stats['count']}, "
                f"错误数={stats['errors']}, "
                f"错误率={endpoint_error_rate:.2f}%, "
                f"平均响应时间={avg_time:.3f}s, "
                f"最小响应时间={stats['min_time']:.3f}s"
            )
        
        # 响应时间统计
        logger.info("响应时间统计:")
        for endpoint, times in self.response_times.items():
            if times:
                avg_time = sum(times) / len(times)
                max_time = max(times)
                logger.info(
                    f"  {endpoint}: "
                    f"平均={avg_time:.3f}s, "
                    f"最大={max_time:.3f}s, "
                    f"样本数={len(times)}"
                )
    
    def _reset_counters(self):
        """重置计数器（保留统计数据）"""
        # 保留 endpoint_stats 和 response_times，只重置计数器
        pass
    
    def get_statistics(self) -> Dict:
        """获取当前统计信息（用于 API 端点）"""
        total_requests = sum(self.request_count.values())
        total_errors = sum(self.error_count.values())
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        endpoint_stats = {}
        for endpoint, stats in self.endpoint_stats.items():
            avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
            endpoint_error_rate = (
                stats["errors"] / stats["count"] * 100
                if stats["count"] > 0
                else 0
            )
            
            endpoint_stats[endpoint] = {
                "count": stats["count"],
                "errors": stats["errors"],
                "error_rate": round(endpoint_error_rate, 2),
                "avg_response_time": round(avg_time, 3),
                "min_response_time": round(stats["min_time"], 3),
            }
        
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": round(error_rate, 2),
            "endpoints": endpoint_stats,
        }


# 全局监控实例（单例模式）
_monitoring_instance: MonitoringMiddleware = None


def get_monitoring_instance() -> MonitoringMiddleware:
    """获取监控实例"""
    return _monitoring_instance


def set_monitoring_instance(instance: MonitoringMiddleware):
    """设置监控实例"""
    global _monitoring_instance
    _monitoring_instance = instance













