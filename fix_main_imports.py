#!/usr/bin/env python3
"""
修复 main.py 中的导入路径
"""
import re

def fix_imports():
    with open('server/src/main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复导入路径 - 移除 src 和 server 前缀
    replacements = [
        ('from src.shared.protocols', 'from shared.protocols'),
        ('from server.models.user', 'from models.user'),
        ('from server.services.auth_service', 'from services.auth_service'),
        ('from server.connection_manager', 'from connection_manager'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    # 写入修复后的内容
    with open('server/src/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已修复导入路径")

fix_imports()
