import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看所有模型
cursor.execute("SELECT * FROM models")
models = cursor.fetchall()
print("本地数据库模型列表:")
for model in models:
    print(f"ID: {model[0]}, 名称: {model[1]}, 显示名: {model[2]}, 状态: {'启用' if model[8] == 1 else '禁用'}")

conn.close()