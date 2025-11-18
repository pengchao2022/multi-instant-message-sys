import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config.config import settings
from server.models.user import User

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户凭据"""
        user = self.db.query(User).filter(User.username == username).first()
        if not user or not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_user(self, user_data) -> User:
        """创建新用户"""
        from src.shared.protocols import RegisterRequest
        
        if isinstance(user_data, RegisterRequest):
            username = user_data.username
            email = user_data.email
            password = user_data.password
        else:
            username = user_data.get('username')
            email = user_data.get('email')
            password = user_data.get('password')
        
        # 检查用户名是否已存在
        if self.get_user_by_username(username):
            raise ValueError(f"Username {username} already exists")
        
        # 检查邮箱是否已存在
        if self.db.query(User).filter(User.email == email).first():
            raise ValueError(f"Email {email} already exists")
            
        hashed_password = self.get_password_hash(password)
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            status="offline"  # 默认状态为离线
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """创建JWT访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except JWTError:
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据用户ID获取用户"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def update_user_status(self, user_id: int, status: str) -> bool:
        """更新用户状态"""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                user.status = status
                user.last_seen = datetime.utcnow()
                self.db.commit()
                print(f"✅ 用户 {user.username} 状态更新为: {status}")
                return True
            else:
                print(f"❌ 用户ID {user_id} 不存在")
                return False
        except Exception as e:
            print(f"❌ 更新用户状态失败: {e}")
            self.db.rollback()
            return False
    
    def get_all_users(self) -> List[User]:
        """获取所有用户"""
        return self.db.query(User).all()
    
    def get_online_users(self) -> List[User]:
        """获取在线用户列表"""
        return self.db.query(User).filter(User.status == "online").all()
    
    def get_offline_users(self) -> List[User]:
        """获取离线用户列表"""
        return self.db.query(User).filter(User.status == "offline").all()
    
    def create_or_get_user(self, user_id: int, username: str) -> User:
        """创建或获取用户（用于测试）"""
        user = self.get_user_by_id(user_id)
        if user:
            return user
        
        # 创建新用户
        user = User(
            id=user_id,
            username=username,
            email=f"{username}@test.com",
            hashed_password="test",  # 简化测试密码
            status="online"
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        print(f"✅ 创建测试用户: {user.username} (ID: {user.id})")
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                self.db.delete(user)
                self.db.commit()
                print(f"✅ 删除用户: {user.username} (ID: {user.id})")
                return True
            return False
        except Exception as e:
            print(f"❌ 删除用户失败: {e}")
            self.db.rollback()
            return False
    
    def update_user_password(self, user_id: int, new_password: str) -> bool:
        """更新用户密码"""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                user.hashed_password = self.get_password_hash(new_password)
                self.db.commit()
                print(f"✅ 用户 {user.username} 密码已更新")
                return True
            return False
        except Exception as e:
            print(f"❌ 更新用户密码失败: {e}")
            self.db.rollback()
            return False
    
    def search_users_by_username(self, username_query: str) -> List[User]:
        """根据用户名搜索用户"""
        return self.db.query(User).filter(User.username.ilike(f"%{username_query}%")).all()
    
    def get_user_stats(self) -> dict:
        """获取用户统计信息"""
        total_users = self.db.query(User).count()
        online_users = self.db.query(User).filter(User.status == "online").count()
        offline_users = total_users - online_users
        
        return {
            "total_users": total_users,
            "online_users": online_users,
            "offline_users": offline_users
        }
    
    def validate_user_credentials(self, username: str, password: str) -> dict:
        """验证用户凭据并返回验证结果"""
        user = self.authenticate_user(username, password)
        if user:
            return {
                "valid": True,
                "user_id": user.id,
                "username": user.username,
                "status": user.status
            }
        else:
            return {
                "valid": False,
                "error": "Invalid credentials"
            }
    
    def refresh_user_token(self, token: str) -> Optional[str]:
        """刷新用户令牌"""
        payload = self.verify_token(token)
        if payload is None:
            return None
        
        username: str = payload.get("sub")
        if username is None:
            return None
        
        user = self.get_user_by_username(username)
        if user is None:
            return None
        
        # 创建新的访问令牌
        new_token = self.create_access_token(data={"sub": username})
        return new_token
    
    def get_user_session_info(self, user_id: int) -> Optional[dict]:
        """获取用户会话信息"""
        user = self.get_user_by_id(user_id)
        if user:
            return {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "status": user.status,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None
            }
        return None
    
    def bulk_update_user_status(self, user_ids: List[int], status: str) -> bool:
        """批量更新用户状态"""
        try:
            users = self.db.query(User).filter(User.id.in_(user_ids)).all()
            for user in users:
                user.status = status
                user.last_seen = datetime.utcnow()
            
            self.db.commit()
            print(f"✅ 批量更新 {len(users)} 个用户状态为: {status}")
            return True
        except Exception as e:
            print(f"❌ 批量更新用户状态失败: {e}")
            self.db.rollback()
            return False
    
    def cleanup_inactive_users(self, inactive_days: int = 30) -> int:
        """清理长期不活跃的用户（模拟功能）"""
        # 注意：实际项目中应该谨慎使用此功能
        # 这里只是模拟，实际应该标记为不活跃而不是删除
        print(f"⚠️  清理不活跃用户功能已禁用（安全考虑）")
        return 0
    
    def is_user_online(self, user_id: int) -> bool:
        """检查用户是否在线"""
        user = self.get_user_by_id(user_id)
        return user is not None and user.status == "online"
    
    def get_user_activity(self, user_id: int) -> Optional[dict]:
        """获取用户活动信息"""
        user = self.get_user_by_id(user_id)
        if user:
            return {
                "user_id": user.id,
                "username": user.username,
                "status": user.status,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None,
                "is_online": user.status == "online"
            }
        return None