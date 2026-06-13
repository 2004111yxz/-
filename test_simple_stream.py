import requests

# 直接测试我们服务器的流式端点
api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "http://127.0.0.1:5000/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Count to 3"}],
    "stream": True
}

print("Testing streaming with curl-like output...")
response = requests.post(
    f"{base_url}/chat/completions",
    headers=headers,
    json=data,
    stream=True,
    timeout=30
)

print(f"\nStatus Code: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
print("\nResponse Body:")
print("-" * 60)

# 读取并显示响应
try:
    # 尝试读取原始内容
    content = response.content.decode('utf-8')
    print(content[:500])
except Exception as e:
    print(f"Error reading content: {e}")
    
print("-" * 60)