import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 查看模型配置
cursor.execute("SELECT * FROM models")
models = cursor.fetchall()
print("模型配置:")
for model in models:
    print(f"ID: {model[0]}")
    print(f"名称: {model[1]}")
    print(f"显示名: {model[2]}")
    print(f"基础URL: {model[3]}")
    print(f"API密钥: {model[4]}")
    print(f"输入价格: {model[5]}")
    print(f"输出价格: {model[6]}")
    print(f"状态: {'启用' if model[8] == 1 else '禁用'}")
    print()

conn.close()