import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)

# 模拟日志查询
user_id = 1  # 管理员用户ID

# 查询日志
cursor = conn.cursor()
cursor.execute("SELECT * FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 50", (user_id,))
rows = cursor.fetchall()
columns = [desc[0] for desc in cursor.description]
results = [dict(zip(columns, row)) for row in rows]

print(f"用户 {user_id} 的调用记录:")
print(f"共 {len(results)} 条记录")
for log in results:
    print(f"ID: {log['id']}, 模型: {log['model']}, 输入Token: {log['prompt_tokens']}, 输出Token: {log['completion_tokens']}, 费用: {log['cost']}")

conn.close()