#!/usr/bin/env python3
"""
修复 main.py 底部的启动代码
"""
import re

def fix_main_bottom():
    with open('server/src/main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找并修复底部的启动代码
    old_pattern = r'uvicorn\.run\(\s*"server\.main:app"'
    new_code = 'uvicorn.run(\n        "main:app"'
    
    content = re.sub(old_pattern, new_code, content)
    
    # 写入修复后的内容
    with open('server/src/main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已修复启动代码")

fix_main_bottom()
