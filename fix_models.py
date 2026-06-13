import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 启用所有模型
cursor.execute("UPDATE models SET status = 1")

# 更新模型配置，移除中文密钥
cursor.execute("UPDATE models SET api_key = 'sk-your-openai-key-here' WHERE name = 'gpt-3.5-turbo'")
cursor.execute("UPDATE models SET api_key = 'sk-your-deepseek-key-here' WHERE name = 'deepseek-chat'")

conn.commit()

# 查看更新后的模型配置
cursor.execute("SELECT * FROM models")
models = cursor.fetchall()
print("更新后的模型配置:")
for model in models:
    print(f"名称: {model[1]}, 状态: {'启用' if model[8] == 1 else '禁用'}, API密钥: {model[4]}")

conn.close()