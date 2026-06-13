import os
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, request, render_template, session, redirect, url_for, abort

from src.config.settings import settings
from src.utils.database import Database
from src.security.password import PasswordPolicy, PasswordHasherService
from src.services import UserService, ModelService, ChatService, VideoService
from src.api.chat_api import chat_bp
from src.api.video_api import video_bp

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'))
app.secret_key = settings.SECRET_KEY

app.register_blueprint(chat_bp)
app.register_blueprint(video_bp)

db = Database(settings.DATABASE_URL, settings.DATABASE_PATH)

user_service = UserService()
model_service = ModelService()
chat_service = ChatService()
video_service = VideoService()

MENU_ITEMS = [
    ("dashboard", "📊 仪表盘", "/dashboard"),
    ("keys", "🔑 API 密钥", "/keys"),
    ("logs", "📋 调用记录", "/logs"),
    ("models", "🤖 模型列表", "/models"),
    ("recharge", "💳 卡密充值", "/recharge"),
    ("profile", "👤 个人设置", "/profile"),
]

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

def init_db():
    conn = db.get_connection()
    
    db.execute_query(conn, '''
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
    
    db.execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS api_keys (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            key TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '默认密钥',
            status INTEGER DEFAULT 1,
            created_at TEXT
        )
    ''')
    
    db.execute_query(conn, '''
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
    
    db.execute_query(conn, '''
        CREATE TABLE IF NOT EXISTS models (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            display_name TEXT,
            base_url TEXT NOT NULL,
            api_key TEXT NOT NULL,
            input_price REAL NOT NULL,
            output_price REAL NOT NULL,
            status INTEGER DEFAULT 1,
            sort INTEGER DEFAULT 0
        )
    ''')
    
    db.execute_query(conn, '''
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
    
    try:
        ph = PasswordHasherService()
        admin_username = settings.ADMIN_USERNAME
        admin_password = settings.ADMIN_PASSWORD
        pwd_hash = ph.hash_password(admin_password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        import uuid
        if db.use_postgres:
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
    
    try:
        if db.use_postgres:
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
    
    video_service.init_tables()
    
    conn.close()

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
            ip_address = request.remote_addr
            success, msg, user = user_service.login(username, password, ip_address)
            
            if success and user:
                session['user_id'] = user['id']
                session['is_admin'] = user['is_admin']
                return redirect('/dashboard')
            error = msg
    
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
        
        success, msg = user_service.register_user(username, password)
        
        if success:
            return redirect('/login')
        error = msg
    
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
            .password-hint{font-size:12px;color:#8c8c8c;margin-bottom:10px}
            .strength-bar{height:4px;background:#f0f0f0;border-radius:2px;margin-top:5px}
            .strength-bar div{height:100%;border-radius:2px;transition:width 0.3s}
            .strength-weak{background:#ff4d4f;width:25%}
            .strength-medium{background:#faad14;width:50%}
            .strength-strong{background:#52c41a;width:75%}
            .strength-very-strong{background:#1890ff;width:100%}
        </style>
        <script>
            function checkPassword() {
                var pwd = document.getElementById('password').value;
                var strength = 0;
                
                if (pwd.length >= 8) strength++;
                if (pwd.length >= 12) strength++;
                if (/[a-z]/.test(pwd)) strength++;
                if (/[A-Z]/.test(pwd)) strength++;
                if (/[0-9]/.test(pwd)) strength++;
                if (/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) strength++;
                
                var bar = document.querySelector('.strength-bar div');
                if (strength <= 2) { bar.className = 'strength-weak'; }
                else if (strength <= 3) { bar.className = 'strength-medium'; }
                else if (strength <= 4) { bar.className = 'strength-strong'; }
                else { bar.className = 'strength-very-strong'; }
            }
        </script>
    </head>
    <body>
        <div class="box">
            <h1>注册账号</h1>
            {% if error %}<div class="error">{{ error }}</div>{% endif %}
            <form method="post">
                <input name="username" placeholder="用户名 (3-20字符)" required>
                <input id="password" name="password" type="password" placeholder="密码" required onkeyup="checkPassword()">
                <div class="password-hint">密码要求：长度≥8位，包含大小写字母、数字、特殊字符中至少3类</div>
                <div class="strength-bar"><div></div></div>
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
    user = user_service.get_user_by_id(session['user_id'])
    logs = chat_service.get_logs(session['user_id'], limit=1)
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_cost = sum(log['cost'] for log in logs if log['created_at'].startswith(today))
    
    all_logs = chat_service.get_logs(session['user_id'])
    total_cost = sum(log['cost'] for log in all_logs)
    total_calls = len(all_logs)
    
    keys = user_service.get_api_keys(session['user_id'])
    key_count = sum(1 for k in keys if k['status'] == 1)
    
    return render_template('dashboard.html', 
                           page_title='仪表盘', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='dashboard',
                           today_cost=today_cost,
                           total_cost=total_cost,
                           total_calls=total_calls,
                           key_count=key_count,
                           host_url=request.host_url)

@app.route('/keys')
@login_required
def keys_page():
    user = user_service.get_user_by_id(session['user_id'])
    keys = user_service.get_api_keys(session['user_id'])
    
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
    user_service.create_api_key(session['user_id'], name)
    return redirect('/keys')

@app.route('/keys/toggle/<int:kid>')
@login_required
def toggle_key(kid):
    user_service.toggle_api_key(kid, session['user_id'])
    return redirect('/keys')

@app.route('/keys/delete/<int:kid>')
@login_required
def delete_key(kid):
    user_service.delete_api_key(kid, session['user_id'])
    return redirect('/keys')

@app.route('/logs')
@login_required
def logs_page():
    user = user_service.get_user_by_id(session['user_id'])
    logs = chat_service.get_logs(session['user_id'])
    
    return render_template('logs.html', 
                           page_title='调用记录', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='logs',
                           logs=logs)

@app.route('/models')
@login_required
def models_page():
    user = user_service.get_user_by_id(session['user_id'])
    models = model_service.get_models()
    
    return render_template('models.html', 
                           page_title='模型列表', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='models',
                           models=models)

@app.route('/recharge', methods=['GET','POST'])
@login_required
def recharge_page():
    user = user_service.get_user_by_id(session['user_id'])
    msg = ""
    msg_type = ""
    
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if not code:
            msg = "请输入卡密"
            msg_type = "error"
        else:
            conn = db.get_connection()
            try:
                card = db.select_one(conn, 'cards', where_clause='code = ? AND status = 0', where_params=(code,))
                if card:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    db.update(conn, 'cards', {'status': 1, 'used_by': session['user_id'], 'used_at': now}, 'id = ?', (card['id'],))
                    user_service.update_balance(session['user_id'], card['amount'])
                    conn.commit()
                    msg = f'充值成功！到账 ¥{card["amount"]}'
                    msg_type = "success"
                    user = user_service.get_user_by_id(session['user_id'])
                else:
                    msg = "卡密无效或已使用"
                    msg_type = "error"
            finally:
                conn.close()
    
    conn = db.get_connection()
    try:
        records = db.select(conn, 'cards', where_clause='used_by = ? AND status = 1', where_params=(session['user_id'],), order_by='id DESC', limit=10)
    finally:
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
    user = user_service.get_user_by_id(session['user_id'])
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
        else:
            success, message = user_service.change_password(session['user_id'], old_password, new_password)
            if success:
                msg = message
                msg_type = "success"
            else:
                msg = message
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
    user = user_service.get_user_by_id(session['user_id'])
    
    conn = db.get_connection()
    try:
        total_users = db.execute_query(conn, "SELECT COUNT(*) as cnt FROM users", fetch='one')
        total_revenue = db.execute_query(conn, "SELECT SUM(amount) as sum FROM cards WHERE status = 1", fetch='one')
        total_calls = db.execute_query(conn, "SELECT COUNT(*) as cnt FROM logs", fetch='one')
        total_cost = db.execute_query(conn, "SELECT SUM(cost) as sum FROM logs", fetch='one')
    finally:
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
    user = user_service.get_user_by_id(session['user_id'])
    conn = db.get_connection()
    try:
        users = db.select(conn, 'users', order_by='id DESC')
    finally:
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
    if request.method == 'POST':
        try:
            balance = float(request.form.get('balance', 0))
            status = int(request.form.get('status', 1))
            user_service.update_balance(uid, balance - (user_service.get_user_by_id(uid) or {}).get('balance', 0))
            conn = db.get_connection()
            try:
                db.update(conn, 'users', {'status': status}, 'id = ?', (uid,))
                conn.commit()
            finally:
                conn.close()
        except (ValueError, TypeError):
            pass
        return redirect('/admin/users')
    
    conn = db.get_connection()
    try:
        u = db.select_one(conn, 'users', where_clause='id = ?', where_params=(uid,))
    finally:
        conn.close()
    
    user = user_service.get_user_by_id(session['user_id'])
    
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
    user = user_service.get_user_by_id(session['user_id'])
    models = model_service.get_models(status=None)
    
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
        model_service.create_model(
            name=request.form['name'],
            display_name=request.form.get('display_name', ''),
            base_url=request.form['base_url'],
            api_key=request.form['api_key'],
            input_price=float(request.form['input_price']),
            output_price=float(request.form['output_price'])
        )
    except Exception as e:
        logger.error(f"Error adding model: {e}")
    return redirect('/admin/models')

@app.route('/admin/models/toggle/<int:mid>')
@login_required
@admin_required
def toggle_model(mid):
    model_service.toggle_model(mid)
    return redirect('/admin/models')

@app.route('/admin/models/delete/<int:mid>')
@login_required
@admin_required
def delete_model(mid):
    model_service.delete_model(mid)
    return redirect('/admin/models')

@app.route('/admin/cards')
@login_required
@admin_required
def admin_cards():
    user = user_service.get_user_by_id(session['user_id'])
    conn = db.get_connection()
    try:
        cards = db.select(conn, 'cards', order_by='id DESC', limit=50)
    finally:
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
        import uuid
        amount = float(request.form.get('amount', 0))
        count = max(1, min(100, int(request.form.get('count', 10))))
        new_cards = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = db.get_connection()
        try:
            for _ in range(count):
                code = str(uuid.uuid4()).replace('-','')[:16].upper()
                db.insert(conn, 'cards', {'code': code, 'amount': amount, 'created_at': now})
                new_cards.append(code)
            conn.commit()
        finally:
            conn.close()
        
        user = user_service.get_user_by_id(session['user_id'])
        conn = db.get_connection()
        try:
            cards = db.select(conn, 'cards', order_by='id DESC', limit=50)
        finally:
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
    user = user_service.get_user_by_id(session['user_id'])
    logs = chat_service.get_all_logs(limit=100)
    
    return render_template('admin_logs.html', 
                           page_title='调用日志', 
                           user=user, 
                           menu_items=MENU_ITEMS, 
                           active_menu='admin',
                           logs=logs)

@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 - 无权限访问</h1><p>您没有权限访问此页面</p>", 403

@app.errorhandler(404)
def not_found(e):
    return "<h1>404 - 页面未找到</h1>", 404

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=settings.PORT, debug=settings.DEBUG)
