# debug_current_config.py
import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config.config import settings

print("🔍 当前配置调试信息:")
print("=" * 50)

# 检查环境变量
print("📋 环境变量:")
print(f"   MYSQL_HOST: {os.getenv('MYSQL_HOST', '未设置')}")
print(f"   MYSQL_USER: {os.getenv('MYSQL_USER', '未设置')}")
print(f"   MYSQL_PASSWORD: {'*' * len(os.getenv('MYSQL_PASSWORD', '')) if os.getenv('MYSQL_PASSWORD') else '未设置'}")
print(f"   MYSQL_DATABASE: {os.getenv('MYSQL_DATABASE', '未设置')}")

print("\n📊 配置对象:")
print(f"   settings.MYSQL_HOST: {settings.MYSQL_HOST}")
print(f"   settings.MYSQL_USER: {settings.MYSQL_USER}")
print(f"   settings.MYSQL_PASSWORD: {'*' * len(settings.MYSQL_PASSWORD) if settings.MYSQL_PASSWORD else '未设置'}")
print(f"   settings.MYSQL_DATABASE: {settings.MYSQL_DATABASE}")

print(f"\n🔗 数据库URL: {settings.DATABASE_URL}")

# 测试SQLAlchemy连接
print("\n🧪 测试SQLAlchemy连接...")
try:
    from sqlalchemy import create_engine, text
    
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT VERSION()"))
        version = result.scalar()
        print(f"✅ SQLAlchemy连接成功! MySQL版本: {version}")
        
        result = conn.execute(text("SELECT DATABASE()"))
        current_db = result.scalar()
        print(f"✅ 当前数据库: {current_db}")
        
except Exception as e:
    print(f"❌ SQLAlchemy连接失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)