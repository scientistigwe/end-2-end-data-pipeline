from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_connector import DatabaseConnector
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_data_loader import DatabaseLoader
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_security import DataSecurityManager
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_types import DatabaseType
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import DatabaseError
import pandas as pd


@dataclass
class DBData:
    """Represents data stored in the database"""
    id: int
    table_name: str
    data_type: DatabaseType
    last_updated: datetime


class DBDataManager:
    """Database data management operations"""

    def __init__(self, connector: DatabaseConnector):
        self.connector = connector
        self.loader = DatabaseLoader(connector)
        self.security_manager = DataSecurityManager()

    def get_data(self, db_config: Dict[str, Any]) -> List[DBData]:
        """Get data from database"""
        try:
            with self.connector.get_connection() as conn:
                data = self._get_data_from_db(conn, db_config)
                return self.decrypt_data(data)
        except Exception as e:
            raise DatabaseError(f"Failed to get data: {str(e)}", e)

    def _get_data_from_db(self, connection: Any, db_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get data from specific database"""
        table_name = db_config['table_name']
        query = f"SELECT * FROM {table_name} ORDER BY last_updated DESC LIMIT 100"
        df = self.loader.load_data(query)

        return [
            {
                'id': row['id'],
                'table_name': table_name,
                'data_type': db_config['data_type'],
                'last_updated': row['last_updated']
            }
            for _, row in df.iterrows()
        ]

    def validate_data(self, data: List[DBData]) -> None:
        """
        Validate database data integrity by checking the actual database records.

        Args:
            data: List of DBData objects to validate

        Raises:
            DatabaseError: If validation fails
        """
        try:
            if not data:
                raise DatabaseError("No data to validate.")

            with self.connector.get_connection():
                for item in data:
                    # Basic field validation
                    if not item.id or not item.last_updated:
                        raise DatabaseError(f"Data integrity issue: Missing required fields for record {item.id}")

                    # Query the database to verify the record exists
                    query = f"SELECT * FROM {item.table_name} WHERE id = {item.id}"
                    df = self.loader.load_data(query)

                    # Verify the record exists in the database
                    if df.empty:
                        raise DatabaseError(
                            f"Data integrity issue: Record {item.id} not found in table {item.table_name}")

        except Exception as e:
            raise DatabaseError(f"Failed to validate data: {str(e)}") from e

    def encrypt_data(self, data: List[DBData]) -> List[Dict[str, Any]]:
        """Encrypt database data"""
        try:
            return self.security_manager.encrypt([{
                'id': item.id,
                'table_name': item.table_name,
                'data_type': str(item.data_type),  # Convert enum to string for encryption
                'last_updated': item.last_updated.isoformat()
            } for item in data])
        except Exception as e:
            raise DatabaseError(f"Failed to encrypt data: {str(e)}", e)

    def decrypt_data(self, encrypted_data: List[Dict[str, Any]]) -> List[DBData]:
        """Decrypt database data"""
        try:
            decrypted_data = self.security_manager.decrypt(encrypted_data)
            return [
                DBData(
                    id=item['id'],
                    table_name=item['table_name'],
                    data_type=item['data_type'],  # Convert string back to enum
                    last_updated=datetime.fromisoformat(str(item['last_updated']))
                )
                for item in decrypted_data
            ]
        except Exception as e:
            raise DatabaseError(f"Failed to decrypt data: {str(e)}", e)