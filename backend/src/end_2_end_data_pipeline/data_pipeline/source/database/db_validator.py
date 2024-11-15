# DatabaseValidator.py
from typing import Dict, Any
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_connector import DatabaseConnector
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_security import DataSecurityManager
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_types import DatabaseType
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import DatabaseConnectionError, DatabaseError
import sqlparse

class DatabaseValidator:
    def __init__(self, connector: DatabaseConnector, security_manager: DataSecurityManager):
        self.connector = connector
        self.security_manager = security_manager

    def validate_connection(self) -> None:
        try:
            with self.connector.get_connection() as conn:
                self._validate_db_type(conn)
                self._validate_query_structure(conn)
        except Exception as e:
            raise DatabaseConnectionError(f"Database connection validation failed: {str(e)}") from e

    def _validate_db_type(self, connection: Any) -> None:
        db_type = self.connector.config.db_type
        if db_type == DatabaseType.POSTGRESQL:
            self._validate_postgresql(connection)
        elif db_type == DatabaseType.MYSQL:
            self._validate_mysql(connection)
        elif db_type == DatabaseType.MONGODB:
            self._validate_mongodb(connection)
        else:
            raise DatabaseError(f"Unsupported database type: {db_type.name}")

    def _validate_connection_params(self, connection: Any) -> None:
        params = self.connector.config.get_connection_params()
        required_params = ['host', 'port', 'database', 'username']
        if not all(param in params for param in required_params):
            raise DatabaseError("Database connection parameter validation failed: Missing required parameters")

        if self.connector.config.db_type != DatabaseType.MONGODB and ('port' not in params or not isinstance(params['port'], int)):
            raise DatabaseError("Database connection parameter validation failed: Invalid port value")

    def _validate_postgresql(self, connection: Any) -> None:
        self._validate_connection_params(connection)

    def _validate_mysql(self, connection: Any) -> None:
        self._validate_connection_params(connection)

    def _validate_mongodb(self, connection: Any) -> None:
        self._validate_connection_params(connection)

    def _validate_query_structure(self, connection: Any) -> None:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                if result != (1,):
                    raise DatabaseError("Database query structure validation failed: Failed to execute test query")

                sql = cursor.connection.query
                formatted_sql = sqlparse.format(sql, reindent=True, keyword_case='upper')
                if "UNION" in formatted_sql.upper():
                    raise DatabaseError("Database query structure validation failed: SQL injection detected")
        except DatabaseError as de:
            raise de
        except Exception as e:
            raise DatabaseError(f"Database query structure validation failed: {str(e)}") from e