# test_db_setup.py
from sqlalchemy import create_engine, inspect
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_db_setup():
    try:
        # Create engine
        engine = create_engine("postgresql://postgres:mercy@localhost:5432/enterprise_pipeline_db")

        # Import models
        from backend.database.models import Base
        from backend.database.models.auth import User

        # Create inspector
        inspector = inspect(engine)

        # Get existing tables
        existing_tables = inspector.get_table_names()
        logger.info(f"Existing tables: {existing_tables}")

        # Create tables
        if 'users' not in existing_tables:
            logger.info("Creating users table...")
            Base.metadata.tables['users'].create(bind=engine)

        logger.info("Creating remaining tables...")
        Base.metadata.create_all(bind=engine)

        # Verify foreign keys
        for table_name in inspector.get_table_names():
            foreign_keys = inspector.get_foreign_keys(table_name)
            logger.info(f"Foreign keys for {table_name}: {foreign_keys}")

        return True
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_db_setup()