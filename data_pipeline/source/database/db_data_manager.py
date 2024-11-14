from typing import Any, Tuple, Optional
import pandas as pd
from data_pipeline.exceptions import (
    DatabaseConnectionError, DataEncodingError, DataValidationError
)
from data_pipeline.source.database.db_connector import DBConnector
from data_pipeline.source.database.db_security import DataSecurityManager
from data_pipeline.source.database.db_config import DatabaseConfig

class DBDataManager:
    """Manages database operations with security and validation"""

    def __init__(self, db_type: str, **connection_params):
        """
        Initialize the data manager

        Args:
            db_type: Type of database
            **connection_params: Connection parameters from DatabaseConfig
        """
        self.db_connector = DBConnector(db_type, **connection_params)
        self.data_security_manager = DataSecurityManager()
        self.db_validator = DatabaseValidator()

    def validate_and_load(self, query: str) -> pd.DataFrame:
        """
        Validate connection and load data

        Args:
            query: SQL query or MongoDB filter

        Returns:
            DataFrame with query results

        Raises:
            DatabaseConnectionError: If connection validation fails
        """
        is_valid, error = self.db_validator.validate_connection(self.db_connector)
        if not is_valid:
            raise DatabaseConnectionError(f"Connection validation failed: {error}")

        with self.db_connector:
            return self.db_connector.load_data(query)

    def encrypt_and_transmit_data(self, data: pd.DataFrame) -> bytes:
        """
        Encrypt data for transmission

        Args:
            data: DataFrame to encrypt

        Returns:
            Encrypted data as bytes
        """
        serialized_data = data.to_json()
        return self.data_security_manager.encrypt_data(serialized_data)


class DatabaseValidator:
    """Validates database connections and operations"""

    def validate_connection(self, connector: DBConnector) -> Tuple[bool, str]:
        """
        Validate database connection

        Args:
            connector: DBConnector instance

        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        try:
            connector.connect()
            return True, ""
        except Exception as e:
            return False, str(e)
        finally:
            connector.disconnect()