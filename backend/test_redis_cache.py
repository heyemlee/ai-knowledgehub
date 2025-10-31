#!/usr/bin/env python3
"""
测试 Redis 缓存配置
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_redis_config():
    """测试 Redis 配置"""
    print("=" * 60)
    print("Redis 缓存配置测试")
    print("=" * 60)
    
    try:
        from app.core.config import settings
        from app.services.cache_service import cache_service
        
        print(f"\n1. Redis URL 配置:")
        redis_url = getattr(settings, 'REDIS_URL', None)
        if redis_url and redis_url.strip():
            print(f"   ✅ REDIS_URL 已配置: {redis_url[:20]}...")
        else:
            print(f"   ℹ️  REDIS_URL 未配置，将使用内存缓存")
        
        print(f"\n2. 缓存服务状态:")
        print(f"   - 使用 Redis: {cache_service._use_redis}")
        print(f"   - Redis 客户端: {'已连接' if cache_service._redis_client else '未连接'}")
        
        if cache_service._use_redis:
            print(f"\n3. Redis 连接测试:")
            try:
                cache_service._redis_client.ping()
                print(f"   ✅ Redis 连接成功")
            except Exception as e:
                print(f"   ❌ Redis 连接失败: {e}")
        else:
            print(f"\n3. 内存缓存模式:")
            print(f"   ✅ 使用内存缓存（适合单机部署）")
        
        print(f"\n4. 缓存功能测试:")
        test_key = "test:cache:check"
        test_value = {"message": "缓存测试", "timestamp": "2024-01-01"}
        
        # 设置缓存
        cache_service.set(test_key, test_value, ttl=60)
        print(f"   ✅ 设置缓存成功")
        
        # 获取缓存
        cached_value = cache_service.get(test_key)
        if cached_value == test_value:
            print(f"   ✅ 获取缓存成功")
        else:
            print(f"   ⚠️  获取缓存值不匹配")
        
        # 清理测试缓存
        cache_service.delete(test_key)
        print(f"   ✅ 删除缓存成功")
        
        print(f"\n" + "=" * 60)
        print("测试完成！")
        print("=" * 60)
        
        if cache_service._use_redis:
            print("\n💡 提示: Redis 缓存已启用，适合多实例部署场景")
        else:
            print("\n💡 提示: 如需启用 Redis 缓存，请在 .env 文件中配置:")
            print("   REDIS_URL=redis://localhost:6379")
        
    except ImportError as e:
        print(f"\n❌ 导入错误: {e}")
        print("   请确保已安装所有依赖: pip install -r requirements.txt")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_redis_config()

