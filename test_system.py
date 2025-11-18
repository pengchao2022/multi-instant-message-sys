#!/usr/bin/env python3
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client.main import ChatClient

async def test_multiple_clients():
    """测试多个客户端同时运行"""
    clients = []
    
    # 创建3个测试客户端
    for i in range(1, 4):
        client = ChatClient("ws://localhost:8000")
        clients.append(client)
        try:
            await client.connect(i, f"User{i}")
            print(f"✅ 客户端 {i} 连接成功")
            # 发送测试消息
            await client.send_message(f"大家好，我是User{i}！")
        except Exception as e:
            print(f"❌ 客户端 {i} 连接失败: {e}")
    
    # 等待消息传递
    print("\n⏳ 等待消息传递...")
    await asyncio.sleep(3)
    
    # 断开所有客户端
    for client in clients:
        await client.disconnect()
    
    print("🎉 测试完成！")

if __name__ == "__main__":
    print("🚀 启动系统测试...")
    asyncio.run(test_multiple_clients())