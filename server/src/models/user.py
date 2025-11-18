from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

# 群组-用户关联表
group_members = Table(
    'group_members',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    status = Column(String(20), default="offline")
    created_at = Column(DateTime, default=func.now())
    last_seen = Column(DateTime, default=func.now())
    
    # 关系
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    received_messages = relationship("Message", back_populates="receiver", foreign_keys="Message.receiver_id")
    groups = relationship("Group", secondary=group_members, back_populates="members")
    owned_groups = relationship("Group", back_populates="owner")

    def to_dict(self):
        """将用户对象转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }

    def to_dict_without_sensitive(self):
        """转换为字典（不包含敏感信息）"""
        return {
            "id": self.id,
            "username": self.username,
            "status": self.status,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, file, audio, video
    file_name = Column(String(255), nullable=True)  # 文件名
    file_size = Column(Integer, nullable=True)  # 文件大小（字节）
    mime_type = Column(String(100), nullable=True)  # 文件MIME类型
    file_path = Column(String(500), nullable=True)  # 文件存储路径
    thumbnail_path = Column(String(500), nullable=True)  # 缩略图路径（用于图片/视频）
    duration = Column(Integer, nullable=True)  # 音频/视频时长（秒）
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    timestamp = Column(DateTime, default=func.now())
    is_read = Column(Boolean, default=False)
    
    # 关系
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    receiver = relationship("User", back_populates="received_messages", foreign_keys=[receiver_id])
    group = relationship("Group", back_populates="messages")

    def to_dict(self):
        """将消息对象转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "message_type": self.message_type,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "file_path": self.file_path,
            "thumbnail_path": self.thumbnail_path,
            "duration": self.duration,
            "sender_id": self.sender_id,
            "sender_username": self.sender.username if self.sender else None,
            "receiver_id": self.receiver_id,
            "receiver_username": self.receiver.username if self.receiver else None,
            "group_id": self.group_id,
            "group_name": self.group.name if self.group else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_read": self.is_read
        }

    def to_dict_basic(self):
        """转换为基本字典（用于WebSocket消息）"""
        return {
            "id": self.id,
            "content": self.content,
            "message_type": self.message_type,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "sender_id": self.sender_id,
            "sender_username": self.sender.username if self.sender else "Unknown",
            "receiver_id": self.receiver_id,
            "group_id": self.group_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_read": self.is_read
        }

    def to_dict_for_websocket(self):
        """转换为WebSocket消息格式"""
        data = {
            "id": self.id,
            "content": self.content,
            "message_type": self.message_type,
            "sender_id": self.sender_id,
            "sender_username": self.sender.username if self.sender else "Unknown",
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_read": self.is_read
        }
        
        # 添加文件相关字段（如果存在）
        if self.file_name:
            data["file_name"] = self.file_name
        if self.file_size:
            data["file_size"] = self.file_size
        if self.mime_type:
            data["mime_type"] = self.mime_type
        if self.file_path:
            data["file_path"] = self.file_path
            
        # 添加接收者信息（如果是私聊）
        if self.receiver_id:
            data["receiver_id"] = self.receiver_id
            data["receiver_username"] = self.receiver.username if self.receiver else None
            
        # 添加群组信息（如果是群聊）
        if self.group_id:
            data["group_id"] = self.group_id
            data["group_name"] = self.group.name if self.group else None
            
        return data

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # 关系
    owner = relationship("User", back_populates="owned_groups")
    members = relationship("User", secondary=group_members, back_populates="groups")
    messages = relationship("Message", back_populates="group")

    def to_dict(self):
        """将群组对象转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "owner_username": self.owner.username if self.owner else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "member_count": len(self.members) if self.members else 0,
            "message_count": len(self.messages) if self.messages else 0
        }

    def to_dict_with_members(self):
        """转换为包含成员信息的字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "owner_username": self.owner.username if self.owner else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "members": [member.to_dict_without_sensitive() for member in self.members] if self.members else [],
            "member_count": len(self.members) if self.members else 0
        }

    def to_dict_basic(self):
        """转换为基本字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "owner_username": self.owner.username if self.owner else None,
            "member_count": len(self.members) if self.members else 0
        }