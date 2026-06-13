import requests
import traceback

api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "https://api.deepseek.com/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

# 测试1: 带stream参数
print("Test 1: Streaming request to upstream")
data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": True
}

try:
    response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, stream=True, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    
    # 尝试读取第一行
    for i, line in enumerate(response.iter_lines()):
        if i >= 3:
            break
        print(f"Line {i}: {line.decode('utf-8')[:100]}")
except Exception as e:
    print(f"Error: {e}")
    print(traceback.format_exc())