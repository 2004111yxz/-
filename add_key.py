import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 添加用户提供的密钥
api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"

# 检查是否已存在
cursor.execute("SELECT * FROM api_keys WHERE key = ?", (api_key,))
if cursor.fetchone():
    print("密钥已存在")
else:
    # 添加新密钥到管理员用户（ID=1）
    cursor.execute("INSERT INTO api_keys (user_id, key, name, status, created_at) VALUES (?, ?, ?, ?, ?)",
                  (1, api_key, "用户密钥", 1, "2024-01-01 00:00:00"))
    conn.commit()
    print("密钥已添加")

# 检查用户余额
cursor.execute("SELECT balance FROM users WHERE id = 1")
user = cursor.fetchone()
if user:
    print(f"当前余额: ¥{user[0]}")

conn.close()