import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看用户和密钥
cursor.execute("SELECT u.username, a.key, a.status FROM users u JOIN api_keys a ON u.id = a.user_id")
results = cursor.fetchall()
print("用户和密钥列表:")
for row in results:
    print(f"用户: {row[0]}, 密钥: {row[1]}, 状态: {'启用' if row[2] == 1 else '禁用'}")

conn.close()