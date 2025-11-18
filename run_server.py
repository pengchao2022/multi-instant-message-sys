#!/usr/bin/env python3
import uvicorn
import sys
import os

# 添加必要的路径到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)  # 项目根目录
sys.path.insert(0, os.path.join(current_dir, "server", "src"))  # server/src 目录

if __name__ == "__main__":
    print("🚀 启动即时消息系统服务器...")
    
    # 直接运行 uvicorn，指定正确的模块路径
    uvicorn.run(
        "main:app",  # 从 server/src/main.py 导入
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
