import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# 检查用户信息
print("=== 用户信息 ===")
cursor = conn.cursor()
cursor.execute("SELECT * FROM users")
users = cursor.fetchall()
for user in users:
    print(f"用户ID: {user['id']}, 用户名: {user['username']}, 余额: {user['balance']}")

# 检查API密钥
print("\n=== API密钥 ===")
cursor.execute("SELECT * FROM api_keys")
keys = cursor.fetchall()
for key in keys:
    print(f"密钥ID: {key['id']}, 用户ID: {key['user_id']}, 密钥: {key['key'][:20]}..., 状态: {key['status']}")

# 检查调用记录
print("\n=== 调用记录 ===")
cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 10")
logs = cursor.fetchall()
if logs:
    for log in logs:
        print(f"日志ID: {log['id']}, 用户ID: {log['user_id']}, 模型: {log['model']}, 费用: {log['cost']}, 时间: {log['created_at']}")
else:
    print("暂无调用记录")

conn.close()