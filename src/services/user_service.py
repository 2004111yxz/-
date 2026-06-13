import uuid
from datetime import datetime
from typing import Dict, Optional

from src.utils.database import Database
from src.security.password import PasswordPolicy, PasswordHasherService, LoginAttemptTracker
from src.config.settings import settings

class UserService:
    def __init__(self):
        self.db = Database(settings.DATABASE_URL, settings.DATABASE_PATH)
        self.password_hasher = PasswordHasherService(
            time_cost=settings.ARGON2_TIME_COST,
            memory_cost=settings.ARGON2_MEMORY_COST,
            parallelism=settings.ARGON2_PARALLELISM
        )
        self.login_tracker = LoginAttemptTracker()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            return self.db.select_one(conn, 'users', where_clause='id = ?', where_params=(user_id,))
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            return self.db.select_one(conn, 'users', where_clause='username = ?', where_params=(username,))
        finally:
            conn.close()
    
    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            key_info = self.db.select_one(conn, 'api_keys', where_clause='key = ? AND status = 1', where_params=(api_key,))
            if key_info:
                return self.db.select_one(conn, 'users', where_clause='id = ? AND status = 1', where_params=(key_info['user_id'],))
            return None
        finally:
            conn.close()
    
    def register_user(self, username: str, password: str) -> tuple[bool, str]:
        valid, errors = PasswordPolicy.validate(password)
        if not valid:
            return False, ', '.join(errors)
        
        if len(username) < 3 or len(username) > 20:
            return False, '用户名长度应在3-20个字符之间'
        
        conn = self.db.get_connection()
        try:
            existing_user = self.db.select_one(conn, 'users', where_clause='username = ?', where_params=(username,))
            if existing_user:
                return False, '用户名已存在'
            
            pwd_hash = self.password_hasher.hash_password(password)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            user_data = {
                'username': username,
                'password': pwd_hash,
                'balance': 0,
                'is_admin': 0,
                'status': 1,
                'created_at': now
            }
            
            user_id = self.db.insert(conn, 'users', user_data)
            
            key_data = {
                'user_id': user_id,
                'key': 'sk-' + str(uuid.uuid4()).replace("-", ""),
                'name': '默认密钥',
                'status': 1,
                'created_at': now
            }
            self.db.insert(conn, 'api_keys', key_data)
            
            conn.commit()
            return True, '注册成功'
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def login(self, username: str, password: str, ip_address: str) -> tuple[bool, str, Optional[Dict]]:
        if self.login_tracker.is_locked(username, ip_address, settings.MAX_LOGIN_ATTEMPTS, settings.LOGIN_LOCKOUT_MINUTES):
            return False, '账户已被锁定，请稍后再试', None
        
        user = self.get_user_by_username(username)
        if not user:
            self.login_tracker.record_attempt(username, ip_address)
            return False, '用户名或密码错误', None
        
        if user['status'] != 1:
            return False, '账户已被禁用', None
        
        if self.password_hasher.verify_password(user['password'], password):
            self.login_tracker.reset_attempts(username, ip_address)
            return True, '登录成功', user
        
        self.login_tracker.record_attempt(username, ip_address)
        attempts_left = settings.MAX_LOGIN_ATTEMPTS - self.login_tracker.get_attempt_count(username, ip_address)
        if attempts_left <= 0:
            return False, '账户已被锁定，请15分钟后再试', None
        return False, f'用户名或密码错误，还剩{attempts_left}次尝试机会', None
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> tuple[bool, str]:
        valid, errors = PasswordPolicy.validate(new_password)
        if not valid:
            return False, ', '.join(errors)
        
        conn = self.db.get_connection()
        try:
            user = self.db.select_one(conn, 'users', where_clause='id = ?', where_params=(user_id,))
            if not user:
                return False, '用户不存在'
            
            if not self.password_hasher.verify_password(user['password'], old_password):
                return False, '原密码错误'
            
            new_hash = self.password_hasher.hash_password(new_password)
            self.db.update(conn, 'users', {'password': new_hash}, 'id = ?', (user_id,))
            conn.commit()
            return True, '密码修改成功'
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()
    
    def update_balance(self, user_id: int, amount: float) -> bool:
        conn = self.db.get_connection()
        try:
            user = self.db.select_one(conn, 'users', where_clause='id = ?', where_params=(user_id,))
            if not user:
                return False
            
            new_balance = user.get('balance', 0) + amount
            self.db.update(conn, 'users', {'balance': new_balance}, 'id = ?', (user_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_api_keys(self, user_id: int) -> list:
        conn = self.db.get_connection()
        try:
            return self.db.select(conn, 'api_keys', where_clause='user_id = ?', where_params=(user_id,), order_by='id DESC')
        finally:
            conn.close()
    
    def create_api_key(self, user_id: int, name: str = '新密钥') -> Optional[str]:
        conn = self.db.get_connection()
        try:
            key = 'sk-' + str(uuid.uuid4()).replace("-", "")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            key_data = {
                'user_id': user_id,
                'key': key,
                'name': name[:50],
                'status': 1,
                'created_at': now
            }
            
            self.db.insert(conn, 'api_keys', key_data)
            conn.commit()
            return key
        except Exception as e:
            conn.rollback()
            return None
        finally:
            conn.close()
    
    def toggle_api_key(self, key_id: int, user_id: int) -> bool:
        conn = self.db.get_connection()
        try:
            key_info = self.db.select_one(conn, 'api_keys', where_clause='id = ? AND user_id = ?', where_params=(key_id, user_id))
            if not key_info:
                return False
            
            new_status = 0 if key_info['status'] == 1 else 1
            self.db.update(conn, 'api_keys', {'status': new_status}, 'id = ?', (key_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_api_key(self, key_id: int, user_id: int) -> bool:
        conn = self.db.get_connection()
        try:
            self.db.delete(conn, 'api_keys', 'id = ? AND user_id = ?', (key_id, user_id))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
