import pymysql
from config.config import settings

def test_mysql_connection():
    try:
        print("🔗 测试MySQL连接...")
        print(f"主机: {settings.MYSQL_HOST}")
        print(f"端口: {settings.MYSQL_PORT}")
        print(f"用户: {settings.MYSQL_USER}")
        print(f"数据库: {settings.MYSQL_DATABASE}")
        
        # 测试连接
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DATABASE,
            charset=settings.MYSQL_CHARSET
        )
        
        print("✅ MySQL连接成功！")
        
        # 测试查询
        with connection.cursor() as cursor:
            # 测试版本
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ MySQL版本: {version[0]}")
            
            # 测试当前数据库
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()
            print(f"✅ 当前数据库: {current_db[0]}")
            
            # 测试字符集
            cursor.execute("SELECT @@character_set_database, @@collation_database")
            charset, collation = cursor.fetchone()
            print(f"✅ 数据库字符集: {charset}")
            print(f"✅ 数据库排序规则: {collation}")
            
            # 列出所有表（应该是空的）
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ 当前表数量: {len(tables)}")
            if tables:
                print("📊 现有表:")
                for table in tables:
                    print(f"   - {table[0]}")
            
        connection.close()
        return True
        
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        return False

if __name__ == "__main__":
    if test_mysql_connection():
        print("\n🎉 MySQL连接测试通过！可以继续下一步。")
    else:
        print("\n💥 MySQL连接测试失败，请检查配置。")