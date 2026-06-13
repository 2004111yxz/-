from typing import Dict, List, Optional

from src.utils.database import Database
from src.config.settings import settings
from src.adapters.adapter_factory import AdapterFactory
from src.adapters.base_adapter import BaseModelAdapter

class ModelService:
    def __init__(self):
        self.db = Database(settings.DATABASE_URL, settings.DATABASE_PATH)
    
    def get_models(self, status: int = 1) -> List[Dict]:
        conn = self.db.get_connection()
        try:
            if status is None:
                return self.db.select(conn, 'models', order_by='sort ASC')
            return self.db.select(conn, 'models', where_clause='status = ?', where_params=(status,), order_by='sort ASC')
        finally:
            conn.close()
    
    def get_model_by_name(self, model_name: str) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            return self.db.select_one(conn, 'models', where_clause='name = ? AND status = 1', where_params=(model_name,))
        finally:
            conn.close()
    
    def get_model_by_id(self, model_id: int) -> Optional[Dict]:
        conn = self.db.get_connection()
        try:
            return self.db.select_one(conn, 'models', where_clause='id = ?', where_params=(model_id,))
        finally:
            conn.close()
    
    def create_model(self, name: str, display_name: str, base_url: str, api_key: str, 
                     input_price: float, output_price: float) -> bool:
        conn = self.db.get_connection()
        try:
            existing = self.db.select_one(conn, 'models', where_clause='name = ?', where_params=(name,))
            if existing:
                return False
            
            model_data = {
                'name': name,
                'display_name': display_name or name,
                'base_url': base_url,
                'api_key': api_key,
                'input_price': input_price,
                'output_price': output_price,
                'status': 1,
                'sort': 0
            }
            
            self.db.insert(conn, 'models', model_data)
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def update_model(self, model_id: int, data: Dict) -> bool:
        conn = self.db.get_connection()
        try:
            self.db.update(conn, 'models', data, 'id = ?', (model_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def toggle_model(self, model_id: int) -> bool:
        conn = self.db.get_connection()
        try:
            model = self.db.select_one(conn, 'models', where_clause='id = ?', where_params=(model_id,))
            if not model:
                return False
            
            new_status = 0 if model['status'] == 1 else 1
            self.db.update(conn, 'models', {'status': new_status}, 'id = ?', (model_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_model(self, model_id: int) -> bool:
        conn = self.db.get_connection()
        try:
            self.db.delete(conn, 'models', 'id = ?', (model_id,))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_adapter(self, model_name: str) -> Optional[BaseModelAdapter]:
        model_config = self.get_model_by_name(model_name)
        if not model_config:
            return None
        return AdapterFactory.get_adapter(model_config)
