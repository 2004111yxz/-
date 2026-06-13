import json
import threading
from datetime import datetime
from typing import Dict, Generator, Optional

from src.utils.database import Database
from src.config.settings import settings
from src.adapters.base_adapter import BaseModelAdapter
from src.services.model_service import ModelService

class ChatService:
    def __init__(self):
        self.db = Database(settings.DATABASE_URL, settings.DATABASE_PATH)
        self.model_service = ModelService()
    
    def chat_completion(self, user_id: int, model_name: str, body: Dict) -> tuple[bool, Dict, str]:
        model_config = self.model_service.get_model_by_name(model_name)
        if not model_config:
            return False, {}, f'Model {model_name} not available'
        
        adapter = self.model_service.get_adapter(model_name)
        if not adapter:
            return False, {}, 'Failed to get adapter'
        
        try:
            user = self._get_user(user_id)
            if not user:
                return False, {}, 'User not found'
            
            if user.get('balance', 0) < 0.001:
                return False, {}, 'Insufficient balance'
            
            response = adapter.generate(body)
            usage = adapter.parse_usage(response)
            
            cost = adapter.get_cost(usage['prompt_tokens'], usage['completion_tokens'])
            
            self._record_log(user_id, model_name, usage['prompt_tokens'], usage['completion_tokens'], cost)
            self._deduct_balance(user_id, cost)
            
            return True, response, ''
        except Exception as e:
            return False, {}, str(e)
    
    def chat_completion_stream(self, user_id: int, model_name: str, body: Dict) -> Generator[str, None, None]:
        model_config = self.model_service.get_model_by_name(model_name)
        if not model_config:
            yield f"data: {json.dumps({'error': {'message': f'Model {model_name} not available'}})}\n\n"
            return
        
        adapter = self.model_service.get_adapter(model_name)
        if not adapter:
            yield f"data: {json.dumps({'error': {'message': 'Failed to get adapter'}})}\n\n"
            return
        
        user = self._get_user(user_id)
        if not user:
            yield f"data: {json.dumps({'error': {'message': 'User not found'}})}\n\n"
            return
        
        if user.get('balance', 0) < 0.001:
            yield f"data: {json.dumps({'error': {'message': 'Insufficient balance'}})}\n\n"
            return
        
        prompt_tokens = 0
        completion_tokens = 0
        full_content = ""
        
        try:
            for chunk in adapter.generate_stream(body):
                yield chunk
                
                if chunk.startswith('data: '):
                    data_str = chunk[6:].strip()
                    if data_str != '[DONE]':
                        try:
                            data = json.loads(data_str)
                            if 'usage' in data:
                                prompt_tokens = data['usage'].get('prompt_tokens', 0)
                                completion_tokens = data['usage'].get('completion_tokens', 0)
                            if 'choices' in data and len(data['choices']) > 0:
                                delta = data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    full_content += delta['content']
                        except json.JSONDecodeError:
                            pass
            
            if not completion_tokens and full_content:
                completion_tokens = max(len(full_content) // 4, 1)
            
            cost = adapter.get_cost(prompt_tokens, completion_tokens)
            
            def update_cost_async():
                try:
                    thread_db = Database(settings.DATABASE_URL, settings.DATABASE_PATH)
                    thread_conn = thread_db.get_connection()
                    try:
                        thread_db.update(thread_conn, 'users', {'balance': user.get('balance', 0) - cost}, 'id = ?', (user_id,))
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        thread_db.insert(thread_conn, 'logs', {
                            'user_id': user_id,
                            'model': model_name,
                            'prompt_tokens': prompt_tokens,
                            'completion_tokens': completion_tokens,
                            'cost': cost,
                            'created_at': now
                        })
                        thread_conn.commit()
                    finally:
                        thread_conn.close()
                except Exception as e:
                    pass
            
            threading.Thread(target=update_cost_async, daemon=True).start()
            
        except Exception as e:
            yield f"data: {json.dumps({'error': {'message': str(e)[:100]}})}\n\n"
    
    def _get_user(self, user_id: int) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            return self.db.select_one(conn, 'users', where_clause='id = ? AND status = 1', where_params=(user_id,))
        finally:
            conn.close()
    
    def _record_log(self, user_id: int, model: str, prompt_tokens: int, completion_tokens: int, cost: float):
        conn = self.db.get_connection()
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_data = {
                'user_id': user_id,
                'model': model,
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'cost': cost,
                'created_at': now
            }
            self.db.insert(conn, 'logs', log_data)
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()
    
    def _deduct_balance(self, user_id: int, cost: float):
        conn = self.db.get_connection()
        try:
            user = self.db.select_one(conn, 'users', where_clause='id = ?', where_params=(user_id,))
            if user:
                new_balance = user.get('balance', 0) - cost
                self.db.update(conn, 'users', {'balance': new_balance}, 'id = ?', (user_id,))
                conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()
    
    def get_logs(self, user_id: int, limit: int = 50) -> list:
        conn = self.db.get_connection()
        try:
            return self.db.select(conn, 'logs', where_clause='user_id = ?', where_params=(user_id,), 
                                 order_by='id DESC', limit=limit)
        finally:
            conn.close()
    
    def get_all_logs(self, limit: int = 100) -> list:
        conn = self.db.get_connection()
        try:
            query = """
                SELECT logs.*, users.username 
                FROM logs LEFT JOIN users ON logs.user_id = users.id 
                ORDER BY logs.id DESC LIMIT ?
            """
            return self.db.execute_query(conn, query, (limit,), fetch='all')
        finally:
            conn.close()
