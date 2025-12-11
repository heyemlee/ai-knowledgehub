"""
数据库迁移脚本：将注册码表从次数计量改为 Token 计量
Migration: Convert registration codes from count-based to token-based
"""
import sqlite3
import os

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'knowledgehub.db')

def migrate_registration_codes():
    """迁移注册码表结构"""
    print("开始迁移注册码表...")
    print(f"数据库路径: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='registration_codes'
        """)
        
        if not cursor.fetchone():
            print("✅ 注册码表不存在，将在应用启动时自动创建")
            return
        
        # 检查是否已经是新结构
        cursor.execute("PRAGMA table_info(registration_codes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'token_quota' in columns:
            print("✅ 表结构已经是最新的，无需迁移")
            return
        
        print("📝 检测到旧表结构，开始迁移...")
        
        # 1. 创建新表
        cursor.execute("""
            CREATE TABLE registration_codes_new (
                id INTEGER PRIMARY KEY,
                code VARCHAR(100) UNIQUE NOT NULL,
                description VARCHAR(500),
                is_active BOOLEAN NOT NULL DEFAULT 1,
                token_quota INTEGER,
                tokens_used INTEGER NOT NULL DEFAULT 0,
                tokens_per_registration INTEGER NOT NULL DEFAULT 800000,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        """)
        print("✅ 创建新表结构")
        
        # 2. 迁移数据
        # 将 max_uses 转换为 token_quota (max_uses × 800000)
        # 将 used_count 转换为 tokens_used (used_count × 800000)
        cursor.execute("""
            INSERT INTO registration_codes_new 
                (id, code, description, is_active, token_quota, tokens_used, 
                 tokens_per_registration, created_by, created_at, updated_at)
            SELECT 
                id, 
                code, 
                description, 
                is_active,
                CASE 
                    WHEN max_uses IS NULL THEN NULL
                    ELSE max_uses * 800000
                END as token_quota,
                used_count * 800000 as tokens_used,
                800000 as tokens_per_registration,
                created_by,
                created_at,
                updated_at
            FROM registration_codes
        """)
        
        migrated_count = cursor.rowcount
        print(f"✅ 迁移了 {migrated_count} 条记录")
        
        # 3. 删除旧表
        cursor.execute("DROP TABLE registration_codes")
        print("✅ 删除旧表")
        
        # 4. 重命名新表
        cursor.execute("ALTER TABLE registration_codes_new RENAME TO registration_codes")
        print("✅ 重命名新表")
        
        # 5. 创建索引
        cursor.execute("CREATE INDEX idx_registration_codes_code ON registration_codes(code)")
        print("✅ 创建索引")
        
        # 提交更改
        conn.commit()
        print("✅ 迁移完成！")
        
        # 显示迁移后的数据
        cursor.execute("SELECT code, token_quota, tokens_used, tokens_per_registration FROM registration_codes")
        rows = cursor.fetchall()
        if rows:
            print("\n迁移后的数据:")
            for row in rows:
                code, quota, used, per_reg = row
                print(f"  - {code}: {used:,} / {quota:,} tokens ({per_reg:,} tokens/reg)")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_registration_codes()
