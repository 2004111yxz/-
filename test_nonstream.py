import requests

api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "http://127.0.0.1:5000/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# 不带 stream 参数
data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
}

print("Testing non-streaming request...")
response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=30)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:200]}")