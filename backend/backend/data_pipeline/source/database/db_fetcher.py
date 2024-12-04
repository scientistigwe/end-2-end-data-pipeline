# db_fetcher.py
import pandas as pd
from typing import Dict, Any, Generator, Optional
import logging
from sqlalchemy import create_engine, text
from .db_config import Config

logger = logging.getLogger(__name__)


class DBFetcher:
    """Handle database data fetching operations"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize database connection"""
        self.config = config
        self.engine = self._create_engine()

    def _create_engine(self):
        """Create SQLAlchemy engine with configuration"""
        connection_string = Config.build_connection_string(self.config)
        return create_engine(
            connection_string,
            pool_size=Config.MAX_POOL_SIZE,
            max_overflow=Config.MAX_OVERFLOW,
            pool_timeout=Config.POOL_TIMEOUT,
            pool_recycle=Config.POOL_RECYCLE
        )

    def fetch_data(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute query and fetch data"""
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(
                    text(query),
                    conn,
                    params=params
                )

            return {
                'data': df,
                'row_count': len(df),
                'columns': list(df.columns)
            }
        except Exception as e:
            logger.error(f"Database fetch error: {str(e)}")
            raise

    def fetch_in_chunks(self, query: str, params: Optional[Dict] = None) -> Generator[pd.DataFrame, None, None]:
        """Fetch large datasets in chunks"""
        try:
            with self.engine.connect() as conn:
                for chunk in pd.read_sql(
                        text(query),
                        conn,
                        params=params,
                        chunksize=Config.CHUNK_SIZE
                ):
                    yield chunk
        except Exception as e:
            logger.error(f"Chunk fetch error: {str(e)}")
            raise

    def get_schema_info(self, schema: str) -> Dict[str, Any]:
        """Get schema metadata"""
        try:
            with self.engine.connect() as conn:
                tables = pd.read_sql(text(
                    """
                    SELECT table_name, column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = :schema
                    ORDER BY table_name, ordinal_position
                    """
                ), conn, params={"schema": schema})

            return {
                'schema': schema,
                'tables': tables.to_dict(orient='records'),
                'table_count': len(tables['table_name'].unique())
            }
        except Exception as e:
            logger.error(f"Schema info error: {str(e)}")
            raise

    def close(self):
        """Close database connection"""
        try:
            self.engine.dispose()
        except Exception as e:
            logger.error(f"Connection close error: {str(e)}")
            raise