# db_validator.py
from typing import Tuple, Dict, Any
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from .db_config import Config

logger = logging.getLogger(__name__)


class DBValidator:
    """Database validation utilities"""

    @staticmethod
    def validate_connection(engine: Engine) -> Tuple[bool, str]:
        """Validate database connection"""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Database connection successful"
        except Exception as e:
            return False, f"Database connection failed: {str(e)}"

    @staticmethod
    def validate_query(engine: Engine, query: str) -> Tuple[bool, str]:
        """Validate SQL query"""
        try:
            # Check if query is SELECT
            if not query.strip().upper().startswith('SELECT'):
                return False, "Only SELECT queries are allowed"

            # Validate query execution
            with engine.connect() as conn:
                conn.execute(text(query))
            return True, "Query validation successful"
        except Exception as e:
            return False, f"Query validation failed: {str(e)}"

    @staticmethod
    def validate_schema_access(engine: Engine, schema: str) -> Tuple[bool, str]:
        """Validate schema access permissions"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(
                    "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
                ), {"schema": schema})
                if result.scalar():
                    return True, "Schema access validated"
                return False, f"Schema {schema} not found or not accessible"
        except Exception as e:
            return False, f"Schema validation failed: {str(e)}"

