import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'moran-ai-platform-2024-stable-version')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    DATABASE_URL = os.environ.get('DATABASE_URL')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'platform.db')
    
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'MoRan')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'yangyang')
    
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15
    
    ARGON2_TIME_COST = int(os.environ.get('ARGON2_TIME_COST', 3))
    ARGON2_MEMORY_COST = int(os.environ.get('ARGON2_MEMORY_COST', 65536))
    ARGON2_PARALLELISM = int(os.environ.get('ARGON2_PARALLELISM', 4))

settings = Settings()
