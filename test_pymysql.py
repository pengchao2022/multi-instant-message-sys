# test_fixed_pymysql.py
from config.config import settings
from urllib.parse import quote_plus

def test_password_encoding():
    """测试密码编码"""
    original_password = "Hellokity@20222022"
    encoded_password = quote_plus(original_password)
    
    print("🔐 密码编码测试:")
    print(f"   原始密码: {original_password}")
    print(f"   编码后: {encoded_password}")
    print(f"   数据库URL: {settings.DATABASE_URL}")
    
    return encoded_password

def test_sqlalchemy_connection():
    """测试修复后的SQLAlchemy连接"""
    try:
        print("\n🔗 测试修复后的SQLAlchemy连接...")
        
        from sqlalchemy import create_engine, text
        
        engine = create_engine(settings.DATABASE_URL)
        
        with engine.connect() as connection:
            result = connection.execute(text("SELECT VERSION()"))
            version = result.scalar()
            print(f"✅ SQLAlchemy 连接成功！")
            print(f"✅ MySQL版本: {version}")
            
            result = connection.execute(text("SELECT DATABASE()"))
            current_db = result.scalar()
            print(f"✅ 当前数据库: {current_db}")
            
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy 连接失败: {e}")
        return False

if __name__ == "__main__":
    print("🔧 修复密码编码问题...\n")
    
    encoded_password = test_password_encoding()
    
    if test_sqlalchemy_connection():
        print("\n🎉 修复成功！现在可以启动服务器了")
    else:
        print("\n💥 修复失败，请检查配置")