import sys
sys.path.insert(0, r'f:\真 中转站')

from app import app, stream_response, get_db, fetch_one
import json

# 创建测试上下文
with app.test_request_context():
    # 获取数据库连接
    conn = get_db()
    
    # 获取用户信息
    api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
    key_info = fetch_one(conn, "SELECT * FROM api_keys WHERE key = ?", (api_key,))
    
    if key_info:
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (key_info['user_id'],))
        model_cfg = fetch_one(conn, "SELECT * FROM models WHERE name = ?", ('deepseek-chat',))
        
        if user and model_cfg:
            print(f"User: {user['username']}, Balance: {user['balance']}")
            print(f"Model: {model_cfg['name']}, Base URL: {model_cfg['base_url']}")
            
            # 测试流式响应
            body = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            }
            
            print("\nCalling stream_response...")
            result = stream_response(conn, user, model_cfg, body)
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")
        else:
            print("User or model not found")
    else:
        print("API key not found")
    
    conn.close()