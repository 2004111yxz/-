import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from src.utils.database import Database
from src.config.settings import settings

class TaskStatus(Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'

class VideoService:
    def __init__(self):
        self.db = Database(settings.DATABASE_URL, settings.DATABASE_PATH)
    
    def init_tables(self):
        conn = self.db.get_connection()
        try:
            self.db.execute_query(conn, '''
                CREATE TABLE IF NOT EXISTS video_tasks (
                    id SERIAL PRIMARY KEY,
                    task_id TEXT UNIQUE NOT NULL,
                    user_id INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    negative_prompt TEXT,
                    style TEXT,
                    duration REAL,
                    resolution TEXT,
                    reference_url TEXT,
                    extra_params TEXT,
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    result_url TEXT,
                    error_message TEXT,
                    webhook_url TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            conn.commit()
        finally:
            conn.close()
    
    def create_task(self, user_id: int, prompt: str, negative_prompt: str = None, 
                    style: str = None, duration: float = None, resolution: str = None,
                    reference_url: str = None, extra_params: Dict = None,
                    webhook_url: str = None) -> str:
        task_id = 'vt-' + str(uuid.uuid4()).replace("-", "")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = self.db.get_connection()
        try:
            task_data = {
                'task_id': task_id,
                'user_id': user_id,
                'prompt': prompt,
                'negative_prompt': negative_prompt or '',
                'style': style or '',
                'duration': duration or 0,
                'resolution': resolution or '',
                'reference_url': reference_url or '',
                'extra_params': str(extra_params) if extra_params else '',
                'status': TaskStatus.PENDING.value,
                'progress': 0,
                'result_url': '',
                'error_message': '',
                'webhook_url': webhook_url or '',
                'created_at': now,
                'updated_at': now
            }
            
            self.db.insert(conn, 'video_tasks', task_data)
            conn.commit()
            return task_id
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            return self.db.select_one(conn, 'video_tasks', where_clause='task_id = ?', where_params=(task_id,))
        finally:
            conn.close()
    
    def get_user_tasks(self, user_id: int, limit: int = 50) -> list:
        conn = self.db.get_connection()
        try:
            return self.db.select(conn, 'video_tasks', where_clause='user_id = ?', where_params=(user_id,),
                                 order_by='id DESC', limit=limit)
        finally:
            conn.close()
    
    def update_task_status(self, task_id: str, status: TaskStatus, progress: int = None,
                           result_url: str = None, error_message: str = None):
        conn = self.db.get_connection()
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if progress is not None:
                update_data['progress'] = progress
            if result_url:
                update_data['result_url'] = result_url
            if error_message:
                update_data['error_message'] = error_message
            
            self.db.update(conn, 'video_tasks', update_data, 'task_id = ?', (task_id,))
            conn.commit()
            
            if status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                self._notify_webhook(task_id)
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def cancel_task(self, task_id: str) -> bool:
        conn = self.db.get_connection()
        try:
            task = self.db.select_one(conn, 'video_tasks', where_clause='task_id = ?', where_params=(task_id,))
            if not task:
                return False
            
            if task['status'] not in [TaskStatus.PENDING.value, TaskStatus.PROCESSING.value]:
                return False
            
            self.db.update(conn, 'video_tasks', {
                'status': TaskStatus.CANCELLED.value,
                'updated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, 'task_id = ?', (task_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _notify_webhook(self, task_id: str):
        import requests
        
        task = self.get_task(task_id)
        if not task or not task.get('webhook_url'):
            return
        
        try:
            payload = {
                'task_id': task['task_id'],
                'status': task['status'],
                'result_url': task.get('result_url'),
                'error_message': task.get('error_message'),
                'created_at': task['created_at'],
                'updated_at': task['updated_at']
            }
            
            requests.post(task['webhook_url'], json=payload, timeout=10)
        except Exception:
            pass
