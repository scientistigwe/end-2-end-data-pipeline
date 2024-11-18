from contextlib import contextmanager
from typing import Generator, Any
import psycopg2
import pymysql
import pymongo
from backend.data_pipeline.exceptions import DatabaseConnectionError, DatabaseError
from .db_config import DatabaseConfig
from .db_types import DatabaseType

class DatabaseConnector:
    """Database connection manager"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection = None

    def connect(self) -> Any:
        """Establish database connection."""
        try:
            connection = self._create_connection()
            self._connection = connection
            return connection
        except Exception as e:
            raise DatabaseConnectionError(f"Connection failed: {str(e)}", e)

    def disconnect(self) -> None:
        """Close database connection safely"""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass  # Ignore errors during disconnection
        self._connection = None

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Get database connection as context manager"""
        try:
            # If no connection exists, establish one
            if not self._connection:
                self.connect()

            yield self._connection
        except DatabaseConnectionError as e:
            # Raise connection error with additional context
            raise DatabaseConnectionError(f"Connection failed: {str(e)}", e)
        except Exception as e:
            # Propagate other exceptions without altering them
            raise e
        finally:
            self.disconnect()

    def _create_connection(self) -> Any:
        """Create appropriate database connection"""
        params = self.config.get_connection_params()

        try:
            if self.config.db_type == DatabaseType.POSTGRESQL:
                return psycopg2.connect(**params)
            elif self.config.db_type == DatabaseType.MYSQL:
                return pymysql.connect(**params)
            elif self.config.db_type == DatabaseType.MONGODB:
                return pymongo.MongoClient(**params)
        except Exception as e:
            raise DatabaseConnectionError(
                f"Failed to connect to {self.config.db_type.name}: {str(e)}", e
            )
