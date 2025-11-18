#!/usr/bin/env python3
import asyncio
import sys
import os
import requests

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from client.main import ChatClient

def print_help():
    """打印帮助信息"""
    print("=" * 50)
    print("多用户即时消息系统 - 客户端")
    print("=" * 50)
    print("可用命令:")
    print("  /help          - 显示帮助信息")
    print("  /users         - 显示在线用户")
    print("  /msg <id> <消息> - 发送私聊消息")
    print("  /status        - 显示连接状态")
    print("  /quit          - 退出程序")
    print("=" * 50)

def get_available_users(server_url: str = "http://localhost:8000"):
    """获取服务器上的可用用户"""
    try:
        response = requests.get(f"{server_url}/users")
        if response.status_code == 200:
            return response.json().get("users", [])
        else:
            print(f"❌ 获取用户列表失败: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ 无法连接到服务器: {e}")
        return []

async def interactive_client():
    """交互式客户端"""
    print_help()
    
    # 获取服务器地址
    server_url = input("请输入服务器地址 (默认: http://localhost:8000): ").strip()
    if not server_url:
        server_url = "http://localhost:8000"
    
    # 获取可用用户列表
    print("🔄 正在获取用户列表...")
    users = get_available_users(server_url)
    
    if users:
        print("\n📋 可用用户:")
        for user in users:
            print(f"  ID: {user['id']}, 用户名: {user['username']}, 状态: {user['status']}")
    else:
        print("❌ 无法获取用户列表，使用默认测试用户")
        users = [
            {"id": 1, "username": "alice", "status": "offline"},
            {"id": 2, "username": "bob", "status": "offline"},
            {"id": 3, "username": "charlie", "status": "offline"},
        ]
    
    # 选择用户
    while True:
        try:
            user_input = input("\n请选择用户ID (输入数字或输入 'new' 创建新用户): ").strip()
            
            if user_input.lower() == 'new':
                # 创建新用户
                new_username = input("请输入新用户名: ").strip()
                if not new_username:
                    print("❌ 用户名不能为空")
                    continue
                
                # 这里可以调用注册API
                print(f"⚠️  创建新用户功能需要服务器支持，暂时使用ID 99")
                user_id = 99
                username = new_username
                break
                
            else:
                user_id = int(user_input)
                # 查找用户
                selected_user = next((u for u in users if u["id"] == user_id), None)
                if selected_user:
                    username = selected_user["username"]
                    break
                else:
                    print(f"❌ 用户ID {user_id} 不存在，请重试")
                    
        except ValueError:
            print("❌ 请输入有效的数字或 'new'")
        except KeyboardInterrupt:
            print("\n👋 退出程序")
            return
    
    # WebSocket 地址
    ws_url = server_url.replace("http", "ws")
    
    # 创建客户端并连接
    client = ChatClient(ws_url)
    
    try:
        print(f"\n🔄 正在连接... 用户: {username} (ID: {user_id})")
        await client.connect(user_id, username)
        print(f"✅ 连接成功!")
        print("💬 输入消息开始聊天，输入 /help 查看帮助")
        
        # 消息输入循环
        while True:
            try:
                message = await asyncio.get_event_loop().run_in_executor(
                    None, input, f"[{username}] > "
                )
                
                if message.lower() in ['/quit', '/exit', '退出']:
                    break
                elif message.lower() == '/help':
                    print_help()
                elif message.lower() == '/users':
                    users = get_available_users(server_url)
                    if users:
                        print("\n📋 在线用户:")
                        online_users = [u for u in users if u['status'] == 'online']
                        offline_users = [u for u in users if u['status'] == 'offline']
                        
                        if online_users:
                            print("  🟢 在线:")
                            for user in online_users:
                                print(f"    ID: {user['id']}, 用户名: {user['username']}")
                        
                        if offline_users:
                            print("  ⚫ 离线:")
                            for user in offline_users:
                                print(f"    ID: {user['id']}, 用户名: {user['username']}")
                    else:
                        print("❌ 无法获取用户列表")
                elif message.lower() == '/status':
                    status = "🟢 已连接" if client.is_connected else "🔴 未连接"
                    print(f"📡 连接状态: {status}")
                    print(f"🌐 服务器: {ws_url}")
                    print(f"👤 用户: {username} (ID: {user_id})")
                elif message.startswith('/msg '):
                    parts = message.split(" ", 2)
                    if len(parts) == 3:
                        try:
                            receiver_id = int(parts[1])
                            content = parts[2]
                            success = await client.send_message(content, receiver_id=receiver_id)
                            if success:
                                print(f"📨 私聊消息已发送给用户 {receiver_id}")
                            else:
                                print("❌ 发送消息失败")
                        except ValueError:
                            print("❌ 错误: 用户ID必须是数字")
                    else:
                        print("❌ 用法: /msg <用户ID> <消息>")
                elif message.startswith('/'):
                    print("❌ 未知命令，输入 /help 查看帮助")
                else:
                    await client.send_message(message)
                    
            except KeyboardInterrupt:
                print("\n👋 正在退出...")
                break
            except Exception as e:
                print(f"❌ 错误: {e}")
                
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("💡 提示: 请确保服务器正在运行且用户ID有效")
    finally:
        await client.disconnect()
        print("✅ 客户端已断开连接")

def main():
    """主函数"""
    try:
        # 运行交互式客户端
        asyncio.run(interactive_client())
        
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序错误: {e}")

if __name__ == "__main__":
    main()