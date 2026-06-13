from flask import Flask, request, render_template_string, session, redirect, url_for, jsonify
import sqlite3
import hashlib
import uuid
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "moran-ai-platform-2024-secret"
DB_PATH = "/tmp/platform.db"

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
                  status INTEGER DEFAULT 1,
                  created_at TEXT)''')
    
    # API密钥表
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  key TEXT UNIQUE NOT NULL,
                  name TEXT DEFAULT '默认密钥',
                  status INTEGER DEFAULT 1,
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
    
    # 模型配置表
    c.execute('''CREATE TABLE IF NOT EXISTS models
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE NOT NULL,
                  display_name TEXT,
                  base_url TEXT NOT NULL,
                  api_key TEXT NOT NULL,
                  input_price REAL NOT NULL,
                  output_price REAL NOT NULL,
                  status INTEGER DEFAULT 1,
                  sort INTEGER DEFAULT 0)''')
    
    # 调用记录表
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  model TEXT,
                  prompt_tokens INTEGER DEFAULT 0,
                  completion_tokens INTEGER DEFAULT 0,
                  cost REAL DEFAULT 0,
                  created_at TEXT)''')
    
    # 创建管理员 MoRan / yangyang
    try:
        pwd = hashlib.md5("yangyang".encode()).hexdigest()
        c.execute("INSERT INTO users (username,password,is_admin,balance,status,created_at) VALUES (?,?,?,?,?,?)",
                  ("MoRan", pwd, 1, 9999.0, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # 给管理员生成默认密钥
        c.execute("INSERT INTO api_keys (user_id,key,name,created_at) VALUES (?,?,?,?)",
                  (1, "sk-" + str(uuid.uuid4()).replace("-",""), "管理员主密钥", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except:
        pass
    
    # 默认模型示例
    try:
        c.execute("INSERT INTO models (name,display_name,base_url,api_key,input_price,output_price,status) VALUES (?,?,?,?,?,?,?)",
                  ("gpt-3.5-turbo", "GPT-3.5-Turbo", "https://openai.api2d.net/v1", "fk-替换为你的密钥", 0.005, 0.015, 1))
    except:
        pass
    
    conn.commit()
    conn.close()

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

# ===================== 前端模板 =====================
USER_LAYOUT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Token 中转平台</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f2f5;min-height:100vh;color:#333}
        .layout{display:flex;min-height:100vh}
        .sidebar{width:220px;background:#001529;color:white;padding:20px 0;flex-shrink:0}
        .sidebar h2{text-align:center;padding:0 20px 20px;border-bottom:1px solid #1f3a5f;margin-bottom:10px}
        .menu-item{display:block;padding:12px 25px;color:#b8c5d1;text-decoration:none;transition:all 0.2s}
        .menu-item:hover,.menu-item.active{background:#1890ff;color:white}
        .main{flex:1;padding:24px;overflow-y:auto}
        .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}
        .card{background:white;border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin-bottom:20px}
        .card h3{margin-bottom:15px;color:#262626}
        .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:20px}
        .stat-card{background:white;border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.08)}
        .stat-card .num{font-size:28px;font-weight:bold;color:#1890ff;margin:8px 0}
        .stat-card .label{color:#8c8c8c;font-size:14px}
        table{width:100%;border-collapse:collapse}
        th,td{padding:12px;text-align:left;border-bottom:1px solid #f0f0f0}
        th{background:#fafafa;font-weight:600;color:#595959}
        .btn{padding:6px 15px;border-radius:4px;border:none;cursor:pointer;font-size:14px;display:inline-block;text-decoration:none}
        .btn-primary{background:#1890ff;color:white}
        .btn-danger{background:#ff4d4f;color:white}
        .btn-default{background:#fff;border:1px solid #d9d9d9;color:#333}
        input,select{padding:8px 12px;border:1px solid #d9d9d9;border-radius:4px;font-size:14px;outline:none}
        input:focus,select:focus{border-color:#1890ff}
        .form-row{display:flex;gap:10px;margin-bottom:15px;align-items:center}
        .tag{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px}
        .tag-green{background:#f6ffed;color:#52c41a;border:1px solid #b7eb8f}
        .tag-red{background:#fff1f0;color:#ff4d4f;border:1px solid #ffa39e}
        .tag-blue{background:#e6f7ff;color:#1890ff;border:1px solid #91d5ff}
        .logout{color:#ff4d4f;text-decoration:none;margin-left:15px}
        .copy-btn{cursor:pointer;color:#1890ff;font-size:13px}
    </style>
</head>
<body>
    <div class="layout">
        <div class="sidebar">
            <h2>🚀 AI 中转平台</h2>
            <a href="/dashboard" class="menu-item {% if page=='dashboard' %}active{% endif %}">📊 仪表盘</a>
            <a href="/keys" class="menu-item {% if page=='keys' %}active{% endif %}">🔑 API 密钥</a>
            <a href="/logs" class="menu-item {% if page=='logs' %}active{% endif %}">📋 调用记录</a>
            <a href="/models" class="menu-item {% if page=='models' %}active{% endif %}">🤖 模型列表</a>
            <a href="/recharge" class="menu-item {% if page=='recharge' %}active{% endif %}">💳 卡密充值</a>
            {% if user.is_admin %}
            <a href="/admin" class="menu-item" style="margin-top:20px;border-top:1px solid #1f3a5f;padding-top:20px">⚙️ 管理后台</a>
            {% endif %}
        </div>
        <div class="main">
            <div class="header">
                <h2>{% block title %}{% endblock %}</h2>
                <div>
                    <span>👤 {{ user.username }}</span>
                    <span style="margin-left:15px;color:#52c41a;font-weight:bold">¥ {{ "%.2f"|format(user.balance) }}</span>
                    <a href="/logout" class="logout">退出</a>
                </div>
            </div>
            {% block content %}{% endblock %}
        </div>
    </div>
</body>
</html>
"""

# ===================== 用户端页面 =====================
@app.route('/')
def home():
    if not login_required():
        return redirect(url_for('login_page'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET','POST'])
def login_page():
    if request.method == 'POST':
        username = request.form['username']
        password = md5(request.form['password'])
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=? AND status=1", (username,password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('dashboard'))
        return render_template_string(LOGIN_PAGE, error="用户名或密码错误")
    return render_template_string(LOGIN_PAGE, error="")

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>登录 - AI 中转平台</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:Arial}
        .login-box{background:white;border-radius:12px;padding:40px;width:380px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}
        h1{text-align:center;margin-bottom:30px;color:#262626}
        input{width:100%;padding:12px 15px;margin-bottom:15px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;outline:none}
        input:focus{border-color:#1890ff}
        button{width:100%;padding:12px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:6px;font-size:16px;cursor:pointer}
        .error{color:#ff4d4f;text-align:center;margin-bottom:15px;font-size:14px}
        .tip{text-align:center;margin-top:15px;color:#8c8c8c;font-size:13px}
        a{color:#1890ff;text-decoration:none}
    </style>
</head>
<body>
    <div class="login-box">
        <h1>🚀 AI 中转平台</h1>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="post">
            <input name="username" placeholder="用户名" required>
            <input name="password" type="password" placeholder="密码" required>
            <button type="submit">登 录</button>
        </form>
        <div class="tip">没有账号？<a href="/register">立即注册</a></div>
    </div>
</body>
</html>
"""

@app.route('/register', methods=['GET','POST'])
def register_page():
    if request.method == 'POST':
        username = request.form['username']
        password = md5(request.form['password'])
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (username,password,balance,status,created_at) VALUES (?,?,0,1,?)",
                        (username, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            user_id = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']
            # 自动生成默认密钥
            conn.execute("INSERT INTO api_keys (user_id,key,name,created_at) VALUES (?,?,?,?)",
                      (user_id, "sk-" + str(uuid.uuid4()).replace("-",""), "默认密钥", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            return redirect(url_for('login_page'))
        except:
            return render_template_string(LOGIN_PAGE, error="用户名已存在")
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>注册 - AI 中转平台</title>
        <style>
            *{margin:0;padding:0;box-sizing:border-box}
            body{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:Arial}
            .box{background:white;border-radius:12px;padding:40px;width:380px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}
            h1{text-align:center;margin-bottom:30px;color:#262626}
            input{width:100%;padding:12px 15px;margin-bottom:15px;border:1px solid #d9d9d9;border-radius:6px;font-size:14px;outline:none}
            button{width:100%;padding:12px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:none;border-radius:6px;font-size:16px;cursor:pointer}
            .tip{text-align:center;margin-top:15px;color:#8c8c8c;font-size:13px}
            a{color:#1890ff;text-decoration:none}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>注册账号</h1>
            <form method="post">
                <input name="username" placeholder="用户名" required>
                <input name="password" type="password" placeholder="密码" required>
                <button type="submit">注 册</button>
            </form>
            <div class="tip"><a href="/login">返回登录</a></div>
        </div>
    </body>
    </html>
    """)

@app.route('/dashboard')
def dashboard():
    if not login_required():
        return redirect(url_for('login_page'))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    # 统计数据
    today = datetime.now().strftime("%Y-%m-%d")
    today_logs = conn.execute("SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id=? AND date(created_at)=?",
                            (session['user_id'], today)).fetchone()
    total_logs = conn.execute("SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id=?",
                            (session['user_id'],)).fetchone()
    key_count = conn.execute("SELECT COUNT(*) as cnt FROM api_keys WHERE user_id=? AND status=1",
                           (session['user_id'],)).fetchone()
    
    conn.close()
    
    content = """
    <div class="stats">
        <div class="stat-card">
            <div class="label">账户余额</div>
            <div class="num">¥ {{ "%.2f"|format(user.balance) }}</div>
        </div>
        <div class="stat-card">
            <div class="label">今日消费</div>
            <div class="num">¥ {{ "%.4f"|format(today_cost) }}</div>
        </div>
        <div class="stat-card">
            <div class="label">累计消费</div>
            <div class="num">¥ {{ "%.4f"|format(total_cost) }}</div>
        </div>
        <div class="stat-card">
            <div class="label">可用密钥</div>
            <div class="num">{{ key_count }} 个</div>
        </div>
    </div>
    
    <div class="card">
        <h3>快速开始</h3>
        <p style="color:#595959;line-height:2">
            1. 前往「API 密钥」获取你的专属密钥<br>
            2. 接口地址：<code style="background:#f5f5f5;padding:2px 6px;border-radius:4px">{{ request.host_url }}v1</code><br>
            3. 兼容 OpenAI 格式，所有支持自定义接口的客户端均可使用<br>
            4. 调用实时扣费，余额不足请使用卡密充值
        </p>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}仪表盘{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, page='dashboard',
                                today_cost=today_logs['cost'] or 0,
                                total_cost=total_logs['cost'] or 0,
                                key_count=key_count['cnt'])

@app.route('/keys')
def keys_page():
    if not login_required():
        return redirect(url_for('login_page'))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    keys = conn.execute("SELECT * FROM api_keys WHERE user_id=? ORDER BY id DESC", (session['user_id'],)).fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
            <h3 style="margin:0">我的 API 密钥</h3>
            <form method="post" action="/keys/add">
                <input name="name" placeholder="密钥名称" style="width:150px" required>
                <button class="btn btn-primary" type="submit">新增密钥</button>
            </form>
        </div>
        <table>
            <tr>
                <th>名称</th>
                <th>密钥</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
            </tr>
            {% for k in keys %}
            <tr>
                <td>{{ k.name }}</td>
                <td><code>{{ k.key }}</code> <span class="copy-btn" onclick="navigator.clipboard.writeText('{{ k.key }}')">复制</span></td>
                <td>
                    {% if k.status %}<span class="tag tag-green">启用</span>{% else %}<span class="tag tag-red">禁用</span>{% endif %}
                </td>
                <td>{{ k.created_at }}</td>
                <td>
                    <a href="/keys/toggle/{{ k.id }}" class="btn btn-default">{% if k.status %}禁用{% else %}启用{% endif %}</a>
                    <a href="/keys/delete/{{ k.id }}" class="btn btn-danger" onclick="return confirm('确定删除？')">删除</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}API 密钥{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, keys=keys, page='keys')

@app.route('/keys/add', methods=['POST'])
def add_key():
    if not login_required():
        return redirect(url_for('login_page'))
    name = request.form.get('name', '新密钥')
    key = "sk-" + str(uuid.uuid4()).replace("-","")
    conn = get_db()
    conn.execute("INSERT INTO api_keys (user_id,key,name,created_at) VALUES (?,?,?,?)",
                (session['user_id'], key, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return redirect(url_for('keys_page'))

@app.route('/keys/toggle/<int:kid>')
def toggle_key(kid):
    if not login_required():
        return redirect(url_for('login_page'))
    conn = get_db()
    key = conn.execute("SELECT * FROM api_keys WHERE id=? AND user_id=?", (kid, session['user_id'])).fetchone()
    if key:
        new_status = 0 if key['status'] else 1
        conn.execute("UPDATE api_keys SET status=? WHERE id=?", (new_status, kid))
        conn.commit()
    conn.close()
    return redirect(url_for('keys_page'))

@app.route('/keys/delete/<int:kid>')
def delete_key(kid):
    if not login_required():
        return redirect(url_for('login_page'))
    conn = get_db()
    conn.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (kid, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('keys_page'))

@app.route('/logs')
def logs_page():
    if not login_required():
        return redirect(url_for('login_page'))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    logs = conn.execute("SELECT * FROM logs WHERE user_id=? ORDER BY id DESC LIMIT 50", (session['user_id'],)).fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <h3>最近调用记录</h3>
        <table>
            <tr>
                <th>模型</th>
                <th>输入Token</th>
                <th>输出Token</th>
                <th>费用</th>
                <th>时间</th>
            </tr>
            {% for log in logs %}
            <tr>
                <td><span class="tag tag-blue">{{ log.model }}</span></td>
                <td>{{ log.prompt_tokens }}</td>
                <td>{{ log.completion_tokens }}</td>
                <td style="color:#ff4d4f">¥ {{ "%.4f"|format(log.cost) }}</td>
                <td>{{ log.created_at }}</td>
            </tr>
            {% else %}
            <tr><td colspan="5" style="text-align:center;color:#8c8c8c;padding:30px">暂无调用记录</td></tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}调用记录{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, logs=logs, page='logs')

@app.route('/models')
def models_page():
    if not login_required():
        return redirect(url_for('login_page'))
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    models = conn.execute("SELECT * FROM models WHERE status=1 ORDER BY sort ASC").fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <h3>支持的模型列表</h3>
        <table>
            <tr>
                <th>模型名称</th>
                <th>模型ID</th>
                <th>输入单价 / 千Token</th>
                <th>输出单价 / 千Token</th>
                <th>状态</th>
            </tr>
            {% for m in models %}
            <tr>
                <td>{{ m.display_name or m.name }}</td>
                <td><code>{{ m.name }}</code></td>
                <td>¥ {{ "%.4f"|format(m.input_price) }}</td>
                <td>¥ {{ "%.4f"|format(m.output_price) }}</td>
                <td><span class="tag tag-green">在线</span></td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}模型列表{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, models=models, page='models')

@app.route('/recharge', methods=['GET','POST'])
def recharge_page():
    if not login_required():
        return redirect(url_for('login_page'))
    msg = ""
    if request.method == 'POST':
        code = request.form['code'].strip().upper()
        conn = get_db()
        card = conn.execute("SELECT * FROM cards WHERE code=? AND status=0", (code,)).fetchone()
        if card:
            conn.execute("UPDATE cards SET status=1, used_by=?, used_at=? WHERE id=?",
                        (session['user_id'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), card['id']))
            conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (card['amount'], session['user_id']))
            conn.commit()
            msg = f"充值成功！到账 ¥{card['amount']}"
        else:
            msg = "卡密无效或已使用"
        conn.close()
    
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    records = conn.execute("SELECT * FROM cards WHERE used_by=? AND status=1 ORDER BY id DESC LIMIT 10", (session['user_id'],)).fetchall()
    conn.close()
    
    content = f"""
    <div class="card">
        <h3>卡密充值</h3>
        {'<p style="color:#52c41a;margin-bottom:15px">'+msg+'</p>' if msg else ''}
        <form method="post" class="form-row">
            <input name="code" placeholder="请输入充值卡密" style="flex:1" required>
            <button class="btn btn-primary" type="submit">立即充值</button>
        </form>
    </div>
    
    <div class="card">
        <h3>充值记录</h3>
        <table>
            <tr>
                <th>卡密</th>
                <th>面额</th>
                <th>充值时间</th>
            </tr>
            {% for r in records %}
            <tr>
                <td>{{ r.code }}</td>
                <td style="color:#52c41a">+ ¥ {{ "%.2f"|format(r.amount) }}</td>
                <td>{{ r.used_at }}</td>
            </tr>
            {% else %}
            <tr><td colspan="3" style="text-align:center;color:#8c8c8c;padding:20px">暂无充值记录</td></tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}卡密充值{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, records=records, page='recharge')

# ===================== 管理后台 =====================
@app.route('/admin')
def admin_home():
    if not admin_required():
        return "无权限"
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    
    # 统计
    total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()['cnt']
    total_revenue = conn.execute("SELECT SUM(amount) as sum FROM cards WHERE status=1").fetchone()['sum'] or 0
    total_calls = conn.execute("SELECT COUNT(*) as cnt FROM logs").fetchone()['cnt']
    total_cost = conn.execute("SELECT SUM(cost) as sum FROM logs").fetchone()['sum'] or 0
    
    conn.close()
    
    content = f"""
    <div class="stats">
        <div class="stat-card">
            <div class="label">总用户数</div>
            <div class="num">{total_users}</div>
        </div>
        <div class="stat-card">
            <div class="label">累计充值额</div>
            <div class="num">¥ {total_revenue:.2f}</div>
        </div>
        <div class="stat-card">
            <div class="label">总调用次数</div>
            <div class="num">{total_calls}</div>
        </div>
        <div class="stat-card">
            <div class="label">总消耗金额</div>
            <div class="num">¥ {total_cost:.4f}</div>
        </div>
    </div>
    
    <div class="card">
        <h3>快捷操作</h3>
        <div style="display:flex;gap:10px">
            <a href="/admin/users" class="btn btn-primary">用户管理</a>
            <a href="/admin/models" class="btn btn-primary">模型管理</a>
            <a href="/admin/cards" class="btn btn-primary">卡密管理</a>
            <a href="/admin/logs" class="btn btn-primary">调用日志</a>
        </div>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}管理后台 - 数据概览{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, page='admin')

@app.route('/admin/users')
def admin_users():
    if not admin_required():
        return "无权限"
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <h3>用户管理</h3>
        <table>
            <tr>
                <th>ID</th>
                <th>用户名</th>
                <th>余额</th>
                <th>身份</th>
                <th>状态</th>
                <th>注册时间</th>
                <th>操作</th>
            </tr>
            {% for u in users %}
            <tr>
                <td>{{ u.id }}</td>
                <td>{{ u.username }}</td>
                <td style="color:#1890ff;font-weight:bold">¥ {{ "%.2f"|format(u.balance) }}</td>
                <td>{% if u.is_admin %}<span class="tag tag-red">管理员</span>{% else %}普通用户{% endif %}</td>
                <td>{% if u.status %}<span class="tag tag-green">正常</span>{% else %}<span class="tag tag-red">禁用</span>{% endif %}</td>
                <td>{{ u.created_at }}</td>
                <td>
                    <a href="/admin/user/edit/{{ u.id }}" class="btn btn-default">编辑</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}用户管理{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, users=users, page='admin')

@app.route('/admin/user/edit/<int:uid>', methods=['GET','POST'])
def edit_user(uid):
    if not admin_required():
        return "无权限"
    conn = get_db()
    if request.method == 'POST':
        balance = float(request.form['balance'])
        status = int(request.form.get('status', 1))
        conn.execute("UPDATE users SET balance=?, status=? WHERE id=?", (balance, status, uid))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_users'))
    
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    
    content = f"""
    <div class="card" style="max-width:500px">
        <h3>编辑用户 - {u['username']}</h3>
        <form method="post">
            <div class="form-row">
                <label style="width:80px">余额：</label>
                <input name="balance" value="{u['balance']}" step="0.01" type="number" style="flex:1">
            </div>
            <div class="form-row">
                <label style="width:80px">状态：</label>
                <select name="status" style="flex:1">
                    <option value="1" {"selected" if u['status'] else ""}>正常</option>
                    <option value="0" {"selected" if not u['status'] else ""}>禁用</option>
                </select>
            </div>
            <button class="btn btn-primary" type="submit">保存</button>
            <a href="/admin/users" class="btn btn-default">返回</a>
        </form>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}编辑用户{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, page='admin')

@app.route('/admin/models')
def admin_models():
    if not admin_required():
        return "无权限"
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    models = conn.execute("SELECT * FROM models ORDER BY sort ASC").fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
            <h3 style="margin:0">模型管理</h3>
            <button class="btn btn-primary" onclick="document.getElementById('addForm').style.display='block'">添加模型</button>
        </div>
        
        <div id="addForm" style="display:none;background:#fafafa;padding:15px;border-radius:6px;margin-bottom:15px">
            <form method="post" action="/admin/models/add">
                <div class="form-row">
                    <input name="name" placeholder="模型ID (如 gpt-3.5-turbo)" required style="flex:1">
                    <input name="display_name" placeholder="显示名称" style="flex:1">
                </div>
                <div class="form-row">
                    <input name="base_url" placeholder="上游Base URL" required style="flex:1">
                    <input name="api_key" placeholder="上游API Key" required style="flex:1">
                </div>
                <div class="form-row">
                    <input name="input_price" type="number" step="0.0001" placeholder="输入单价/千Token" required style="flex:1">
                    <input name="output_price" type="number" step="0.0001" placeholder="输出单价/千Token" required style="flex:1">
                    <button class="btn btn-primary" type="submit">添加</button>
                </div>
            </form>
        </div>
        
        <table>
            <tr>
                <th>模型ID</th>
                <th>显示名</th>
                <th>输入单价</th>
                <th>输出单价</th>
                <th>状态</th>
                <th>操作</th>
            </tr>
            {% for m in models %}
            <tr>
                <td><code>{{ m.name }}</code></td>
                <td>{{ m.display_name or '-' }}</td>
                <td>¥ {{ "%.4f"|format(m.input_price) }}/k</td>
                <td>¥ {{ "%.4f"|format(m.output_price) }}/k</td>
                <td>{% if m.status %}<span class="tag tag-green">启用</span>{% else %}<span class="tag tag-red">禁用</span>{% endif %}</td>
                <td>
                    <a href="/admin/models/toggle/{{ m.id }}" class="btn btn-default">切换</a>
                    <a href="/admin/models/delete/{{ m.id }}" class="btn btn-danger" onclick="return confirm('确定删除？')">删除</a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}模型管理{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, models=models, page='admin')

@app.route('/admin/models/add', methods=['POST'])
def add_model():
    if not admin_required():
        return "无权限"
    conn = get_db()
    conn.execute("INSERT INTO models (name,display_name,base_url,api_key,input_price,output_price) VALUES (?,?,?,?,?,?)",
                (request.form['name'], request.form.get('display_name',''), request.form['base_url'],
                 request.form['api_key'], float(request.form['input_price']), float(request.form['output_price'])))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_models'))

@app.route('/admin/models/toggle/<int:mid>')
def toggle_model(mid):
    if not admin_required():
        return "无权限"
    conn = get_db()
    m = conn.execute("SELECT * FROM models WHERE id=?", (mid,)).fetchone()
    if m:
        conn.execute("UPDATE models SET status=? WHERE id=?", (0 if m['status'] else 1, mid))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_models'))

@app.route('/admin/models/delete/<int:mid>')
def delete_model(mid):
    if not admin_required():
        return "无权限"
    conn = get_db()
    conn.execute("DELETE FROM models WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_models'))

@app.route('/admin/cards')
def admin_cards():
    if not admin_required():
        return "无权限"
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    cards = conn.execute("SELECT * FROM cards ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
            <h3 style="margin:0">卡密管理</h3>
            <form method="post" action="/admin/cards/generate" style="display:flex;gap:10px">
                <input name="amount" type="number" step="0.01" placeholder="面额" required style="width:120px">
                <input name="count" type="number" value="10" placeholder="数量" style="width:100px">
                <button class="btn btn-primary" type="submit">批量生成</button>
            </form>
        </div>
        
        {% if new_cards %}
        <div style="background:#f6ffed;padding:15px;border-radius:6px;margin-bottom:15px;border:1px solid #b7eb8f">
            <p style="color:#52c41a;margin-bottom:10px">生成成功！共 {{ new_cards|length }} 张卡密：</p>
            <textarea style="width:100%;height:120px;padding:10px;font-family:monospace">{% for c in new_cards %}{{ c }}
{% endfor %}</textarea>
        </div>
        {% endif %}
        
        <table>
            <tr>
                <th>卡密</th>
                <th>面额</th>
                <th>状态</th>
                <th>使用者</th>
                <th>生成时间</th>
            </tr>
            {% for c in cards %}
            <tr>
                <td><code>{{ c.code }}</code></td>
                <td>¥ {{ "%.2f"|format(c.amount) }}</td>
                <td>
                    {% if c.status %}<span class="tag tag-green">已使用</span>{% else %}<span class="tag tag-blue">未使用</span>{% endif %}
                </td>
                <td>{{ c.used_by or '-' }}</td>
                <td>{{ c.created_at }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}卡密管理{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, cards=cards, new_cards=None, page='admin')

@app.route('/admin/cards/generate', methods=['POST'])
def generate_cards():
    if not admin_required():
        return "无权限"
    amount = float(request.form['amount'])
    count = int(request.form.get('count', 10))
    new_cards = []
    conn = get_db()
    for _ in range(count):
        code = str(uuid.uuid4()).replace('-','')[:16].upper()
        conn.execute("INSERT INTO cards (code,amount,created_at) VALUES (?,?,?)",
                    (code, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        new_cards.append(code)
    conn.commit()
    
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    cards = conn.execute("SELECT * FROM cards ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
            <h3 style="margin:0">卡密管理</h3>
            <form method="post" action="/admin/cards/generate" style="display:flex;gap:10px">
                <input name="amount" type="number" step="0.01" placeholder="面额" required style="width:120px">
                <input name="count" type="number" value="10" placeholder="数量" style="width:100px">
                <button class="btn btn-primary" type="submit">批量生成</button>
            </form>
        </div>
        
        <div style="background:#f6ffed;padding:15px;border-radius:6px;margin-bottom:15px;border:1px solid #b7eb8f">
            <p style="color:#52c41a;margin-bottom:10px">生成成功！共 {{ new_cards|length }} 张卡密：</p>
            <textarea style="width:100%;height:120px;padding:10px;font-family:monospace">{% for c in new_cards %}{{ c }}
{% endfor %}</textarea>
        </div>
        
        <table>
            <tr>
                <th>卡密</th>
                <th>面额</th>
                <th>状态</th>
                <th>使用者</th>
                <th>生成时间</th>
            </tr>
            {% for c in cards %}
            <tr>
                <td><code>{{ c.code }}</code></td>
                <td>¥ {{ "%.2f"|format(c.amount) }}</td>
                <td>
                    {% if c.status %}<span class="tag tag-green">已使用</span>{% else %}<span class="tag tag-blue">未使用</span>{% endif %}
                </td>
                <td>{{ c.used_by or '-' }}</td>
                <td>{{ c.created_at }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}卡密管理{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, cards=cards, new_cards=new_cards, page='admin')

@app.route('/admin/logs')
def admin_logs():
    if not admin_required():
        return "无权限"
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    logs = conn.execute("""
        SELECT logs.*, users.username 
        FROM logs LEFT JOIN users ON logs.user_id = users.id 
        ORDER BY logs.id DESC LIMIT 100
    """).fetchall()
    conn.close()
    
    content = """
    <div class="card">
        <h3>全局调用日志</h3>
        <table>
            <tr>
                <th>用户</th>
                <th>模型</th>
                <th>总Token</th>
                <th>费用</th>
                <th>时间</th>
            </tr>
            {% for log in logs %}
            <tr>
                <td>{{ log.username or '未知' }}</td>
                <td><span class="tag tag-blue">{{ log.model }}</span></td>
                <td>{{ log.prompt_tokens + log.completion_tokens }}</td>
                <td style="color:#ff4d4f">¥ {{ "%.4f"|format(log.cost) }}</td>
                <td>{{ log.created_at }}</td>
            </tr>
            {% else %}
            <tr><td colspan="5" style="text-align:center;color:#8c8c8c;padding:30px">暂无记录</td></tr>
            {% endfor %}
        </table>
    </div>
    """
    
    return render_template_string(USER_LAYOUT + "{% block title %}调用日志{% endblock %}{% block content %}" + content + "{% endblock %}",
                                user=user, logs=logs, page='admin')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# ===================== 核心 API 中转 + 计费 =====================
@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
def chat_completions():
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Access-Control-Allow-Headers': '*'
        }
    
    # 验证 API Key
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        return {"error": {"message": "无效的 API Key", "type": "auth_error"}}, 401, {'Access-Control-Allow-Origin': '*'}
    
    api_key = auth.replace('Bearer ', '').strip()
    
    conn = get_db()
    key_info = conn.execute("SELECT * FROM api_keys WHERE key=? AND status=1", (api_key,)).fetchone()
    
    if not key_info:
        conn.close()
        return {"error": {"message": "API Key 无效或已禁用", "type": "auth_error"}}, 401, {'Access-Control-Allow-Origin': '*'}
    
    user_id = key_info['user_id']
    user = conn.execute("SELECT * FROM users WHERE id=? AND status=1", (user_id,)).fetchone()
    
    if not user:
        conn.close()
        return {"error": {"message": "账户已被禁用", "type": "auth_error"}}, 403, {'Access-Control-Allow-Origin': '*'}
    
    # 获取模型配置
    body = request.json
    model_name = body.get('model', 'gpt-3.5-turbo')
    model_cfg = conn.execute("SELECT * FROM models WHERE name=? AND status=1", (model_name,)).fetchone()
    
    if not model_cfg:
        conn.close()
        return {"error": {"message": f"模型 {model_name} 不可用", "type": "model_error"}}, 400, {'Access-Control-Allow-Origin': '*'}
    
    # 预扣费检查（最低预估）
    if user['balance'] < 0.001:
        conn.close()
        return {"error": {"message": "余额不足，请充值", "type": "insufficient_quota"}}, 402, {'Access-Control-Allow-Origin': '*'}
    
    # 转发请求
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
        
        # 计算费用
        if 'usage' in result:
            prompt_tokens = result['usage'].get('prompt_tokens', 0)
            completion_tokens = result['usage'].get('completion_tokens', 0)
        else:
            prompt_tokens = 0
            completion_tokens = 0
        
        cost = (prompt_tokens / 1000) * model_cfg['input_price'] + (completion_tokens / 1000) * model_cfg['output_price']
        
        # 结算扣费 + 记录日志
        conn.execute("UPDATE users SET balance=balance-? WHERE id=?", (cost, user_id))
        conn.execute("INSERT INTO logs (user_id,model,prompt_tokens,completion_tokens,cost,created_at) VALUES (?,?,?,?,?,?)",
                    (user_id, model_name, prompt_tokens, completion_tokens, cost, 
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        return result, resp.status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    
    except Exception as e:
        conn.close()
        return {"error": {"message": str(e), "type": "server_error"}}, 500, {'Access-Control-Allow-Origin': '*'}

# ===================== 启动 =====================
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
