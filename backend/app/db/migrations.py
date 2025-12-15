"""
数据库迁移模块
在应用启动时自动运行
"""
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)


def get_db_path():
    """获取数据库路径"""
    # 尝试从环境变量获取
    db_path = os.getenv('DATABASE_PATH')
    if db_path:
        return db_path
    
    # 默认路径
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(backend_dir, 'knowledgehub.db')


def run_migrations():
    """运行所有数据库迁移"""
    try:
        # 迁移 1: 添加 token_quota 字段
        migrate_add_token_quota()
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise


def migrate_add_token_quota():
    """迁移：为 users 表添加 token_quota 字段"""
    try:
        db_path = get_db_path()
        logger.info(f"Using database: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查字段是否已存在
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'token_quota' in columns:
            logger.info("✓ token_quota field already exists, skipping migration")
            conn.close()
            return
        
        logger.info("Adding token_quota field to users table...")
        
        # 添加字段
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN token_quota INTEGER NOT NULL DEFAULT 800000
        """)
        
        conn.commit()
        logger.info("✓ Successfully added token_quota field")
        
        # 验证
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info(f"✓ Migration completed. {user_count} users updated with default quota")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to add token_quota field: {e}")
        raise
