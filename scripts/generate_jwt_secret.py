#!/usr/bin/env python3
"""
生成强随机 JWT 密钥
用于 Railway 部署或本地开发
"""
import secrets
import sys


def generate_jwt_secret(length: int = 64) -> str:
    """
    生成强随机 JWT 密钥
    
    Args:
        length: 密钥长度（字节数），默认 64
        
    Returns:
        URL 安全的 base64 编码字符串
    """
    return secrets.token_urlsafe(length)


def main():
    """主函数"""
    print("=" * 60)
    print("🔐 JWT 密钥生成器")
    print("=" * 60)
    print()
    
    # 生成密钥
    secret = generate_jwt_secret()
    
    print("✅ 已生成强随机 JWT 密钥：")
    print()
    print(f"JWT_SECRET_KEY={secret}")
    print()
    print("=" * 60)
    print("📋 使用说明：")
    print("=" * 60)
    print()
    print("1. 复制上面的密钥")
    print("2. 在 Railway 项目的 Variables 中添加:")
    print("   - 变量名: JWT_SECRET_KEY")
    print("   - 变量值: (粘贴上面生成的密钥)")
    print()
    print("3. 本地开发时，添加到 .env 文件:")
    print(f"   JWT_SECRET_KEY={secret}")
    print()
    print("⚠️  安全提示：")
    print("   - 永远不要在 Git 中提交真实密钥")
    print("   - 生产环境和开发环境使用不同的密钥")
    print("   - 定期轮换密钥（建议每 3-6 个月）")
    print("   - 如密钥泄露，立即重新生成并更新")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 错误: {e}", file=sys.stderr)
        sys.exit(1)








