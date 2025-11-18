# server/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from config.config import settings

# 创建MySQL数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.MYSQL_POOL_SIZE,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    echo=True  # 开发时显示SQL，生产环境设为False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 从现有的user.py导入Base，确保使用同一个Base
from .models.user import Base

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """创建所有数据库表"""
    Base.metadata.create_all(bind=engine)

def update_database_schema():
    """更新数据库表结构，添加缺失的字段"""
    try:
        with engine.connect() as conn:
            # 检查 messages 表是否存在
            result = conn.execute(text("SHOW TABLES LIKE 'messages'"))
            if result.fetchone():
                print("📊 找到 messages 表，开始检查字段...")
                
                # 检查并添加缺失的列
                columns_to_check = [
                    ("file_name", "VARCHAR(255)"),
                    ("file_size", "INT"),
                    ("mime_type", "VARCHAR(100)"),
                    ("file_path", "VARCHAR(500)"),
                    ("thumbnail_path", "VARCHAR(500)"),
                    ("duration", "INT"),
                    ("message_type", "VARCHAR(20)")
                ]
                
                for column_name, column_type in columns_to_check:
                    try:
                        # 检查列是否已存在
                        check_sql = text(f"""
                            SELECT COUNT(*) FROM information_schema.COLUMNS 
                            WHERE TABLE_SCHEMA = 'allen_chat' 
                            AND TABLE_NAME = 'messages' 
                            AND COLUMN_NAME = '{column_name}'
                        """)
                        result = conn.execute(check_sql)
                        if result.fetchone()[0] == 0:
                            # 添加列
                            alter_sql = text(f"ALTER TABLE messages ADD COLUMN {column_name} {column_type}")
                            conn.execute(alter_sql)
                            print(f"✅ 已添加列: {column_name}")
                        else:
                            print(f"✅ 列已存在: {column_name}")
                            
                    except Exception as e:
                        print(f"❌ 添加列 {column_name} 时出错: {e}")
                
                # 设置 message_type 的默认值
                try:
                    update_sql = text("UPDATE messages SET message_type = 'text' WHERE message_type IS NULL")
                    conn.execute(update_sql)
                    print("✅ 已设置 message_type 默认值")
                except Exception as e:
                    print(f"⚠️ 设置默认值时出错: {e}")
                
                print("🎉 数据库表结构更新完成！")
            else:
                print("❌ messages 表不存在，将创建新表...")
                create_tables()
                print("✅ 数据库表创建完成！")
                
        # 提交更改
        conn.commit()
                
    except Exception as e:
        print(f"❌ 数据库更新失败: {e}")

def init_database():
    """初始化数据库：创建表和更新结构"""
    print("🔄 初始化数据库...")
    
    try:
        # 创建所有表
        create_tables()
        print("✅ 数据库表创建完成")
        
        # 更新表结构
        update_database_schema()
        print("🎉 数据库初始化完成")
        
    except Exception as e:
        print(f"⚠️ 数据库初始化过程中出现警告: {e}")
        # 不抛出异常，让服务器继续启动