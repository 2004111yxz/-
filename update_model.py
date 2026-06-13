import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 更新 DeepSeek 模型的 API 密钥（使用用户提供的密钥）
api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
cursor.execute("UPDATE models SET api_key = ?, status = 1 WHERE name = 'deepseek-chat'", (api_key,))
conn.commit()

print("DeepSeek 模型已更新")

# 查看更新后的配置
cursor.execute("SELECT name, api_key, status FROM models WHERE name = 'deepseek-chat'")
model = cursor.fetchone()
print(f"模型: {model[0]}, 密钥: {model[1][:10]}..., 状态: {'启用' if model[2] == 1 else '禁用'}")

conn.close()