import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)

# 检查 logs 表结构
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(logs)")
columns = cursor.fetchall()

print("logs 表结构:")
for col in columns:
    print(f"列名: {col[1]}, 类型: {col[2]}, 是否非空: {col[3]}, 默认值: {col[4]}")

conn.close()