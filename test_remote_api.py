import requests

# 测试远程服务器的API调用
api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "https://zhong-zhuan-zhen.onrender.com/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello, how are you?"}]
}

try:
    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=30)
    print("状态码:", response.status_code)
    print("响应:", response.text[:500])
except Exception as e:
    print("错误:", str(e))