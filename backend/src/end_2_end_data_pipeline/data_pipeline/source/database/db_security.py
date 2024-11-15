from datetime import datetime
from typing import List, Dict, Any
from cryptography.fernet import Fernet
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import DatabaseError
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_types import DatabaseType
import os


class DataSecurityManager:
    """Data encryption and decryption operations"""

    def __init__(self):
        self._fernet = None
        self.setup_encryption()

    def setup_encryption(self) -> None:
        """Set up encryption using environment key"""
        try:
            key = os.environ.get('DB_ENCRYPTION_KEY')
            if not key:
                key = Fernet.generate_key()
                os.environ['DB_ENCRYPTION_KEY'] = key.decode()
            self._fernet = Fernet(key if isinstance(key, bytes) else key.encode())

        except Exception as e:
            raise DatabaseError(f"Encryption setup failed: {str(e)}")

    def _format_datetime(self, dt: Any) -> str:
        """Ensure datetime is formatted correctly"""
        # If it's a string, we don't need to format it, return as is
        if isinstance(dt, str):
            return dt
        # If it's a datetime object, convert to string using isoformat
        elif isinstance(dt, datetime):
            return dt.isoformat()
        else:
            raise ValueError("Invalid type for datetime")

    def encrypt(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Encrypt data"""
        return [
            {
                'id': self._fernet.encrypt(str(item['id']).encode()).decode(),
                'table_name': self._fernet.encrypt(item['table_name'].encode()).decode(),
                'data_type': self._fernet.encrypt(item['data_type'].encode()).decode(),
                'last_updated': self._fernet.encrypt(
                    self._format_datetime(item['last_updated']).encode()).decode()
        # Use _format_datetime here
        }
            for item in data
        ]

    def decrypt(self, encrypted_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Decrypt encrypted data"""
        try:
            decrypted_items = []
            for item in encrypted_data:
                decrypted_item = {
                    'id': int(self._fernet.decrypt(item['id'].encode()).decode()),
                    'table_name': self._fernet.decrypt(item['table_name'].encode()).decode(),
                    'data_type': self._fernet.decrypt(item['data_type'].encode()).decode(),
                    'last_updated': datetime.fromisoformat(
                        self._fernet.decrypt(item['last_updated'].encode()).decode()
                    )
                }
                decrypted_items.append(decrypted_item)
            return decrypted_items

        except Exception as e:
            raise DatabaseError(f"Decryption failed: {str(e)}")

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string, handling both formats with and without microseconds"""
        try:
            # Try parsing with microseconds using isoformat style
            return datetime.fromisoformat(dt_str)
        except ValueError:
            # If it fails, parse without microseconds
            return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')