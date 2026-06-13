import requests

# 测试非流式请求来对比
api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "http://127.0.0.1:5000/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# 测试1: 非流式请求
print("Test 1: Non-streaming request")
data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
}
response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=30)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")
print()

# 测试2: 流式请求
print("Test 2: Streaming request")
data["stream"] = True
response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=30)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('Content-Type')}")
print(f"Response: {response.text[:200]}")