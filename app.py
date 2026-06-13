from flask import Flask, request, render_template_string, session, redirect, url_for
import sqlite3
import hashlib
import uuid
import requests
import time
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your-secret-key-change-it"  # 部署前修改
DB_PATH = "platform.db"

# ===================== 数据库初始化 =====================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  balance REAL DEFAULT 0,
                  is_admin INTEGER DEFAULT 0,
                  created_at TEXT)''')
    
    # 卡密表
    c.execute('''CREATE TABLE IF NOT EXISTS cards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT UNIQUE NOT NULL,
                  amount REAL NOT NULL,
                  status INTEGER DEFAULT 0,
                  used_by INTEGER,
                  used_at TEXT,
                  created_at TEXT)''')
    
    # 调用记录表
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  model TEXT,
                  prompt_tokens INTEGER,
                  completion_tokens INTEGER,
                  cost REAL,
                  created_at TEXT)''')
    
    # 模型配置表
    c.execute('''CREATE TABLE IF NOT EXISTS models
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  base_url TEXT NOT NULL,
                  api_key TEXT NOT NULL,
                  price_per_1k REAL NOT NULL,
                  status INTEGER DEFAULT 1)''')
    
    # 创建默认管理员 admin/admin123
    try:
        pwd = hashlib.md5("admin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username,password,is_admin,created_at) VALUES (?,?,?,?)",
                  ("admin", pwd, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except:
        pass
    
    # 添加默认模型示例（可在后台修改）
    try:
        c.execute("INSERT INTO models (name,base_url,api_key,price_per_1k) VALUES (?,?,?,?)",
                  ("gpt-3.5-turbo", "https://api.openai.com/v1", "sk-your-key", 0.01))
    except:
        pass
    
    conn.commit()
    conn.close()

# ===================== 工具函数 =====================
def md5(s):
    return hashlib.md5(s.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required():
    return 'user_id' in session

def admin_required():
    return session.get('is_admin', 0) == 1

# ===================== 前端页面 =====================
INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>AI Token 平台</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:Arial;background:#f5f7fa;min-height:100vh}
        .nav{background:#2c3e50;color:white;padding:15px;display:flex;justify-content:space-between;align-items:center}
        .container{max-width:800px;margin:30px auto;padding:20px}
        .card{background:white;border-radius:12px;padding:25px;box-shadow:0 2px 10px rgba(0,0,0,0.1);margin-bottom:20px}
        h1,h2{color:#2c3e50;margin-bottom:20px}
        input,button{padding:12px 18px;border-radius:8px;font-size:14px}
        input{border:1px solid #ddd;width:100%;margin-bottom:10px}
        button{background:#3498db;color:white;border:none;cursor:pointer;width:100%}
        button:hover{background:#2980b9}
        .balance{font-size:32px;font-weight:bold;color:#27ae60}
        .tip{color:#7f8c8d;font-size:13px;margin:10px 0}
        table{width:100%;border-collapse:collapse;margin-top:15px}
        th,td{padding:10px;text-align:left;border-bottom:1px solid #eee}
        .tabs{display:flex;gap:10px;margin-bottom:20px}
        .tab{padding:10px 20px;background:#ecf0f1;border-radius:8px;cursor:pointer}
        .tab.active{background:#3498db;color:white}
        a{color:#3498db;text-decoration:none}
    </style>
</head>
<body>
    <div class="nav">
        <h3 style="color:white">🚀 AI Token 平台</h3>
        <div>
            {% if user %}
                <span>{{ user.username }}</span>
                <a href="/logout" style="color:white;margin-left:15px">退出</a>
            {% else %}
                <a href="/login" style="color:white">登录</a>
            {% endif %}
        </div>
    </div>
    <div class="container">
        {% if not user %}
        <div class="card">
            <h2>登录</h2>
            <form method="post" action="/login">
                <input name="username" placeholder="用户名" required>
                <input name="password" type="password" placeholder="密码" required>
                <button type="submit">登录</button>
            </form>
            <div class="tip">没有账号？<a href="/register">立即注册</a></div>
        </div>
        {% else %}
        <div class="card">
            <h2>我的账户</h2>
            <div class="balance">¥ {{ "%.2f"|format(user.balance) }}</div>
            <div class="tip">剩余额度，可用于调用所有 AI 模型</div>
        </div>
        
        <div class="card">
            <h2>卡密充值</h2>
            <form method="post" action="/recharge">
                <input name="code" placeholder="输入充值卡密" required>
                <button type="submit">立即充值</button>
            </form>
        </div>
        
        <div class="card">
            <h2>API 使用信息</h2>
            <p><strong>接口地址：</strong>{{ request.host_url }}v1/chat/completions</p>
            <p><strong>API Key：</strong>sk-{{ user.id }}-{{ user.username }}</p>
            <div class="tip">兼容 OpenAI 格式，直接替换 base_url 和 key 即可使用</div>
        </div>
        
        <div class="card">
            <h2>调用记录</h2>
            <table>
                <tr><th>模型</th><th>消耗Token</th><th>费用</th><th>时间</th></tr>
                {% for log in logs %}
                <tr>
                    <td>{{ log.model }}</td>
                    <td>{{ log.prompt_tokens + log.completion_tokens }}</td>
                    <td>¥ {{ "%.4f"|format(log.cost) }}</td>
                    <td>{{ log.created_at }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>管理后台</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:Arial;background:#f5f7fa}
        .nav{background:#2c3e50;color:white;padding:15px}
        .container{max-width:1000px;margin:20px auto;padding:20px}
        .card{background:white;border-radius:12px;padding:25px;box-shadow:0 2px 10px rgba(0,0,0,0.1);margin-bottom:20px}
        h2{color:#2c3e50;margin-bottom:15px}
        input,button,select{padding:10px 15px;border-radius:8px;font-size:14px}
        input{border:1px solid #ddd;margin-right:10px}
        button{background:#27ae60;color:white;border:none;cursor:pointer}
        table{width:100%;border-collapse:collapse;margin-top:15px}
        th,td{padding:10px;text-align:left;border-bottom:1px solid #eee}
        .tabs{display:flex;gap:10px;margin-bottom:20px}
        .tab{padding:10px 20px;background:#ecf0f1;border-radius:8px;cursor:pointer}
        .tab.active{background:#3498db;color:white}
    </style>
</head>
<body>
    <div class="nav"><h2>⚙️ 管理后台</h2></div>
    <div class="container">
        <div class="card">
            <h2>生成充值卡密</h2>
            <form method="post" action="/admin/card">
                <input name="amount" type="number" step="0.01" placeholder="面额（元）" required>
                <input name="count" type="number" value="1" placeholder="生成数量">
                <button type="submit">生成</button>
            </form>
            {% if new_cards %}
            <div style="margin-top:15px">
                <p>生成成功！共 {{ new_cards|length }} 张：</p>
                <textarea style="width:100%;height:150px;margin-top:10px;padding:10px">{% for c in new_cards %}{{ c }}
{% endfor %}</textarea>
            </div>
            {% endif %}
        </div>
        
        <div class="card">
            <h2>用户列表</h2>
            <table>
                <tr><th>ID</th><th>用户名</th><th>余额</th><th>注册时间</th></tr>
                {% for u in users %}
                <tr>
                    <td>{{ u.id }}</td>
                    <td>{{ u.username }}</td>
                    <td>¥ {{ "%.2f"|format(u.balance) }}</td>
                    <td>{{ u.created_at }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        
        <div class="card">
            <h2>模型配置</h2>
            <table>
                <tr><th>模型名</th><th>上游地址</th><th>单价/千token</th><th>状态</th></tr>
                {% for m in models %}
                <tr>
                    <td>{{ m.name }}</td>
                    <td>{{ m.base_url }}</td>
                    <td>¥ {{ m.price_per_1k }}</td>
                    <td>{{ "启用" if m.status else "禁用" }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>
</body>
</html>
"""

# ===================== 页面路由 =====================
@app.route('/')
def index():
    user = None
    logs = []
    if login_required():
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
        logs = conn.execute("SELECT * FROM logs WHERE user_id=? ORDER BY id DESC LIMIT 20", (session['user_id'],)).fetchall()
        conn.close()
    return render_template_string(INDEX_HTML, user=user, logs=logs)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = md5(request.form['password'])
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username,password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('index'))
        return "用户名或密码错误"
    return redirect(url_for('index'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = md5(request.form['password'])
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username,password,balance,created_at) VALUES (?,?,0,?)",
                        (username, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
        except:
            return "用户名已存在"
    return '''
    <div style="max-width:400px;margin:100px auto;background:white;padding:30px;border-radius:12px">
        <h2>注册</h2>
        <form method="post">
            <input name="username" placeholder="用户名" required style="width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:8px">
            <input name="password" type="password" placeholder="密码" required style="width:100%;padding:12px;margin:10px 0;border:1px solid #ddd;border-radius:8px">
            <button type="submit" style="width:100%;padding:12px;background:#3498db;color:white;border:none;border-radius:8px">注册</button>
        </form>
    </div>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/recharge', methods=['POST'])
def recharge():
    if not login_required():
        return redirect(url_for('index'))
    code = request.form['code'].strip()
    conn = get_db()
    card = conn.execute("SELECT * FROM cards WHERE code=? AND status=0", (code,)).fetchone()
    if not card:
        conn.close()
        return "卡密无效或已使用"
    conn.execute("UPDATE cards SET status=1, used_by=?, used_at=? WHERE id=?",
                (session['user_id'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), card['id']))
    conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (card['amount'], session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# ===================== 管理后台 =====================
@app.route('/admin')
def admin():
    if not admin_required():
        return "无权限"
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    models = conn.execute("SELECT * FROM models").fetchall()
    conn.close()
    return render_template_string(ADMIN_HTML, users=users, models=models, new_cards=[])

@app.route('/admin/card', methods=['POST'])
def admin_card():
    if not admin_required():
        return "无权限"
    amount = float(request.form['amount'])
    count = int(request.form.get('count', 1))
    new_cards = []
    conn = get_db()
    for _ in range(count):
        code = str(uuid.uuid4()).replace('-','')[:16].upper()
        conn.execute("INSERT INTO cards (code,amount,created_at) VALUES (?,?,?)",
                    (code, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_cards.append(code)
    conn.commit()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    models = conn.execute("SELECT * FROM models").fetchall()
    conn.close()
    return render_template_string(ADMIN_HTML, users=users, models=models, new_cards=new_cards)

# ===================== 核心：API 中转 + 计费 =====================
@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    # 验证 API Key
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        return {"error": "无效的 API Key"}, 401
    
    # 解析用户ID（简化版，生产环境建议用独立key表）
    try:
        key_part = auth.replace('Bearer sk-','')
        user_id = int(key_part.split('-')[0])
    except:
        return {"error": "无效的 API Key"}, 401
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return {"error": "用户不存在"}, 401
    
    # 获取模型配置
    body = request.json
    model_name = body.get('model', 'gpt-3.5-turbo')
    model_cfg = conn.execute("SELECT * FROM models WHERE name=? AND status=1", (model_name,)).fetchone()
    if not model_cfg:
        conn.close()
        return {"error": f"模型 {model_name} 不可用"}, 400
    
    # 预扣费（按输入token估算，多退少补）
    est_cost = 0.01  # 预估最低费用
    if user['balance'] < est_cost:
        conn.close()
        return {"error": "余额不足，请充值"}, 402
    
    # 转发请求到上游
    try:
        resp = requests.post(
            f"{model_cfg['base_url']}/chat/completions",
            json=body,
            headers={
                'Authorization': f"Bearer {model_cfg['api_key']}",
                'Content-Type': 'application/json'
            },
            timeout=120
        )
        result = resp.json()
        
        # 计算实际费用
        prompt_tokens = result.get('usage', {}).get('prompt_tokens', 0)
        completion_tokens = result.get('usage', {}).get('completion_tokens', 0)
        total_tokens = prompt_tokens + completion_tokens
        cost = (total_tokens / 1000) * model_cfg['price_per_1k']
        
        # 结算扣费
        conn.execute("UPDATE users SET balance=balance-? WHERE id=?", (cost, user_id))
        conn.execute("INSERT INTO logs (user_id,model,prompt_tokens,completion_tokens,cost,created_at) VALUES (?,?,?,?,?,?)",
                    (user_id, model_name, prompt_tokens, completion_tokens, cost, 
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        return result, resp.status_code, {'Content-Type': 'application/json'}
    
    except Exception as e:
        conn.close()
        return {"error": str(e)}, 500

# ===================== 启动 =====================
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)