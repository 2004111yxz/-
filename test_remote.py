import requests

api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "https://zhong-zhuan-zhen.onrender.com/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}]
}

try:
    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=30)
    print("Status:", response.status_code)
    print("Response:", response.text)
except Exception as e:
    print("Error:", str(e))