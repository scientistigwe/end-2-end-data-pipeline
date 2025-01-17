# scripts/test_db.py
import logging
from sqlalchemy import create_engine, inspect, text
from backend.docs.analyst_pa.backend.config import get_config
from backend.db.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_database_connection():
    """Test db connection and table structure"""
    try:
        # Get config
        config = get_config('development')

        # Create engine
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI)

        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"Connected to PostgreSQL version: {version}")

        # Get table information
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")

        # Get expected tables
        expected_tables = {table.name for table in Base.metadata.sorted_tables}
        logger.info(f"Expected tables: {expected_tables}")

        # Check for missing tables
        missing_tables = expected_tables - set(existing_tables)
        if missing_tables:
            logger.warning(f"Missing tables: {missing_tables}")

        # Check table details
        for table_name in existing_tables:
            columns = inspector.get_columns(table_name)
            logger.info(f"\nTable: {table_name}")
            logger.info("Columns:")
            for column in columns:
                logger.info(f"  - {column['name']}: {column['type']}")

            # Check foreign keys
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                logger.info("Foreign Keys:")
                for fk in fks:
                    logger.info(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

        return True

    except Exception as e:
        logger.error(f"Database test failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_database_connection()