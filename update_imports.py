import os
import re

def update_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 更新导入路径
    updated_content = content.replace(
        'from shared.protocols', 'from src.shared.protocols'
    ).replace(
        'from config.config', 'from config.config'
    ).replace(
        'from models.', 'from src.models.'
    ).replace(
        'from services.', 'from src.services.'
    ).replace(
        'from database', 'from src.database'
    ).replace(
        'from connection_manager', 'from src.connection_manager'
    )
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

# 更新服务器端文件
server_files = [
    'server/src/main.py',
    'server/src/connection_manager.py',
    'server/src/database.py',
    'server/src/models/user.py',
    'server/src/services/auth_service.py'
]

for file in server_files:
    if os.path.exists(file):
        print(f"更新文件: {file}")
        update_imports(file)
    else:
        print(f"文件不存在: {file}")
