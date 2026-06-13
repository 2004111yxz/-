import requests
import json

# 直接测试上游API
api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "https://api.deepseek.com/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Count from 1 to 3"}],
    "stream": True
}

print("Testing upstream API streaming...")
print("-" * 50)

try:
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=data,
        stream=True,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print("\nFirst few lines of response:")
    print("-" * 50)
    
    count = 0
    for line in response.iter_lines():
        if line:
            line_text = line.decode('utf-8')
            print(line_text[:100])  # 只显示前100个字符
            count += 1
            if count >= 10:  # 只显示前10行
                print("...")
                break
    
    print("-" * 50)
    print("Upstream streaming test complete!")
    
except Exception as e:
    print(f"Error: {str(e)}")