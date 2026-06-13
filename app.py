from flask import Flask, request, render_template, render_template_string, session, redirect, url_for, abort, Response
import hashlib
import uuid
import requests
import os
import logging
from datetime import datetime
from functools import wraps

# PostgreSQL 支持是可选的，只在设置了 DATABASE_URL 时才需要
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
app.secret_key = os.environ.get('SECRET_KEY', 'moran-ai-platform-2024-stable-version')

# 数据库配置 - 支持 PostgreSQL 和 SQLite
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = bool(DATABASE_URL)

# 启动时检查依赖
if USE_POSTGRES and not PSYCOPG2_AVAILABLE:
    raise RuntimeError("检测到 DATABASE_URL 环境变量，但 psycopg2 库未安装。请运行: pip install psycopg2-binary")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MENU_ITEMS = [
    ("dashboard", "首页", "/dashboard"),
    ("chat", "控制台", "/chat"),
    ("models", "模型", "/models"),
]

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    if USE_POSTGRES:
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL 数据库需要 psycopg2 库，请安装: pip install psycopg2-binary")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        import sqlite3
        db_path = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'platform.db'))
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

def execute_query(conn, query, params=None, fetch=False):
    """统一的查询执行函数，兼容 PostgreSQL 和 SQLite"""
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # 替换 SQLite 语法为 PostgreSQL 语法
        query = query.replace('AUTOINCREMENT', 'SERIAL')
        query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
        query = query.replace('?', '%s')
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
            # 转换为字典列表
            cursor.close()
            return result
        cursor.close()
        return None
    else:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
            cursor.close()
            return result
        cursor.close()
        return None

def init_db():
    conn = get_db()
    
    # 创建用户表
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            balance REAL DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            status INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')
    
    # 创建 API 密钥表
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            key TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '默认密钥',
            status INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')
    
    # 创建卡密表
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS cards (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE NOT NULL,
            amount REAL NOT NULL,
            status INTEGER DEFAULT 0,
            used_by INTEGER,
            used_at TEXT,
            created_at TEXT
        )
    ''')
    
    # 创建模型表
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS models (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT,
            provider TEXT DEFAULT 'openai',
            base_url TEXT NOT NULL,
            api_key TEXT NOT NULL,
            input_price REAL NOT NULL,
            output_price REAL NOT NULL,
            status INTEGER DEFAULT 1,
            sort INTEGER DEFAULT 0,
            remark TEXT,
            version INTEGER DEFAULT 1
        )
    ''')
    
    # 创建模型历史表
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS model_history (
            id SERIAL PRIMARY KEY,
            model_id INTEGER NOT NULL,
            version INTEGER NOT NULL,
            changes TEXT,
            operator TEXT,
            created_at TEXT
        )
    ''')
    
    # 创建日志表
    execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            model TEXT,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            cost REAL DEFAULT 0,
            created_at TEXT
        )
    ''')
    
    conn.commit()
    
    # 创建管理员账户
    try:
        admin_username = os.environ.get('ADMIN_USERNAME', 'MoRan')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'yangyang')
        pwd_hash = hash_password(admin_password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, is_admin, balance, status, created_at) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (admin_username, pwd_hash, 1, 9999.0, 1, now)
            )
            user_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO api_keys (user_id, key, name, created_at) VALUES (%s, %s, %s, %s)",
                (user_id, "sk-" + str(uuid.uuid4()).replace("-", ""), "管理员主密钥", now)
            )
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, is_admin, balance, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (admin_username, pwd_hash, 1, 9999.0, 1, now)
            )
            user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO api_keys (user_id, key, name, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "sk-" + str(uuid.uuid4()).replace("-", ""), "管理员主密钥", now)
            )
            cursor.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.info(f"Admin user already exists or error: {e}")
    
    # 创建默认模型
    try:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO models (name, display_name, base_url, api_key, input_price, output_price, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ("gpt-3.5-turbo", "GPT-3.5-Turbo", "https://api.openai.com/v1", "sk-替换为你的OpenAI密钥", 0.0015, 0.002, 1)
            )
            cursor.execute(
                "INSERT INTO models (name, display_name, base_url, api_key, input_price, output_price, status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                ("deepseek-chat", "DeepSeek Chat", "https://api.deepseek.com/v1", "sk-替换为你的DeepSeek密钥", 0.0005, 0.0015, 1)
            )
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO models (name, display_name, base_url, api_key, input_price, output_price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("gpt-3.5-turbo", "GPT-3.5-Turbo", "https://api.openai.com/v1", "sk-替换为你的OpenAI密钥", 0.0015, 0.002, 1)
            )
            cursor.execute(
                "INSERT INTO models (name, display_name, base_url, api_key, input_price, output_price, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("deepseek-chat", "DeepSeek Chat", "https://api.deepseek.com/v1", "sk-替换为你的DeepSeek密钥", 0.0005, 0.0015, 1)
            )
            cursor.close()
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.info(f"Default model already exists or error: {e}")
    
    conn.close()

def row_to_dict(row):
    """将数据库行转换为字典"""
    if row is None:
        return None
    if USE_POSTGRES:
        return dict(row)
    else:
        return dict(row) if hasattr(row, 'keys') else row

def get_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
        user = cursor.fetchone()
        cursor.close()
    else:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
        row = cursor.fetchone()
        cursor.close()
        if row:
            columns = [desc[0] for desc in cursor.description]
            user = dict(zip(columns, row))
        else:
            user = None
    conn.close()
    return user

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
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
            if USE_POSTGRES:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute("SELECT * FROM users WHERE username = %s AND status = 1", (username,))
                user = cursor.fetchone()
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ? AND status = 1", (username,))
                row = cursor.fetchone()
                cursor.close()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    user = dict(zip(columns, row))
                else:
                    user = None
            conn.close()
            
            if user and user['password'] == hash_password(password):
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
                pwd_hash = hash_password(password)
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = get_db()
                
                if USE_POSTGRES:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (username, password, balance, status, created_at) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                        (username, pwd_hash, 0, 1, now)
                    )
                    uid = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO api_keys (user_id, key, name, created_at) VALUES (%s, %s, %s, %s)",
                        (uid, "sk-" + str(uuid.uuid4()).replace("-", ""), "默认密钥", now)
                    )
                    cursor.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO users (username, password, balance, status, created_at) VALUES (?, ?, ?, ?, ?)",
                        (username, pwd_hash, 0, 1, now)
                    )
                    uid = cursor.lastrowid
                    cursor.execute(
                        "INSERT INTO api_keys (user_id, key, name, created_at) VALUES (?, ?, ?, ?)",
                        (uid, "sk-" + str(uuid.uuid4()).replace("-", ""), "默认密钥", now)
                    )
                    cursor.close()
                
                conn.commit()
                conn.close()
                return redirect('/login')
            except Exception as e:
                conn.rollback()
                conn.close()
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

def fetch_all(conn, query, params=None):
    """获取所有结果"""
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        cursor.close()
        return results
    else:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        return results

def fetch_one(conn, query, params=None):
    """获取单个结果"""
    if USE_POSTGRES:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query, params or ())
        result = cursor.fetchone()
        cursor.close()
        return result
    else:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        row = cursor.fetchone()
        if row:
            columns = [desc[0] for desc in cursor.description]
            result = dict(zip(columns, row))
        else:
            result = None
        cursor.close()
        return result

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_user()
    conn = get_db()
    
    today = datetime.now().strftime("%Y-%m-%d")
    if USE_POSTGRES:
        today_logs = fetch_one(conn, "SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id = %s AND DATE(created_at) = %s", (session['user_id'], today))
        total_logs = fetch_one(conn, "SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id = %s", (session['user_id'],))
        key_count = fetch_one(conn, "SELECT COUNT(*) as cnt FROM api_keys WHERE user_id = %s AND status = 1", (session['user_id'],))
    else:
        today_logs = fetch_one(conn, "SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id = ? AND DATE(created_at) = ?", (session['user_id'], today))
        total_logs = fetch_one(conn, "SELECT SUM(cost) as cost, COUNT(*) as cnt FROM logs WHERE user_id = ?", (session['user_id'],))
        key_count = fetch_one(conn, "SELECT COUNT(*) as cnt FROM api_keys WHERE user_id = ? AND status = 1", (session['user_id'],))
    conn.close()
    
    return render_template('dashboard.html', 
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
    if USE_POSTGRES:
        keys = fetch_all(conn, "SELECT * FROM api_keys WHERE user_id = %s ORDER BY id DESC", (session['user_id'],))
    else:
        keys = fetch_all(conn, "SELECT * FROM api_keys WHERE user_id = ? ORDER BY id DESC", (session['user_id'],))
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
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    if USE_POSTGRES:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO api_keys (user_id, key, name, created_at) VALUES (%s, %s, %s, %s)",
                      (session['user_id'], key, name, now))
        cursor.close()
    else:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO api_keys (user_id, key, name, created_at) VALUES (?, ?, ?, ?)",
                      (session['user_id'], key, name, now))
        cursor.close()
    conn.commit()
    conn.close()
    return redirect('/keys')

@app.route('/keys/toggle/<int:kid>')
@login_required
def toggle_key(kid):
    conn = get_db()
    if USE_POSTGRES:
        k = fetch_one(conn, "SELECT * FROM api_keys WHERE id = %s AND user_id = %s", (kid, session['user_id']))
    else:
        k = fetch_one(conn, "SELECT * FROM api_keys WHERE id = ? AND user_id = ?", (kid, session['user_id']))
    if k:
        new_status = 0 if k['status'] else 1
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute("UPDATE api_keys SET status = %s WHERE id = %s", (new_status, kid))
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute("UPDATE api_keys SET status = ? WHERE id = ?", (new_status, kid))
            cursor.close()
        conn.commit()
    conn.close()
    return redirect('/keys')

@app.route('/keys/delete/<int:kid>')
@login_required
def delete_key(kid):
    conn = get_db()
    if USE_POSTGRES:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_keys WHERE id = %s AND user_id = %s", (kid, session['user_id']))
        cursor.close()
    else:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_keys WHERE id = ? AND user_id = ?", (kid, session['user_id']))
        cursor.close()
    conn.commit()
    conn.close()
    return redirect('/keys')

@app.route('/logs')
@login_required
def logs_page():
    user = get_user()
    conn = get_db()
    if USE_POSTGRES:
        logs = fetch_all(conn, "SELECT * FROM logs WHERE user_id = %s ORDER BY id DESC LIMIT 50", (session['user_id'],))
    else:
        logs = fetch_all(conn, "SELECT * FROM logs WHERE user_id = ? ORDER BY id DESC LIMIT 50", (session['user_id'],))
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
    if USE_POSTGRES:
        models = fetch_all(conn, "SELECT * FROM models WHERE status = 1 ORDER BY sort ASC")
    else:
        models = fetch_all(conn, "SELECT * FROM models WHERE status = 1 ORDER BY sort ASC")
    conn.close()
    
    return render_template('models.html', 
                           page_title='模型列表', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='models',
                           models=models,
                           host_url=request.host_url)

@app.route('/chat')
@login_required
def chat_page():
    user = get_user()
    conn = get_db()
    if USE_POSTGRES:
        models = fetch_all(conn, "SELECT * FROM models WHERE status = 1 ORDER BY sort ASC")
        api_key = fetch_one(conn, "SELECT * FROM api_keys WHERE user_id = %s AND status = 1 ORDER BY id DESC LIMIT 1", (session['user_id'],))
    else:
        models = fetch_all(conn, "SELECT * FROM models WHERE status = 1 ORDER BY sort ASC")
        api_key = fetch_one(conn, "SELECT * FROM api_keys WHERE user_id = ? AND status = 1 ORDER BY id DESC LIMIT 1", (session['user_id'],))
    conn.close()
    
    selected_model = request.args.get('model', models[0]['name'] if models else 'gpt-3.5-turbo')
    
    return render_template('chat.html', 
                           page_title='AI 对话', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='chat',
                           models=models,
                           selected_model=selected_model,
                           api_key=api_key['key'] if api_key else '')

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
            if USE_POSTGRES:
                card = fetch_one(conn, "SELECT * FROM cards WHERE code = %s AND status = 0", (code,))
            else:
                card = fetch_one(conn, "SELECT * FROM cards WHERE code = ? AND status = 0", (code,))
            if card:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if USE_POSTGRES:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE cards SET status = 1, used_by = %s, used_at = %s WHERE id = %s",
                                  (session['user_id'], now, card['id']))
                    cursor.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (card['amount'], session['user_id']))
                    cursor.close()
                else:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE cards SET status = 1, used_by = ?, used_at = ? WHERE id = ?",
                                  (session['user_id'], now, card['id']))
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (card['amount'], session['user_id']))
                    cursor.close()
                conn.commit()
                msg = f'充值成功！到账 ¥{card["amount"]}'
                msg_type = "success"
                user = get_user()
            else:
                msg = "卡密无效或已使用"
                msg_type = "error"
            conn.close()
    
    conn = get_db()
    if USE_POSTGRES:
        records = fetch_all(conn, "SELECT * FROM cards WHERE used_by = %s AND status = 1 ORDER BY id DESC LIMIT 10", (session['user_id'],))
    else:
        records = fetch_all(conn, "SELECT * FROM cards WHERE used_by = ? AND status = 1 ORDER BY id DESC LIMIT 10", (session['user_id'],))
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
        elif user['password'] == hash_password(old_password):
            pwd_hash = hash_password(new_password)
            conn = get_db()
            if USE_POSTGRES:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password = %s WHERE id = %s", (pwd_hash, session['user_id']))
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password = ? WHERE id = ?", (pwd_hash, session['user_id']))
                cursor.close()
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
    
    if USE_POSTGRES:
        total_users = fetch_one(conn, "SELECT COUNT(*) as cnt FROM users")
        total_revenue = fetch_one(conn, "SELECT SUM(amount) as sum FROM cards WHERE status = 1")
        total_calls = fetch_one(conn, "SELECT COUNT(*) as cnt FROM logs")
        total_cost = fetch_one(conn, "SELECT SUM(cost) as sum FROM logs")
    else:
        total_users = fetch_one(conn, "SELECT COUNT(*) as cnt FROM users")
        total_revenue = fetch_one(conn, "SELECT SUM(amount) as sum FROM cards WHERE status = 1")
        total_calls = fetch_one(conn, "SELECT COUNT(*) as cnt FROM logs")
        total_cost = fetch_one(conn, "SELECT SUM(cost) as sum FROM logs")
    conn.close()
    
    return render_template('admin_dashboard.html', 
                           page_title='管理后台', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           total_users=total_users['cnt'],
                           total_revenue=total_revenue['sum'] or 0,
                           total_calls=total_calls['cnt'],
                           total_cost=total_cost['sum'] or 0)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    user = get_user()
    conn = get_db()
    if USE_POSTGRES:
        users = fetch_all(conn, "SELECT * FROM users ORDER BY id DESC")
    else:
        users = fetch_all(conn, "SELECT * FROM users ORDER BY id DESC")
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
            if USE_POSTGRES:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = %s, status = %s WHERE id = %s", (balance, status, uid))
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = ?, status = ? WHERE id = ?", (balance, status, uid))
                cursor.close()
            conn.commit()
        except (ValueError, TypeError):
            pass
        conn.close()
        return redirect('/admin/users')
    
    if USE_POSTGRES:
        u = fetch_one(conn, "SELECT * FROM users WHERE id = %s", (uid,))
    else:
        u = fetch_one(conn, "SELECT * FROM users WHERE id = ?", (uid,))
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
    if USE_POSTGRES:
        models = fetch_all(conn, "SELECT * FROM models ORDER BY sort ASC")
    else:
        models = fetch_all(conn, "SELECT * FROM models ORDER BY sort ASC")
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
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO models (name, display_name, base_url, api_key, input_price, output_price) VALUES (%s, %s, %s, %s, %s, %s)",
                          (request.form['name'], request.form.get('display_name',''), request.form['base_url'],
                           request.form['api_key'], float(request.form['input_price']), float(request.form['output_price'])))
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO models (name, display_name, base_url, api_key, input_price, output_price) VALUES (?, ?, ?, ?, ?, ?)",
                          (request.form['name'], request.form.get('display_name',''), request.form['base_url'],
                           request.form['api_key'], float(request.form['input_price']), float(request.form['output_price'])))
            cursor.close()
        conn.commit()
    except Exception as e:
        logger.error(f"Error adding model: {e}")
    finally:
        conn.close()
    return redirect('/admin/models')

@app.route('/admin/models/toggle/<int:mid>')
@login_required
@admin_required
def toggle_model(mid):
    conn = get_db()
    if USE_POSTGRES:
        m = fetch_one(conn, "SELECT * FROM models WHERE id = %s", (mid,))
    else:
        m = fetch_one(conn, "SELECT * FROM models WHERE id = ?", (mid,))
    if m:
        new_status = 0 if m['status'] else 1
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute("UPDATE models SET status = %s WHERE id = %s", (new_status, mid))
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute("UPDATE models SET status = ? WHERE id = ?", (new_status, mid))
            cursor.close()
        conn.commit()
    conn.close()
    return redirect('/admin/models')

@app.route('/admin/models/delete/<int:mid>')
@login_required
@admin_required
def delete_model(mid):
    conn = get_db()
    if USE_POSTGRES:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM models WHERE id = %s", (mid,))
        cursor.close()
    else:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM models WHERE id = ?", (mid,))
        cursor.close()
    conn.commit()
    conn.close()
    return redirect('/admin/models')

@app.route('/admin/cards')
@login_required
@admin_required
def admin_cards():
    user = get_user()
    conn = get_db()
    if USE_POSTGRES:
        cards = fetch_all(conn, "SELECT * FROM cards ORDER BY id DESC LIMIT 50")
    else:
        cards = fetch_all(conn, "SELECT * FROM cards ORDER BY id DESC LIMIT 50")
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
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db()
        for _ in range(count):
            code = str(uuid.uuid4()).replace('-','')[:16].upper()
            if USE_POSTGRES:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cards (code, amount, created_at) VALUES (%s, %s, %s)", (code, amount, now))
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO cards (code, amount, created_at) VALUES (?, ?, ?)", (code, amount, now))
                cursor.close()
            new_cards.append(code)
        conn.commit()
        
        user = get_user()
        if USE_POSTGRES:
            cards = fetch_all(conn, "SELECT * FROM cards ORDER BY id DESC LIMIT 50")
        else:
            cards = fetch_all(conn, "SELECT * FROM cards ORDER BY id DESC LIMIT 50")
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
    if USE_POSTGRES:
        logs = fetch_all(conn, """
            SELECT logs.*, users.username 
            FROM logs LEFT JOIN users ON logs.user_id = users.id 
            ORDER BY logs.id DESC LIMIT 100
        """)
    else:
        logs = fetch_all(conn, """
            SELECT logs.*, users.username 
            FROM logs LEFT JOIN users ON logs.user_id = users.id 
            ORDER BY logs.id DESC LIMIT 100
        """)
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
        return {"error": {"message": "Invalid API Key"}}, 401, {'Access-Control-Allow-Origin': '*'}
    
    api_key = auth.replace('Bearer ', '').strip()
    
    conn = get_db()
    if USE_POSTGRES:
        key_info = fetch_one(conn, "SELECT * FROM api_keys WHERE key = %s AND status = 1", (api_key,))
    else:
        key_info = fetch_one(conn, "SELECT * FROM api_keys WHERE key = ? AND status = 1", (api_key,))
    
    if not key_info:
        conn.close()
        logger.warning(f"API Key not found or disabled: {api_key[:10]}...")
        return {"error": {"message": "API Key not found or disabled"}}, 401, {'Access-Control-Allow-Origin': '*'}
    
    user_id = key_info['user_id']
    if USE_POSTGRES:
        user = fetch_one(conn, "SELECT * FROM users WHERE id = %s AND status = 1", (user_id,))
    else:
        user = fetch_one(conn, "SELECT * FROM users WHERE id = ? AND status = 1", (user_id,))
    
    if not user:
        conn.close()
        logger.warning(f"User account disabled: {user_id}")
        return {"error": {"message": "Account disabled"}}, 403, {'Access-Control-Allow-Origin': '*'}
    
    body = request.json
    if not body:
        conn.close()
        return {"error": {"message": "Empty request body"}}, 400, {'Access-Control-Allow-Origin': '*'}
    
    model_name = body.get('model', 'gpt-3.5-turbo')
    if USE_POSTGRES:
        model_cfg = fetch_one(conn, "SELECT * FROM models WHERE name = %s AND status = 1", (model_name,))
    else:
        model_cfg = fetch_one(conn, "SELECT * FROM models WHERE name = ? AND status = 1", (model_name,))
    
    if not model_cfg:
        conn.close()
        logger.warning(f"Model not available: {model_name}")
        return {"error": {"message": f"Model {model_name} not available"}}, 400, {'Access-Control-Allow-Origin': '*'}
    
    if user['balance'] < 0.001:
        conn.close()
        return {"error": {"message": "Insufficient balance, please recharge"}}, 402, {'Access-Control-Allow-Origin': '*'}
    
    # 检查是否需要流式输出
    is_streaming = body.get('stream', False)
    print(f"[DEBUG] Stream check - is_streaming: {is_streaming}, body keys: {list(body.keys())}", flush=True)
    logger.info(f"Stream check - is_streaming: {is_streaming}, body keys: {list(body.keys())}")
    
    # 流式响应处理
    if is_streaming:
        print("[DEBUG] Entering stream_response function", flush=True)
        logger.info("Entering stream_response function")
        return stream_response(conn, user, model_cfg, body)
    
    try:
        resp = requests.post(
            f"{model_cfg['base_url']}/chat/completions",
            json={**body, 'stream': False},  # 强制禁用流式响应
            headers={
                'Authorization': f"Bearer {model_cfg['api_key']}",
                'Content-Type': 'application/json'
            },
            timeout=120
        )
        
        if not resp.text:
            conn.close()
            logger.error(f"Empty response from upstream: {model_name}")
            return {"error": {"message": "Empty response from upstream service"}}, 503, {'Access-Control-Allow-Origin': '*'}
        
        # 处理可能的 SSE 格式响应
        response_text = resp.text.strip()
        if response_text.startswith('data: '):
            # 解析 SSE 格式，提取第一个完整的 JSON
            lines = response_text.split('\n')
            for line in lines:
                if line.startswith('data: '):
                    json_str = line[5:].strip()
                    if json_str and json_str != '[DONE]':
                        try:
                            import json
                            result = json.loads(json_str)
                            break
                        except ValueError:
                            continue
            else:
                conn.close()
                logger.error("No valid JSON found in SSE response")
                return {"error": {"message": "Invalid SSE response format"}}, 503, {'Access-Control-Allow-Origin': '*'}
        else:
            try:
                result = resp.json()
            except (ValueError, json.JSONDecodeError, Exception) as e:
                logger.error(f"JSON Decode Error: {type(e).__name__}: {str(e)}, Response text: {resp.text[:500]}")
                conn.close()
                return {"error": {"message": f"JSON parse error: {str(e)[:100]}"}}, 503, {'Access-Control-Allow-Origin': '*'}
        
        if 'usage' in result:
            prompt_tokens = result['usage'].get('prompt_tokens', 0)
            completion_tokens = result['usage'].get('completion_tokens', 0)
        else:
            prompt_tokens = 0
            completion_tokens = 0
        
        cost = (prompt_tokens / 1000) * model_cfg['input_price'] + (completion_tokens / 1000) * model_cfg['output_price']
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (cost, user_id))
            cursor.execute("INSERT INTO logs (user_id, model, prompt_tokens, completion_tokens, cost, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                          (user_id, model_name, prompt_tokens, completion_tokens, cost, now))
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (cost, user_id))
            cursor.execute("INSERT INTO logs (user_id, model, prompt_tokens, completion_tokens, cost, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                          (user_id, model_name, prompt_tokens, completion_tokens, cost, now))
            cursor.close()
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
        return {"error": {"message": f"Upstream service error: {str(e)[:100]}"}}, 503, {'Access-Control-Allow-Origin': '*'}
    except Exception as e:
        conn.close()
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": {"message": f"Server error: {str(e)[:100]}"}}, 500, {'Access-Control-Allow-Origin': '*'}


def stream_response(conn, user, model_cfg, body):
    """处理流式响应"""
    user_id = user['id']
    model_name = body.get('model', 'gpt-3.5-turbo')
    
    try:
        # 发送流式请求到上游
        resp = requests.post(
            f"{model_cfg['base_url']}/chat/completions",
            json={**body, 'stream': True},
            headers={
                'Authorization': f"Bearer {model_cfg['api_key']}",
                'Content-Type': 'application/json'
            },
            stream=True,
            timeout=120
        )
        
        # 如果上游返回非200状态码，记录错误
        if resp.status_code != 200:
            error_text = resp.text[:200] if resp.text else "Empty error response"
            logger.error(f"Upstream streaming error: {resp.status_code} - {error_text}")
            conn.close()
            return {"error": {"message": f"Upstream error {resp.status_code}: {error_text}"}}, resp.status_code, {'Access-Control-Allow-Origin': '*'}
        
        prompt_tokens = 0
        completion_tokens = 0
        full_content = ""
        
        def generate():
            nonlocal prompt_tokens, completion_tokens, full_content
            
            try:
                for line in resp.iter_lines():
                    if not line:
                        continue
                    
                    line_text = line.decode('utf-8', errors='ignore').strip()
                    
                    if not line_text:
                        continue
                    
                    if line_text.startswith('data: '):
                        data_str = line_text[6:].strip()
                        
                        if data_str == '[DONE]':
                            yield 'data: [DONE]\n\n'
                            break
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            # 提取 token 计数
                            if 'usage' in data:
                                prompt_tokens = data['usage'].get('prompt_tokens', 0)
                                completion_tokens = data['usage'].get('completion_tokens', 0)
                            
                            # 累积完整内容用于计费
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta and delta['content'] is not None:
                                    full_content += delta['content']
                            
                            # 转发数据
                            yield f'{line_text}\n\n'
                            
                        except json.JSONDecodeError:
                            continue
                    elif line_text:
                        # 其他响应行直接转发
                        yield f'{line_text}\n\n'
                
                # 流结束后计算并扣除费用
                if not completion_tokens:
                    completion_tokens = max(len(full_content) // 4, 1)  # 至少1个token
                
            except Exception as e:
                logger.error(f"Error in streaming generator: {str(e)}")
        
        # 异步更新费用和日志 - 在新线程中创建新的数据库连接
        import threading
        def update_cost():
            try:
                # 为后台线程创建新的数据库连接
                thread_conn = get_db()
                
                cost = (prompt_tokens / 1000) * model_cfg['input_price'] + (completion_tokens / 1000) * model_cfg['output_price']
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if USE_POSTGRES:
                    cursor = thread_conn.cursor()
                    cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (cost, user_id))
                    cursor.execute("INSERT INTO logs (user_id, model, prompt_tokens, completion_tokens, cost, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
                                  (user_id, model_name, prompt_tokens, completion_tokens, cost, now))
                    cursor.close()
                else:
                    cursor = thread_conn.cursor()
                    cursor.execute("UPDATE users SET balance = balance - ? WHERE id = ?", (cost, user_id))
                    cursor.execute("INSERT INTO logs (user_id, model, prompt_tokens, completion_tokens, cost, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                  (user_id, model_name, prompt_tokens, completion_tokens, cost, now))
                    cursor.close()
                thread_conn.commit()
                thread_conn.close()
                
                logger.info(f"Streaming complete - User: {user_id}, Model: {model_name}, Cost: {cost:.4f}, Tokens: {prompt_tokens + completion_tokens}")
            except Exception as e:
                logger.error(f"Failed to update streaming cost: {str(e)}")
        
        # 在后台线程中更新费用
        threading.Thread(target=update_cost, daemon=True).start()
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST,OPTIONS',
                'Access-Control-Allow-Headers': '*',
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except requests.exceptions.RequestException as e:
        conn.close()
        logger.error(f"Stream request error: {str(e)}")
        return {"error": {"message": f"Stream error: {str(e)[:100]}"}}, 503, {'Access-Control-Allow-Origin': '*'}
    except Exception as e:
        conn.close()
        logger.error(f"Stream error: {str(e)}")
        return {"error": {"message": f"Stream error: {str(e)[:100]}"}}, 500, {'Access-Control-Allow-Origin': '*'}

@app.route('/admin')
@login_required
def admin_page():
    user = get_user()
    if not user or not user.get('is_admin'):
        abort(403)
    
    conn = get_db()
    if USE_POSTGRES:
        models = fetch_all(conn, "SELECT * FROM models ORDER BY sort ASC")
    else:
        models = fetch_all(conn, "SELECT * FROM models ORDER BY sort ASC")
    conn.close()
    
    return render_template('admin_models.html',
                           page_title='模型管理',
                           user=user,
                           menu_items=MENU_ITEMS,
                           active_menu='admin',
                           models=models)

@app.route('/admin/models/list')
@login_required
def admin_models_list():
    user = get_user()
    if not user or not user.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 403
    
    conn = get_db()
    if USE_POSTGRES:
        models = fetch_all(conn, "SELECT id, name, display_name, status FROM models ORDER BY sort ASC")
    else:
        models = fetch_all(conn, "SELECT id, name, display_name, status FROM models ORDER BY sort ASC")
    conn.close()
    
    return jsonify(models)

@app.route('/admin/model/<int:model_id>')
@login_required
def admin_get_model(model_id):
    user = get_user()
    if not user or not user.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 403
    
    conn = get_db()
    if USE_POSTGRES:
        model = fetch_one(conn, "SELECT * FROM models WHERE id = %s", (model_id,))
    else:
        model = fetch_one(conn, "SELECT * FROM models WHERE id = ?", (model_id,))
    conn.close()
    
    if not model:
        return jsonify({"error": "Model not found"}), 404
    
    return jsonify(model)

@app.route('/admin/model/<int:model_id>/history')
@login_required
def admin_model_history(model_id):
    user = get_user()
    if not user or not user.get('is_admin'):
        return jsonify({"error": "Unauthorized"}), 403
    
    conn = get_db()
    if USE_POSTGRES:
        history = fetch_all(conn, "SELECT * FROM model_history WHERE model_id = %s ORDER BY version DESC LIMIT 20", (model_id,))
    else:
        history = fetch_all(conn, "SELECT * FROM model_history WHERE model_id = ? ORDER BY version DESC LIMIT 20", (model_id,))
    conn.close()
    
    return jsonify(history)

@app.route('/admin/model/save', methods=['POST'])
@login_required
def admin_save_model():
    user = get_user()
    if not user or not user.get('is_admin'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    model_id = request.form.get('id', '').strip()
    name = request.form.get('name', '').strip()
    display_name = request.form.get('display_name', '').strip()
    provider = request.form.get('provider', 'openai')
    base_url = request.form.get('base_url', '').strip()
    api_key = request.form.get('api_key', '').strip()
    input_price = request.form.get('input_price', '')
    output_price = request.form.get('output_price', '')
    sort = request.form.get('sort', '10')
    status = request.form.get('status', '1')
    remark = request.form.get('remark', '').strip()
    
    if not name or not base_url or not input_price or not output_price:
        return jsonify({"success": False, "message": "请填写必填字段"}), 400
    
    try:
        input_price = float(input_price)
        output_price = float(output_price)
        sort = int(sort)
        status = int(status)
    except ValueError:
        return jsonify({"success": False, "message": "参数格式错误"}), 400
    
    conn = get_db()
    
    try:
        if model_id:
            if USE_POSTGRES:
                old_model = fetch_one(conn, "SELECT * FROM models WHERE id = %s", (model_id,))
            else:
                old_model = fetch_one(conn, "SELECT * FROM models WHERE id = ?", (model_id,))
            
            changes = []
            if old_model:
                if old_model['name'] != name:
                    changes.append(f"名称: {old_model['name']} -> {name}")
                if old_model['display_name'] != display_name:
                    changes.append(f"显示名称: {old_model['display_name']} -> {display_name}")
                if old_model['provider'] != provider:
                    changes.append(f"厂商: {old_model['provider']} -> {provider}")
                if old_model['base_url'] != base_url:
                    changes.append(f"API地址: {old_model['base_url']} -> {base_url}")
                if old_model['input_price'] != input_price:
                    changes.append(f"输入价格: {old_model['input_price']} -> {input_price}")
                if old_model['output_price'] != output_price:
                    changes.append(f"输出价格: {old_model['output_price']} -> {output_price}")
                if old_model['sort'] != sort:
                    changes.append(f"排序: {old_model['sort']} -> {sort}")
                if old_model['status'] != status:
                    changes.append(f"状态: {'启用' if old_model['status'] == 1 else '禁用'} -> {'启用' if status == 1 else '禁用'}")
            
            new_version = old_model['version'] + 1 if old_model else 1
            
            if USE_POSTGRES:
                cursor = conn.cursor()
                cursor.execute("UPDATE models SET name = %s, display_name = %s, provider = %s, base_url = %s, api_key = %s, input_price = %s, output_price = %s, sort = %s, status = %s, remark = %s, version = %s WHERE id = %s",
                              (name, display_name, provider, base_url, api_key, input_price, output_price, sort, status, remark, new_version, model_id))
                
                if changes:
                    cursor.execute("INSERT INTO model_history (model_id, version, changes, operator) VALUES (%s, %s, %s, %s)",
                                  (model_id, new_version, ', '.join(changes), user['username']))
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("UPDATE models SET name = ?, display_name = ?, provider = ?, base_url = ?, api_key = ?, input_price = ?, output_price = ?, sort = ?, status = ?, remark = ?, version = ? WHERE id = ?",
                              (name, display_name, provider, base_url, api_key, input_price, output_price, sort, status, remark, new_version, model_id))
                
                if changes:
                    cursor.execute("INSERT INTO model_history (model_id, version, changes, operator) VALUES (?, ?, ?, ?)",
                                  (model_id, new_version, ', '.join(changes), user['username']))
                cursor.close()
            
            conn.commit()
            message = "更新成功"
        else:
            if USE_POSTGRES:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO models (name, display_name, provider, base_url, api_key, input_price, output_price, sort, status, remark, version) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1) RETURNING id",
                              (name, display_name, provider, base_url, api_key, input_price, output_price, sort, status, remark))
                model_id = cursor.fetchone()[0]
                cursor.execute("INSERT INTO model_history (model_id, version, changes, operator) VALUES (%s, %s, %s, %s)",
                              (model_id, 1, '创建模型', user['username']))
                cursor.close()
            else:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO models (name, display_name, provider, base_url, api_key, input_price, output_price, sort, status, remark, version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                              (name, display_name, provider, base_url, api_key, input_price, output_price, sort, status, remark))
                model_id = cursor.lastrowid
                cursor.execute("INSERT INTO model_history (model_id, version, changes, operator) VALUES (?, ?, ?, ?)",
                              (model_id, 1, '创建模型', user['username']))
                cursor.close()
            
            conn.commit()
            message = "创建成功"
        
        conn.close()
        return jsonify({"success": True, "message": message, "model_id": model_id})
    
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Save model error: {str(e)}")
        return jsonify({"success": False, "message": "保存失败: " + str(e)[:50]}), 500

@app.route('/admin/model/<int:model_id>/delete', methods=['POST'])
@login_required
def admin_delete_model(model_id):
    user = get_user()
    if not user or not user.get('is_admin'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    conn = get_db()
    
    try:
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM model_history WHERE model_id = %s", (model_id,))
            cursor.execute("DELETE FROM models WHERE id = %s", (model_id,))
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM model_history WHERE model_id = ?", (model_id,))
            cursor.execute("DELETE FROM models WHERE id = ?", (model_id,))
            cursor.close()
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "删除成功"})
    
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Delete model error: {str(e)}")
        return jsonify({"success": False, "message": "删除失败: " + str(e)[:50]}), 500

@app.route('/admin/model/<int:model_id>/rollback/<int:version>', methods=['POST'])
@login_required
def admin_rollback_model(model_id, version):
    user = get_user()
    if not user or not user.get('is_admin'):
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    conn = get_db()
    
    try:
        if USE_POSTGRES:
            history = fetch_all(conn, "SELECT * FROM model_history WHERE model_id = %s ORDER BY version ASC", (model_id,))
        else:
            history = fetch_all(conn, "SELECT * FROM model_history WHERE model_id = ? ORDER BY version ASC", (model_id,))
        
        if version < 1 or version > len(history):
            conn.close()
            return jsonify({"success": False, "message": "无效的版本号"}), 400
        
        current_version = history[-1]['version'] if history else 1
        
        if USE_POSTGRES:
            cursor = conn.cursor()
            cursor.execute("UPDATE models SET version = %s WHERE id = %s", (current_version + 1, model_id))
            cursor.execute("INSERT INTO model_history (model_id, version, changes, operator) VALUES (%s, %s, %s, %s)",
                          (model_id, current_version + 1, f'回滚到版本 {version}', user['username']))
            cursor.close()
        else:
            cursor = conn.cursor()
            cursor.execute("UPDATE models SET version = ? WHERE id = ?", (current_version + 1, model_id))
            cursor.execute("INSERT INTO model_history (model_id, version, changes, operator) VALUES (?, ?, ?, ?)",
                          (model_id, current_version + 1, f'回滚到版本 {version}', user['username']))
            cursor.close()
        
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "恢复成功"})
    
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Rollback model error: {str(e)}")
        return jsonify({"success": False, "message": "恢复失败: " + str(e)[:50]}), 500

@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 - 无权限访问</h1><p>您没有权限访问此页面</p>", 403

@app.errorhandler(404)
def not_found(e):
    return "<h1>404 - 页面未找到</h1>", 404

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
