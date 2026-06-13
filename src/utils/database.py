import os
import sqlite3
from typing import Any, Dict, List, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

class Database:
    def __init__(self, database_url: Optional[str] = None, database_path: str = 'platform.db'):
        self.database_url = database_url
        self.database_path = database_path
        self.use_postgres = bool(database_url)
        
        if self.use_postgres and not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL 需要 psycopg2-binary，请安装: pip install psycopg2-binary")
    
    def get_connection(self):
        if self.use_postgres:
            conn = psycopg2.connect(self.database_url)
            conn.autocommit = False
            return conn
        else:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), self.database_path)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
    
    def execute_query(self, conn, query: str, params: Optional[tuple] = None, fetch: str = None) -> Any:
        if self.use_postgres:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            query = query.replace('AUTOINCREMENT', 'SERIAL')
            query = query.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
            query = query.replace('?', '%s')
            cursor.execute(query, params or ())
            
            if fetch == 'all':
                result = cursor.fetchall()
                cursor.close()
                return result
            elif fetch == 'one':
                result = cursor.fetchone()
                cursor.close()
                return result
            elif fetch == 'lastrowid':
                lastrowid = cursor.fetchone()[0] if cursor.description else None
                cursor.close()
                return lastrowid
            cursor.close()
            return None
        else:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            
            if fetch == 'all':
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in rows]
                cursor.close()
                return result
            elif fetch == 'one':
                row = cursor.fetchone()
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    result = dict(zip(columns, row))
                else:
                    result = None
                cursor.close()
                return result
            elif fetch == 'lastrowid':
                lastrowid = cursor.lastrowid
                cursor.close()
                return lastrowid
            cursor.close()
            return None
    
    def insert(self, conn, table: str, data: Dict[str, Any]) -> int:
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data)) if self.use_postgres else ', '.join(['?'] * len(data))
        query = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
        
        if self.use_postgres:
            query += " RETURNING id"
        
        return self.execute_query(conn, query, tuple(data.values()), fetch='lastrowid')
    
    def update(self, conn, table: str, data: Dict[str, Any], where_clause: str, where_params: tuple):
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()]) if self.use_postgres else ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        params = tuple(data.values()) + where_params
        self.execute_query(conn, query, params)
    
    def select(self, conn, table: str, columns: str = '*', where_clause: str = None, where_params: tuple = None, 
               order_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        query = f"SELECT {columns} FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        return self.execute_query(conn, query, where_params, fetch='all')
    
    def select_one(self, conn, table: str, columns: str = '*', where_clause: str = None, where_params: tuple = None) -> Optional[Dict[str, Any]]:
        query = f"SELECT {columns} FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        query += " LIMIT 1"
        
        return self.execute_query(conn, query, where_params, fetch='one')
    
    def delete(self, conn, table: str, where_clause: str, where_params: tuple):
        query = f"DELETE FROM {table} WHERE {where_clause}"
        self.execute_query(conn, query, where_params)
