import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 强制启用所有模型
cursor.execute("UPDATE models SET status = 1 WHERE name = 'gpt-3.5-turbo'")
cursor.execute("UPDATE models SET status = 1 WHERE name = 'deepseek-chat'")

conn.commit()
print("已强制启用所有模型")

# 查看状态
cursor.execute("SELECT name, status FROM models")
models = cursor.fetchall()
for model in models:
    print(f"{model[0]}: {'启用' if model[1] == 1 else '禁用'}")

conn.close()