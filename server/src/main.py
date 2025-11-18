import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict
import uvicorn
import asyncio
import uuid
import shutil
import base64

from config.config import settings
from shared.protocols import LoginRequest, RegisterRequest, WSMessage, WSMessageTypes, MessageResponse, UserResponse
from models.user import Base, User, Message, Group
from services.auth_service import AuthService
from connection_manager import ConnectionManager

# 修复数据库配置 - 移除SQLite特有参数
engine = create_engine(
    settings.DATABASE_URL,
    # 移除 check_same_thread 参数，这是SQLite特有的
    # connect_args={"check_same_thread": False}  # 删除这一行
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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

def create_tables():
    """创建所有数据库表"""
    Base.metadata.create_all(bind=engine)

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

# 创建表并初始化数据库
init_database()

app = FastAPI(
    title="Multi Instant Message System",
    description="多用户即时消息系统 API",
    version="1.0.0"
)

# CORS配置
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 连接管理器
connection_manager = ConnectionManager()

# 文件上传配置
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 依赖注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    return AuthService(db)

# REST API 路由
@app.post("/register", response_model=dict)
async def register(user_data: RegisterRequest, auth_service: AuthService = Depends(get_auth_service)):
    """
    用户注册
    """
    try:
        user = auth_service.create_user(user_data)
        return {
            "message": "User created successfully", 
            "user_id": user.id,
            "username": user.username
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/login", response_model=dict)
async def login(login_data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)):
    """
    用户登录
    """
    user = auth_service.authenticate_user(login_data.username, login_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 更新用户状态为在线
    auth_service.update_user_status(user.id, "online")
    
    access_token = auth_service.create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username
    }

@app.post("/send-message", response_model=dict)
async def send_message(
    message_data: dict,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    通过REST API发送消息
    """
    try:
        print(f"📨 收到REST消息发送请求: {message_data}")
        
        # 验证发送者
        sender_id = message_data.get("sender_id")
        if not sender_id:
            raise HTTPException(status_code=400, detail="sender_id is required")
        
        sender = auth_service.get_user_by_id(sender_id)
        if not sender:
            raise HTTPException(status_code=404, detail="Sender not found")
        
        # 验证消息内容
        content = message_data.get("content")
        if not content:
            raise HTTPException(status_code=400, detail="Message content is required")
        
        # 检查是私聊还是群聊
        receiver_id = message_data.get("receiver_id")
        message_type = message_data.get("message_type", "private")
        
        print(f"🔍 消息类型: {message_type}, 接收者ID: {receiver_id}")
        
        if message_type == "private" and receiver_id:
            # 私聊消息需要验证接收者
            receiver = auth_service.get_user_by_id(receiver_id)
            if not receiver:
                raise HTTPException(status_code=404, detail="Receiver not found")
            print(f"📨 私聊消息: {sender.username} -> {receiver.username}")
        elif message_type == "public":
            print(f"📢 公共消息: {sender.username}")
            receiver_id = None  # 公共消息没有特定接收者
        else:
            raise HTTPException(status_code=400, detail="Invalid message type or missing receiver_id for private message")
        
        # 创建WebSocket消息格式
        ws_message_data = {
            "content": content,
            "message_type": message_type,
            "receiver_id": receiver_id,
            "group_id": message_data.get("group_id")
        }
        
        ws_message = WSMessage(
            type=WSMessageTypes.MESSAGE_SEND,
            data=ws_message_data
        )
        
        print(f"🔄 处理消息: 发送者 {sender.username} -> 接收者 {receiver_id}")
        print(f"🔄 当前活跃连接数量: {len(connection_manager.active_connections)}")
        print(f"🔄 当前活跃连接用户ID: {list(connection_manager.active_connections.keys())}")
        
        # 使用连接管理器处理消息
        await connection_manager.handle_message_send(ws_message, sender, db)
        
        return {
            "message": "Message sent successfully",
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "content": content[:50] + "..." if len(content) > 50 else content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 发送消息失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@app.post("/send-message-with-files")
async def send_message_with_files(
    message_data: dict,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    发送包含文本和文件的消息
    """
    try:
        print(f"📦 收到组合消息发送请求: {message_data}")
        
        # 验证发送者
        sender_id = message_data.get("sender_id")
        if not sender_id:
            raise HTTPException(status_code=400, detail="sender_id is required")
        
        sender = auth_service.get_user_by_id(sender_id)
        if not sender:
            raise HTTPException(status_code=404, detail="Sender not found")
        
        # 获取消息内容
        text_content = message_data.get("text_content", "")
        files = message_data.get("files", [])
        
        # 检查是私聊还是群聊
        receiver_id = message_data.get("receiver_id")
        message_type = message_data.get("message_type", "private")
        
        print(f"🔍 组合消息类型: {message_type}, 接收者ID: {receiver_id}, 文件数量: {len(files)}")
        
        if message_type == "private" and receiver_id:
            # 私聊消息需要验证接收者
            receiver = auth_service.get_user_by_id(receiver_id)
            if not receiver:
                raise HTTPException(status_code=404, detail="Receiver not found")
            print(f"📨 私聊组合消息: {sender.username} -> {receiver.username}")
        elif message_type == "public":
            print(f"📢 公共组合消息: {sender.username}")
            receiver_id = None  # 公共消息没有特定接收者
        else:
            raise HTTPException(status_code=400, detail="Invalid message type or missing receiver_id for private message")
        
        # 处理文件上传
        uploaded_files = []
        for file_info in files:
            try:
                file_name = file_info.get("file_name")
                file_data_base64 = file_info.get("file_data")
                file_size = file_info.get("file_size", 0)
                is_image = file_info.get("is_image", False)
                mime_type = file_info.get("mime_type", "application/octet-stream")
                
                if not file_name or not file_data_base64:
                    print(f"⚠️ 文件信息不完整: {file_name}")
                    continue
                
                # 解码base64文件数据
                file_data = base64.b64decode(file_data_base64)
                
                # 生成唯一文件名
                file_extension = os.path.splitext(file_name)[1]
                unique_filename = f"{uuid.uuid4().hex}{file_extension}"
                file_path = os.path.join(UPLOAD_DIR, unique_filename)
                
                # 保存文件
                with open(file_path, "wb") as buffer:
                    buffer.write(file_data)
                
                # 确定消息类型
                file_message_type = "image" if is_image else "file"
                
                # 保存到数据库
                db_message = Message(
                    content=f"/download/{unique_filename}",
                    message_type=file_message_type,
                    file_name=file_name,
                    file_size=file_size,
                    mime_type=mime_type,
                    file_path=file_path,
                    sender_id=sender_id,
                    receiver_id=receiver_id
                )
                
                db.add(db_message)
                db.commit()
                db.refresh(db_message)
                
                # 构建文件响应数据
                file_response = {
                    "id": db_message.id,
                    "content": f"/download/{unique_filename}",
                    "message_type": file_message_type,
                    "file_name": file_name,
                    "file_size": file_size,
                    "mime_type": mime_type,
                    "sender_id": sender_id,
                    "sender_username": sender.username,
                    "receiver_id": receiver_id,
                    "timestamp": db_message.timestamp.isoformat() if db_message.timestamp else None,
                    "is_image": is_image
                }
                
                uploaded_files.append(file_response)
                print(f"✅ 文件保存成功: {file_name} ({file_size} bytes)")
                
            except Exception as e:
                print(f"❌ 处理文件 {file_info.get('file_name', 'unknown')} 时出错: {str(e)}")
                continue
        
        # 构建组合消息响应数据
        combined_response = {
            "text_content": text_content,
            "files": uploaded_files,
            "sender_id": sender_id,
            "sender_username": sender.username,
            "receiver_id": receiver_id,
            "message_type": message_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 发送WebSocket消息
        if receiver_id:
            # 私聊组合消息
            ws_message = {
                "type": "combined_message",
                "data": combined_response
            }
            await connection_manager.send_personal_json(ws_message, receiver_id)
            print(f"📨 私聊组合消息发送给用户 {receiver_id}")
        else:
            # 群聊组合消息
            ws_message = {
                "type": "combined_message",
                "data": combined_response
            }
            await connection_manager.broadcast_json(ws_message)
            print(f"📢 群聊组合消息广播给所有用户")
        
        # 同时给发送者发送确认消息
        confirmation_message = {
            "type": "message_sent",
            "data": {
                "delivered": True,
                "receiver_id": receiver_id,
                "content": text_content[:50] + "..." if text_content and len(text_content) > 50 else text_content,
                "message_type": "combined",
                "file_count": len(uploaded_files)
            }
        }
        await connection_manager.send_personal_json(confirmation_message, sender_id)
        
        return {
            "success": True,
            "message": "Combined message sent successfully",
            "data": combined_response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 发送组合消息失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to send combined message: {str(e)}")

# 文件上传接口
@app.post("/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    sender_id: int = Form(...),
    receiver_id: int = Form(None),
    message_type: str = Form("file"),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    上传文件
    """
    try:
        print(f"📤 收到文件上传请求: {file.filename}, 发送者: {sender_id}, 接收者: {receiver_id}")
        
        # 验证发送者
        sender = auth_service.get_user_by_id(sender_id)
        if not sender:
            raise HTTPException(status_code=404, detail="Sender not found")
        
        # 验证接收者（如果是私聊）
        if receiver_id:
            receiver = auth_service.get_user_by_id(receiver_id)
            if not receiver:
                raise HTTPException(status_code=404, detail="Receiver not found")
        
        # 确定文件类型
        if file.content_type and file.content_type.startswith('image/'):
            file_message_type = "image"
        else:
            file_message_type = "file"
        
        # 生成唯一文件名
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        
        # 保存到数据库
        db_message = Message(
            content=f"/download/{unique_filename}",  # 下载URL
            message_type=file_message_type,
            file_name=file.filename,
            file_size=file_size,
            mime_type=file.content_type,
            file_path=file_path,
            sender_id=sender_id,
            receiver_id=receiver_id
        )
        
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        
        # 构建响应数据
        response_data = {
            "id": db_message.id,
            "content": f"/download/{unique_filename}",
            "message_type": file_message_type,
            "file_name": file.filename,
            "file_size": file_size,
            "mime_type": file.content_type,
            "sender_id": sender_id,
            "sender_username": sender.username,
            "receiver_id": receiver_id,
            "timestamp": db_message.timestamp.isoformat() if db_message.timestamp else None
        }
        
        print(f"✅ 文件上传成功: {file.filename}, 大小: {file_size} 字节")
        
        # 发送WebSocket消息
        if receiver_id:
            # 私聊文件消息
            ws_message = {
                "type": "file_message",
                "data": response_data
            }
            await connection_manager.send_personal_json(ws_message, receiver_id)
            print(f"📨 私聊文件消息发送给用户 {receiver_id}")
        else:
            # 群聊文件消息
            ws_message = {
                "type": "file_message",
                "data": response_data
            }
            await connection_manager.broadcast_json(ws_message)
            print(f"📢 群聊文件消息广播给所有用户")
        
        return {
            "success": True,
            "message": "File uploaded successfully",
            "data": response_data
        }
        
    except Exception as e:
        print(f"❌ 文件上传失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

# 文件下载接口
@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载文件
    """
    try:
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # 从数据库获取文件信息
        db = SessionLocal()
        try:
            message = db.query(Message).filter(Message.file_path == file_path).first()
            if message:
                return FileResponse(
                    path=file_path,
                    filename=message.file_name,
                    media_type=message.mime_type or "application/octet-stream"
                )
            else:
                return FileResponse(
                    path=file_path,
                    filename=filename,
                    media_type="application/octet-stream"
                )
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ 文件下载失败: {e}")
        raise HTTPException(status_code=500, detail=f"File download failed: {str(e)}")

@app.get("/")
async def root():
    """
    根路径
    """
    return {
        "message": "Multi Instant Message System API", 
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/users", response_model=dict)
async def get_users(db: Session = Depends(get_db)):
    """
    获取所有用户列表
    """
    users = db.query(User).all()
    return {
        "users": [
            {
                "id": u.id, 
                "username": u.username, 
                "email": u.email,
                "status": u.status,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_seen": u.last_seen.isoformat() if u.last_seen else None
            } for u in users
        ]
    }

@app.get("/users/{user_id}", response_model=dict)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    获取特定用户信息
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "status": user.status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_seen": user.last_seen.isoformat() if user.last_seen else None
    }

@app.get("/messages", response_model=dict)
async def get_messages(
    db: Session = Depends(get_db), 
    limit: int = 50,
    user_id: int = None
):
    """
    获取消息列表
    """
    query = db.query(Message)
    
    # 如果指定了用户ID，只获取该用户发送或接收的消息
    if user_id:
        query = query.filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        )
    
    messages = query.order_by(Message.timestamp.desc()).limit(limit).all()
    
    return {
        "messages": [
            {
                "id": m.id,
                "content": m.content,
                "message_type": m.message_type,
                "file_name": m.file_name,
                "file_size": m.file_size,
                "mime_type": m.mime_type,
                "sender_id": m.sender_id,
                "sender_username": m.sender.username if m.sender else "Unknown",
                "receiver_id": m.receiver_id,
                "receiver_username": m.receiver.username if m.receiver else None,
                "group_id": m.group_id,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "is_read": m.is_read
            } for m in reversed(messages)
        ]
    }

@app.get("/messages/{message_id}", response_model=dict)
async def get_message(message_id: int, db: Session = Depends(get_db)):
    """
    获取特定消息
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {
        "id": message.id,
        "content": message.content,
        "message_type": message.message_type,
        "file_name": message.file_name,
        "file_size": message.file_size,
        "mime_type": message.mime_type,
        "sender_id": message.sender_id,
        "sender_username": message.sender.username if message.sender else "Unknown",
        "receiver_id": message.receiver_id,
        "receiver_username": message.receiver.username if message.receiver else None,
        "group_id": message.group_id,
        "timestamp": message.timestamp.isoformat() if message.timestamp else None,
        "is_read": message.is_read
    }

@app.post("/messages/{message_id}/read", response_model=dict)
async def mark_message_as_read(message_id: int, db: Session = Depends(get_db)):
    """
    标记消息为已读
    """
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.is_read = True
    db.commit()
    
    return {"message": "Message marked as read", "message_id": message_id}

@app.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "service": "Multi Instant Message System"
    }

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    """
    获取系统统计信息
    """
    total_users = db.query(User).count()
    total_messages = db.query(Message).count()
    online_users = db.query(User).filter(User.status == "online").count()
    
    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "online_users": online_users,
        "offline_users": total_users - online_users
    }

# WebSocket 路由
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket 连接端点
    """
    db = SessionLocal()
    try:
        # 首先接受WebSocket连接
        await websocket.accept()
        print(f"🔗 WebSocket连接已接受，用户ID: {user_id}")
        
        auth_service = AuthService(db)
        user = auth_service.get_user_by_id(user_id)
        
        if not user:
            print(f"❌ 用户 {user_id} 不存在，拒绝连接")
            await websocket.close(code=1008, reason="User not found")
            return
        
        # 更新用户状态为在线
        if not auth_service.update_user_status(user.id, "online"):
            print(f"❌ 无法更新用户 {user.username} 状态")
            await websocket.close(code=1008, reason="User status update failed")
            return
        
        print(f"✅ 用户 {user.username} (ID: {user.id}) 验证成功")
        
        # 连接到连接管理器
        await connection_manager.connect(websocket, user)
        print(f"🔗 用户 {user.username} WebSocket 连接成功，当前活跃连接: {len(connection_manager.active_connections)}")
        print(f"🔗 当前所有活跃连接用户ID: {list(connection_manager.active_connections.keys())}")
        
        # 添加心跳检测
        try:
            while True:
                data = await websocket.receive_json()
                print(f"📨 收到WebSocket消息: {data}")
                message = WSMessage(**data)
                
                # 处理不同类型的消息
                if message.type == WSMessageTypes.MESSAGE_SEND:
                    await connection_manager.handle_message_send(message, user, db)
                elif message.type == WSMessageTypes.TYPING_START:
                    await connection_manager.broadcast_typing(user.id, True)
                elif message.type == WSMessageTypes.TYPING_STOP:
                    await connection_manager.broadcast_typing(user.id, False)
                elif message.type == "ping":
                    # 响应心跳包
                    await websocket.send_json({
                        "type": "pong",
                        "data": {"timestamp": asyncio.get_event_loop().time()}
                    })
                    print(f"💓 心跳响应发送给用户 {user.username}")
                else:
                    print(f"⚠️  未知消息类型: {message.type}")
                    
        except WebSocketDisconnect:
            print(f"🔌 用户 {user.username} WebSocket 断开连接")
            connection_manager.disconnect(user)
            await connection_manager.broadcast_user_status(user, "offline")
            
            # 更新用户状态为离线
            auth_service.update_user_status(user.id, "offline")
            
        except Exception as e:
            print(f"❌ WebSocket 处理错误: {e}")
            import traceback
            traceback.print_exc()
            connection_manager.disconnect(user)
            await connection_manager.broadcast_user_status(user, "offline")
            auth_service.update_user_status(user.id, "offline")
                
    except Exception as e:
        print(f"❌ WebSocket 连接错误: {e}")
        import traceback
        traceback.print_exc()
        try:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")
        except:
            pass
    finally:
        db.close()

# 新增API端点：获取在线用户
@app.get("/online-users", response_model=dict)
async def get_online_users(db: Session = Depends(get_db)):
    """
    获取在线用户列表
    """
    auth_service = AuthService(db)
    online_users = auth_service.get_online_users()
    
    return {
        "online_users": [
            {
                "id": user.id,
                "username": user.username,
                "status": user.status,
                "last_seen": user.last_seen.isoformat() if user.last_seen else None
            }
            for user in online_users
        ]
    }

# 新增API端点：用户登出
@app.post("/logout/{user_id}", response_model=dict)
async def logout(user_id: int, db: Session = Depends(get_db)):
    """
    用户登出
    """
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if auth_service.update_user_status(user.id, "offline"):
        return {
            "message": "Logout successful",
            "user_id": user_id,
            "username": user.username
        }
    else:
        raise HTTPException(status_code=500, detail="Logout failed")

# 新增API端点：检查用户状态
@app.get("/user-status/{user_id}", response_model=dict)
async def get_user_status(user_id: int, db: Session = Depends(get_db)):
    """
    获取用户状态
    """
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "status": user.status,
        "last_seen": user.last_seen.isoformat() if user.last_seen else None
    }

# 新增API端点：获取WebSocket连接状态
@app.get("/websocket-status", response_model=dict)
async def get_websocket_status():
    """
    获取WebSocket连接状态
    """
    return {
        "active_connections": len(connection_manager.active_connections),
        "connected_users": list(connection_manager.active_connections.keys()),
        "user_status": connection_manager.user_status
    }

# 启动事件
@app.on_event("startup")
async def startup_event():
    """
    应用启动时执行
    """
    print("🚀 Multi Instant Message System 服务器启动中...")
    print(f"🌐 服务器地址: http://{settings.SERVER_HOST}:{settings.SERVER_PORT}")
    print(f"📊 数据库: {settings.DATABASE_URL}")
    
    # 检查数据库连接和表
    db = SessionLocal()
    try:
        users_count = db.query(User).count()
        messages_count = db.query(Message).count()
        print(f"📈 数据库状态: {users_count} 用户, {messages_count} 消息")
        
        # 重置所有用户状态为离线
        online_users = db.query(User).filter(User.status == "online").all()
        for user in online_users:
            user.status = "offline"
        db.commit()
        print(f"🔄 重置 {len(online_users)} 个在线用户状态为离线")
        
        # 确保上传目录存在
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        print(f"📁 上传目录已创建: {UPLOAD_DIR}")
        
    except Exception as e:
        print(f"⚠️  数据库检查警告: {e}")
    finally:
        db.close()
    
    print("✅ 服务器启动完成！")

@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时执行
    """
    print("🛑 服务器正在关闭...")
    
    # 将所有在线用户状态设置为离线
    db = SessionLocal()
    try:
        online_users = db.query(User).filter(User.status == "online").all()
        for user in online_users:
            user.status = "offline"
        db.commit()
        print(f"✅ 已更新 {len(online_users)} 个在线用户状态为离线")
    except Exception as e:
        print(f"❌ 关闭时更新用户状态失败: {e}")
    finally:
        db.close()
    
    print("👋 服务器已关闭")

# 错误处理
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"message": "Resource not found", "path": str(request.url)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )

# 主程序入口
if __name__ == "__main__":
    print("🚀 启动 Multi Instant Message System 服务器...")
    print(f"📁 项目根目录: {project_root}")
    print(f"🔧 配置: host={settings.SERVER_HOST}, port={settings.SERVER_PORT}")
    
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True,
        log_level="info"
    )