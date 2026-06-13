import requests

api_key = "sk-371bbfda9100439d9f285a46038927c5"
base_url = "http://127.0.0.1:5000/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]  # 使用英文避免编码问题
}

try:
    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data)
    print("状态码:", response.status_code)
    print("响应:", response.text)
except Exception as e:
    print("错误:", str(e))