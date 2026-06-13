from flask import Flask, request, render_template, render_template_string, session, redirect, url_for, flash, abort
import sqlite3
import bcrypt
import uuid
import requests
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'moran-ai-platform-2024-stable-version')
DB_PATH = os.environ.get('DATABASE_PATH', '/tmp/platform.db')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MENU_ITEMS = [
    ("dashboard", "📊 仪表盘", "/dashboard"),
    ("keys", "🔑 API 密钥", "/keys"),
    ("logs", "📋 调用记录", "/logs"),
    ("models", "🤖 模型列表", "/models"),
    ("recharge", "💳 卡密充值", "/recharge"),
    ("profile", "👤 个人设置", "/profile"),
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  balance REAL DEFAULT 0,
                  is_admin INTEGER DEFAULT 0,
                  status INTEGER DEFAULT 1,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  key TEXT UNIQUE NOT NULL,
                  name TEXT DEFAULT '默认密钥',
                  status INTEGER DEFAULT 1,
                  created_at TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  code TEXT UNIQUE NOT NULL,
                  amount REAL NOT NULL,
                  status INTEGER DEFAULT 0,
                  used_by INTEGER,
                  used_at TEXT,
                  created_at TEXT)''')
    
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  model TEXT,
                  prompt_tokens INTEGER DEFAULT 0,
                  completion_tokens INTEGER DEFAULT 0,
                  cost REAL DEFAULT 0,
                  created_at TEXT)''')
    
    try:
        admin_username = os.environ.get('ADMIN_USERNAME', 'MoRan')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'yangyang')
        pwd_hash = bcrypt.hashpw(admin_password.encode(), bcrypt.gensalt())
        c.execute("INSERT INTO users (username,password,is_admin,balance,status,created_at) VALUES (?,?,?,?,?,?)",
                  (admin_username, pwd_hash.decode(), 1, 9999.0, 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        c.execute("INSERT INTO api_keys (user_id,key,name,created_at) VALUES (?,?,?,?)",
                  (1, "sk-" + str(uuid.uuid4()).replace("-",""), "管理员主密钥", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except sqlite3.IntegrityError:
        pass
    
    try:
        c.execute("INSERT INTO models (name,display_name,base_url,api_key,input_price,output_price,status) VALUES (?,?,?,?,?,?,?)",
                  ("gpt-3.5-turbo", "GPT-3.5-Turbo", "https://openai.api2d.net/v1", "fk-替换为你的密钥", 0.005, 0.015, 1))
    except sqlite3.IntegrityError:
        pass
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return user

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if session.get('is_admin', 0) != 1:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    init_db()
    if 'user_id' not in session:
        return redirect('/login')
    return redirect('/dashboard')

@app.route('/login', methods=['GET','POST'])
def login_page():
    error = ""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            error = "请输入用户名和密码"
        else:
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE username=? AND status=1", (username,)).fetchone()
            conn.close()
            
            if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
                session['user_id'] = user['id']
                session['is_admin'] = user['is_admin']
                return redirect('/dashboard')
            error = "用户名或密码错误"
    
    return render_template_string("""
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
    """, error=error)

@app.route('/register', methods=['GET','POST'])
def register_page():
    error = ""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            error = "请输入用户名和密码"
        elif len(username) < 3 or len(username) > 20:
            error = "用户名长度应在3-20个字符之间"
        elif len(password) < 6:
            error = "密码长度至少6个字符"
        else:
            try:
                pwd_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                conn = get_db()
                conn.execute("INSERT INTO users (username,password,balance,status,created_at) VALUES (?,?,0,1,?)",
                            (username, pwd_hash.decode(), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                uid = conn.execute("SELECT last_insert_rowid() as id").fetchone()['id']
                conn.execute("INSERT INTO api_keys (user_id,key,name,created_at) VALUES (?,?,?,?)",
                          (uid, "sk-" + str(uuid.uuid4()).replace("-",""), "默认密钥", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                return redirect('/login')
            except sqlite3.IntegrityError:
                error = "用户名已存在"
    
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
            .error{color:#ff4d4f;text-align:center;margin-bottom:15px;font-size:14px}
        </style>
    </head>
    <body>
        <div class="box">
            <h1>注册账号</h1>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
            <form method="post">
                <input name="username" placeholder="用户名" required>
                <input name="password" type="password" placeholder="密码" required>
                <button type="submit">注 册</button>
            </form>
            <div class="tip"><a href="/login">返回登录</a></div>
        </div>
    </body>
    </html>
    """, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user()
    conn = get_db()
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_logs = conn.execute("SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id=? AND date(created_at)=?",
                            (session['user_id'], today)).fetchone()
    total_logs = conn.execute("SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id=?",
                            (session['user_id'],)).fetchone()
    key_count = conn.execute("SELECT COUNT(*) as cnt FROM api_keys WHERE user_id=? AND status=1",
                           (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('base.html', 
                           page_title='仪表盘', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='dashboard',
                           today_cost=today_logs['cost'] or 0,
                           total_cost=total_logs['cost'] or 0,
                           total_calls=total_logs['cnt'] or 0,
                           key_count=key_count['cnt'] or 0,
                           host_url=request.host_url)

@app.route('/keys')
@login_required
def keys_page():
    user = get_user()
    conn = get_db()
    keys = conn.execute("SELECT * FROM api_keys WHERE user_id=? ORDER BY id DESC", (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('keys.html', 
                           page_title='API 密钥', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='keys',
                           keys=keys)

@app.route('/keys/add', methods=['POST'])
@login_required
def add_key():
    name = request.form.get('name', '新密钥').strip()[:50]
    key = "sk-" + str(uuid.uuid4()).replace("-","")
    conn = get_db()
    conn.execute("INSERT INTO api_keys (user_id,key,name,created_at) VALUES (?,?,?,?)",
                (session['user_id'], key, name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return redirect('/keys')

@app.route('/keys/toggle/<int:kid>')
@login_required
def toggle_key(kid):
    conn = get_db()
    k = conn.execute("SELECT * FROM api_keys WHERE id=? AND user_id=?", (kid, session['user_id'])).fetchone()
    if k:
        new_status = 0 if k['status'] else 1
        conn.execute("UPDATE api_keys SET status=? WHERE id=?", (new_status, kid))
        conn.commit()
    conn.close()
    return redirect('/keys')

@app.route('/keys/delete/<int:kid>')
@login_required
def delete_key(kid):
    conn = get_db()
    conn.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (kid, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/keys')

@app.route('/logs')
@login_required
def logs_page():
    user = get_user()
    conn = get_db()
    logs = conn.execute("SELECT * FROM logs WHERE user_id=? ORDER BY id DESC LIMIT 50", (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('logs.html', 
                           page_title='调用记录', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='logs',
                           logs=logs)

@app.route('/models')
@login_required
def models_page():
    user = get_user()
    conn = get_db()
    models = conn.execute("SELECT * FROM models WHERE status=1 ORDER BY sort ASC").fetchall()
    conn.close()
    
    return render_template('models.html', 
                           page_title='模型列表', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='models',
                           models=models)

@app.route('/recharge', methods=['GET','POST'])
@login_required
def recharge_page():
    user = get_user()
    msg = ""
    msg_type = ""
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if not code:
            msg = "请输入卡密"
            msg_type = "error"
        else:
            conn = get_db()
            card = conn.execute("SELECT * FROM cards WHERE code=? AND status=0", (code,)).fetchone()
            if card:
                conn.execute("UPDATE cards SET status=1, used_by=?, used_at=? WHERE id=?",
                            (session['user_id'], datetime.now().strftime("%Y-%m-%d %H:%M:%S"), card['id']))
                conn.execute("UPDATE users SET balance=balance+? WHERE id=?", (card['amount'], session['user_id']))
                conn.commit()
                msg = f'充值成功！到账 ¥{card["amount"]}'
                msg_type = "success"
                user = get_user()
            else:
                msg = "卡密无效或已使用"
                msg_type = "error"
            conn.close()
    
    conn = get_db()
    records = conn.execute("SELECT * FROM cards WHERE used_by=? AND status=1 ORDER BY id DESC LIMIT 10", (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('recharge.html', 
                           page_title='卡密充值', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='recharge',
                           msg=msg,
                           msg_type=msg_type,
                           records=records)

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile_page():
    user = get_user()
    msg = ""
    msg_type = ""
    
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not old_password or not new_password or not confirm_password:
            msg = "请填写所有字段"
            msg_type = "error"
        elif new_password != confirm_password:
            msg = "两次输入的密码不一致"
            msg_type = "error"
        elif len(new_password) < 6:
            msg = "密码长度至少6个字符"
            msg_type = "error"
        elif bcrypt.checkpw(old_password.encode(), user['password'].encode()):
            pwd_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
            conn = get_db()
            conn.execute("UPDATE users SET password=? WHERE id=?", (pwd_hash.decode(), session['user_id']))
            conn.commit()
            conn.close()
            msg = "密码修改成功"
            msg_type = "success"
        else:
            msg = "原密码错误"
            msg_type = "error"
    
    return render_template('profile.html', 
                           page_title='个人设置', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='profile',
                           msg=msg,
                           msg_type=msg_type)

@app.route('/admin')
@login_required
@admin_required
def admin_home():
    user = get_user()
    conn = get_db()
    
    total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()['cnt']
    total_revenue = conn.execute("SELECT SUM(amount) as sum FROM cards WHERE status=1").fetchone()['sum'] or 0
    total_calls = conn.execute("SELECT COUNT(*) as cnt FROM logs").fetchone()['cnt']
    total_cost = conn.execute("SELECT SUM(cost) as sum FROM logs").fetchone()['sum'] or 0
    conn.close()
    
    return render_template('admin_dashboard.html', 
                           page_title='管理后台', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           total_users=total_users,
                           total_revenue=total_revenue,
                           total_calls=total_calls,
                           total_cost=total_cost)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    user = get_user()
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('admin_users.html', 
                           page_title='用户管理', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           users=users)

@app.route('/admin/user/edit/<int:uid>', methods=['GET','POST'])
@login_required
@admin_required
def edit_user(uid):
    conn = get_db()
    if request.method == 'POST':
        try:
            balance = float(request.form.get('balance', 0))
            status = int(request.form.get('status', 1))
            conn.execute("UPDATE users SET balance=?, status=? WHERE id=?", (balance, status, uid))
            conn.commit()
        except (ValueError, TypeError):
            pass
        conn.close()
        return redirect('/admin/users')
    
    u = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    user = get_user()
    conn.close()
    
    return render_template('admin_edit_user.html', 
                           page_title='编辑用户', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           edit_user=u)

@app.route('/admin/models')
@login_required
@admin_required
def admin_models():
    user = get_user()
    conn = get_db()
    models = conn.execute("SELECT * FROM models ORDER BY sort ASC").fetchall()
    conn.close()
    
    return render_template('admin_models.html', 
                           page_title='模型管理', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           models=models)

@app.route('/admin/models/add', methods=['POST'])
@login_required
@admin_required
def add_model():
    try:
        conn = get_db()
        conn.execute("INSERT INTO models (name,display_name,base_url,api_key,input_price,output_price) VALUES (?,?,?,?,?,?)",
                    (request.form['name'], request.form.get('display_name',''), request.form['base_url'],
                     request.form['api_key'], float(request.form['input_price']), float(request.form['output_price'])))
        conn.commit()
    except (sqlite3.Error, ValueError):
        pass
    finally:
        conn.close()
    return redirect('/admin/models')

@app.route('/admin/models/toggle/<int:mid>')
@login_required
@admin_required
def toggle_model(mid):
    conn = get_db()
    m = conn.execute("SELECT * FROM models WHERE id=?", (mid,)).fetchone()
    if m:
        conn.execute("UPDATE models SET status=? WHERE id=?", (0 if m['status'] else 1, mid))
        conn.commit()
    conn.close()
    return redirect('/admin/models')

@app.route('/admin/models/delete/<int:mid>')
@login_required
@admin_required
def delete_model(mid):
    conn = get_db()
    conn.execute("DELETE FROM models WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    return redirect('/admin/models')

@app.route('/admin/cards')
@login_required
@admin_required
def admin_cards():
    user = get_user()
    conn = get_db()
    cards = conn.execute("SELECT * FROM cards ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    
    return render_template('admin_cards.html', 
                           page_title='卡密管理', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           cards=cards,
                           new_cards=None)

@app.route('/admin/cards/generate', methods=['POST'])
@login_required
@admin_required
def generate_cards():
    try:
        amount = float(request.form.get('amount', 0))
        count = max(1, min(100, int(request.form.get('count', 10))))
        new_cards = []
        conn = get_db()
        for _ in range(count):
            code = str(uuid.uuid4()).replace('-','')[:16].upper()
            conn.execute("INSERT INTO cards (code,amount,created_at) VALUES (?,?,?)",
                        (code, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            new_cards.append(code)
        conn.commit()
        
        user = get_user()
        cards = conn.execute("SELECT * FROM cards ORDER BY id DESC LIMIT 50").fetchall()
        conn.close()
        
        return render_template('admin_cards.html', 
                               page_title='卡密管理', 
                               user=user, 
                               menu_items=MENU_ITEMS, 
                               active_menu='admin',
                               cards=cards,
                               new_cards=new_cards,
                               amount=amount)
    except (ValueError, TypeError):
        return redirect('/admin/cards')

@app.route('/admin/logs')
@login_required
@admin_required
def admin_logs():
    user = get_user()
    conn = get_db()
    logs = conn.execute("""
        SELECT logs.*, users.username 
        FROM logs LEFT JOIN users ON logs.user_id = users.id 
        ORDER BY logs.id DESC LIMIT 100
    """).fetchall()
    conn.close()
    
    return render_template('admin_logs.html', 
                           page_title='调用日志', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           logs=logs)

@app.route('/v1/chat/completions', methods=['POST', 'OPTIONS'])
def chat_completions():
    if request.method == 'OPTIONS':
        return '', 200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST,OPTIONS',
            'Access-Control-Allow-Headers': '*'
        }
    
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer sk-'):
        logger.warning("Invalid API Key format")
        return {"error": {"message": "无效的 API Key"}}, 401, {'Access-Control-Allow-Origin': '*'}
    
    api_key = auth.replace('Bearer ', '').strip()
    
    conn = get_db()
    key_info = conn.execute("SELECT * FROM api_keys WHERE key=? AND status=1", (api_key,)).fetchone()
    
    if not key_info:
        conn.close()
        logger.warning(f"API Key not found or disabled: {api_key[:10]}...")
        return {"error": {"message": "API Key 无效或已禁用"}}, 401, {'Access-Control-Allow-Origin': '*'}
    
    user_id = key_info['user_id']
    user = conn.execute("SELECT * FROM users WHERE id=? AND status=1", (user_id,)).fetchone()
    
    if not user:
        conn.close()
        logger.warning(f"User account disabled: {user_id}")
        return {"error": {"message": "账户已被禁用"}}, 403, {'Access-Control-Allow-Origin': '*'}
    
    body = request.json
    if not body:
        conn.close()
        return {"error": {"message": "请求体为空"}}, 400, {'Access-Control-Allow-Origin': '*'}
    
    model_name = body.get('model', 'gpt-3.5-turbo')
    model_cfg = conn.execute("SELECT * FROM models WHERE name=? AND status=1", (model_name,)).fetchone()
    
    if not model_cfg:
        conn.close()
        logger.warning(f"Model not available: {model_name}")
        return {"error": {"message": f"模型 {model_name} 不可用"}}, 400, {'Access-Control-Allow-Origin': '*'}
    
    if user['balance'] < 0.001:
        conn.close()
        return {"error": {"message": "余额不足，请充值"}}, 402, {'Access-Control-Allow-Origin': '*'}
    
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
        
        if 'usage' in result:
            prompt_tokens = result['usage'].get('prompt_tokens', 0)
            completion_tokens = result['usage'].get('completion_tokens', 0)
        else:
            prompt_tokens = 0
            completion_tokens = 0
        
        cost = (prompt_tokens / 1000) * model_cfg['input_price'] + (completion_tokens / 1000) * model_cfg['output_price']
        
        conn.execute("UPDATE users SET balance=balance-? WHERE id=?", (cost, user_id))
        conn.execute("INSERT INTO logs (user_id,model,prompt_tokens,completion_tokens,cost,created_at) VALUES (?,?,?,?,?,?)",
                    (user_id, model_name, prompt_tokens, completion_tokens, cost, 
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        
        logger.info(f"API call successful - User: {user_id}, Model: {model_name}, Cost: {cost:.4f}")
        
        return result, resp.status_code, {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        }
    
    except requests.exceptions.RequestException as e:
        conn.close()
        logger.error(f"Request error: {str(e)}")
        return {"error": {"message": f"上游服务错误: {str(e)[:100]}"}}, 503, {'Access-Control-Allow-Origin': '*'}
    except Exception as e:
        conn.close()
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": {"message": f"服务器错误: {str(e)[:100]}"}}, 500, {'Access-Control-Allow-Origin': '*'}

@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 - 无权限访问</h1><p>您没有权限访问此页面</p>", 403

@app.errorhandler(404)
def not_found(e):
    return "<h1>404 - 页面未找到</h1>", 404

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)