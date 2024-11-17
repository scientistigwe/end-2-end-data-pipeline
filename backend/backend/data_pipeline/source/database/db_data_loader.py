from typing import Union, Dict, Any
import pandas as pd
from backend.backend.data_pipeline.exceptions import DatabaseQueryError
from .db_connector import DatabaseConnector
from .db_types import DatabaseType


class DatabaseLoader:
    """Database data loading operations"""

    def __init__(self, connector: DatabaseConnector):
        self.connector = connector

    def load_data(
            self,
            query: Union[str, Dict[str, Any]],
            params: Dict[str, Any] = None
    ) -> pd.DataFrame:
        """Load data from database into DataFrame"""
        try:
            with self.connector.get_connection() as conn:
                if self.connector.config.db_type in (
                        DatabaseType.POSTGRESQL,
                        DatabaseType.MYSQL
                ):
                    return self._load_sql_data(query, params, conn)
                elif self.connector.config.db_type == DatabaseType.MONGODB:
                    return self._load_mongo_data(query, conn)
        except Exception as e:
            raise DatabaseQueryError(f"Failed to load data: {str(e)}", e)

    def _load_sql_data(
            self,
            query: str,
            params: Dict[str, Any],
            connection: Any
    ) -> pd.DataFrame:
        """Load data from SQL database"""
        # Always pass params to read_sql_query, even if None
        return pd.read_sql_query(query, connection, params=params)

    def _load_mongo_data(
            self,
            query: Dict[str, Any],
            connection: Any
    ) -> pd.DataFrame:
        """Load data from MongoDB"""
        collection = query.get('collection', 'default')
        filter_dict = query.get('filter', {})
        projection = query.get('projection', None)

        db = connection[self.connector.config.database]
        cursor = db[collection].find(filter_dict, projection)
        return pd.DataFrame(list(cursor))
