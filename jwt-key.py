import secrets

# 生成32字节的随机密钥（256位）
secret_key = secrets.token_urlsafe(32)
print(f"SECRET_KEY={secret_key}")