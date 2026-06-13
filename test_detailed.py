import requests
import json
import traceback

api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "http://127.0.0.1:5000/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Count from 1 to 3"}],
    "stream": True
}

print("Testing streaming with detailed error tracking...")
print("-" * 50)

try:
    print("Sending request...")
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=data,
        stream=True,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    # 检查响应内容
    content = b""
    for chunk in response.iter_content(chunk_size=1024):
        if chunk:
            content += chunk
            print(f"Received chunk: {chunk[:100]}...")
    
    print(f"\nFull response content: {content[:500]}")
    
except Exception as e:
    print(f"Error: {str(e)}")
    print(traceback.format_exc())