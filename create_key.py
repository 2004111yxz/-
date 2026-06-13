import sqlite3
import os
import uuid

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 为管理员用户创建一个新密钥
new_key = "sk-" + str(uuid.uuid4()).replace("-", "")
cursor.execute("INSERT INTO api_keys (user_id, key, name, status, created_at) VALUES (?, ?, ?, ?, ?)",
              (1, new_key, "测试密钥", 1, "2024-01-01 00:00:00"))

conn.commit()

print("新密钥已创建:")
print(f"API Key: {new_key}")

# 保存密钥到文件
with open("new_api_key.txt", "w") as f:
    f.write(new_key)

conn.close()