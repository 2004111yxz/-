import requests

# 测试登录和查看日志
base_url = "http://127.0.0.1:5000"

# 先登录
login_data = {
    'username': 'MoRan',
    'password': 'yangyang'
}

session = requests.Session()
response = session.post(f"{base_url}/login", data=login_data)
print("登录状态:", response.status_code)

# 查看日志页面
response = session.get(f"{base_url}/logs")
print("日志页面状态:", response.status_code)
print("页面内容预览:", response.text[:500])