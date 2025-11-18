from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
from urllib.parse import quote_plus

# 加载 .env 文件
load_dotenv()

class Settings(BaseSettings):
    # 服务器配置
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    WEBSOCKET_PORT: int = 8001
    
    # MySQL 8 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "allen_chat"
    MYSQL_CHARSET: str = "utf8mb4"
    
    # 连接池配置
    MYSQL_POOL_SIZE: int = 5
    MYSQL_POOL_RECYCLE: int = 3600
    
    # JWT配置
    SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    @property
    def DATABASE_URL(self):
        """获取MySQL数据库连接URL - 对密码进行URL编码"""
        encoded_password = quote_plus(self.MYSQL_PASSWORD)
        return f"mysql+pymysql://{self.MYSQL_USER}:{encoded_password}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset={self.MYSQL_CHARSET}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()

# 调试信息（可选）
if __name__ == "__main__":
    print("🔧 配置调试信息:")
    print(f"MYSQL_HOST: {settings.MYSQL_HOST}")
    print(f"MYSQL_USER: {settings.MYSQL_USER}")
    print(f"MYSQL_PASSWORD: {'*' * len(settings.MYSQL_PASSWORD) if settings.MYSQL_PASSWORD else '空'}")
    print(f"MYSQL_DATABASE: {settings.MYSQL_DATABASE}")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")