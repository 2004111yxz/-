import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

cursor = conn.cursor()

# 检查密钥
api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
cursor.execute("SELECT * FROM api_keys WHERE key = ?", (api_key,))
key_info = cursor.fetchone()

if key_info:
    print(f"Key found: {key_info['key'][:20]}...")
    print(f"User ID: {key_info['user_id']}")
    print(f"Status: {key_info['status']}")
    
    # 检查用户
    cursor.execute("SELECT * FROM users WHERE id = ?", (key_info['user_id'],))
    user = cursor.fetchone()
    
    if user:
        print(f"\nUser: {user['username']}")
        print(f"Balance: {user['balance']}")
        print(f"Status: {user['status']}")
    
    # 检查模型
    cursor.execute("SELECT * FROM models WHERE name = 'deepseek-chat'")
    model = cursor.fetchone()
    
    if model:
        print(f"\nModel: {model['name']}")
        print(f"Base URL: {model['base_url']}")
        print(f"API Key: {model['api_key'][:20]}...")
        print(f"Status: {model['status']}")
else:
    print("Key not found!")

conn.close()