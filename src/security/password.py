import re
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

class PasswordPolicy:
    MIN_LENGTH = 8
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGITS = True
    REQUIRE_SPECIAL = True
    
    @staticmethod
    def validate(password: str) -> tuple[bool, list[str]]:
        errors = []
        
        if len(password) < PasswordPolicy.MIN_LENGTH:
            errors.append(f"密码长度至少{PasswordPolicy.MIN_LENGTH}位")
        
        if PasswordPolicy.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("需要包含大写字母")
        
        if PasswordPolicy.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("需要包含小写字母")
        
        if PasswordPolicy.REQUIRE_DIGITS and not re.search(r'[0-9]', password):
            errors.append("需要包含数字")
        
        if PasswordPolicy.REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("需要包含特殊字符")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def calculate_strength(password: str) -> tuple[int, str]:
        score = 0
        
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if re.search(r'[a-z]', password):
            score += 1
        if re.search(r'[A-Z]', password):
            score += 1
        if re.search(r'[0-9]', password):
            score += 1
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            score += 1
        
        if score <= 2:
            return score, "弱"
        elif score <= 3:
            return score, "中"
        elif score <= 4:
            return score, "强"
        else:
            return score, "非常强"

class PasswordHasherService:
    def __init__(self, time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4):
        self.ph = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=32,
            salt_len=16
        )
    
    def hash_password(self, password: str) -> str:
        return self.ph.hash(password)
    
    def verify_password(self, hash: str, password: str) -> bool:
        try:
            return self.ph.verify(hash, password)
        except VerifyMismatchError:
            return False
        except Exception:
            return False
    
    def needs_rehash(self, hash: str) -> bool:
        return self.ph.needs_rehash(hash)

class LoginAttemptTracker:
    def __init__(self):
        self.attempts: dict[tuple[str, str], dict] = {}
    
    def record_attempt(self, username: str, ip_address: str):
        key = (username, ip_address)
        
        if key not in self.attempts:
            self.attempts[key] = {
                'count': 0,
                'first_attempt': None,
                'locked_until': None
            }
        
        self.attempts[key]['count'] += 1
        
        from datetime import datetime
        if self.attempts[key]['first_attempt'] is None:
            self.attempts[key]['first_attempt'] = datetime.now()
    
    def is_locked(self, username: str, ip_address: str, max_attempts: int = 5, lockout_minutes: int = 15) -> bool:
        from datetime import datetime, timedelta
        
        key = (username, ip_address)
        if key not in self.attempts:
            return False
        
        attempt_data = self.attempts[key]
        
        if attempt_data['locked_until'] is not None:
            if datetime.now() < attempt_data['locked_until']:
                return True
            else:
                self.reset_attempts(username, ip_address)
                return False
        
        if attempt_data['count'] >= max_attempts:
            attempt_data['locked_until'] = datetime.now() + timedelta(minutes=lockout_minutes)
            return True
        
        return False
    
    def reset_attempts(self, username: str, ip_address: str):
        key = (username, ip_address)
        if key in self.attempts:
            del self.attempts[key]
    
    def get_attempt_count(self, username: str, ip_address: str) -> int:
        key = (username, ip_address)
        return self.attempts.get(key, {}).get('count', 0)
