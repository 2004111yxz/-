import requests
import json

api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "http://127.0.0.1:5000/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Say 'hello'"}],
    "stream": True
}

print("Testing streaming with correct approach...")
print("-" * 60)

# 发送请求但不使用 stream=True，因为我们需要先让服务器处理请求
response = requests.post(
    f"{base_url}/chat/completions",
    headers=headers,
    json=data,
    timeout=30
)

print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
print()

if response.status_code == 200:
    print("Response content:")
    print(response.text[:500])
else:
    print(f"Error response: {response.text}")

print("-" * 60)