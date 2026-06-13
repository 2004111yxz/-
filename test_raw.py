import requests

api_key = "sk-4b7824c8ca9d4292a33576dd12c06fea"
base_url = "http://127.0.0.1:5000/v1"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

data = {
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": True
}

print("Sending streaming request...")
try:
    response = requests.post(
        f"{base_url}/chat/completions",
        headers=headers,
        json=data,
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    print(f"Response text: '{response.text}'")
    print(f"Response text length: {len(response.text)}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()