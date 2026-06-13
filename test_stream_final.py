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
    "messages": [{"role": "user", "content": "Say 'hello' in one word"}],
    "stream": True
}

print("Testing streaming with full response...")
try:
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=data,
        stream=True,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'N/A')}")
    print("\nStreaming response:")
    print("-" * 60)
    
    # 读取所有内容
    full_text = ""
    for line in response.iter_lines():
        if line:
            line_text = line.decode('utf-8')
            print(line_text)
            
            # 提取文本内容
            if line_text.startswith('data: '):
                data_str = line_text[6:].strip()
                if data_str and data_str != '[DONE]':
                    try:
                        chunk = json.loads(data_str)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            delta = chunk['choices'][0].get('delta', {})
                            if 'content' in delta:
                                full_text += delta['content']
                    except:
                        pass
    
    print("-" * 60)
    print(f"\nFull response: {full_text}")
    print("SUCCESS! Streaming is working!")
    
except Exception as e:
    print(f"Error: {e}")