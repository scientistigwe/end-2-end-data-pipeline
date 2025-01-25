# backend/config/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import logging
import os
from typing import Tuple

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration and initialization."""

    def __init__(self, app_config=None):
        self.app_config = app_config
        self.engine = None
        self.SessionLocal = None

    def init_db(self) -> Tuple[any, scoped_session]:
        """Initialize database connection and session management."""
        try:
            # Construct database URL with strict validation
            db_user = os.getenv('DB_USER')
            db_password = os.getenv('DB_PASSWORD')
            db_host = os.getenv('DB_HOST', 'localhost')
            db_port = int(os.getenv('DB_PORT', '5432'))  # Default PostgreSQL port
            db_name = os.getenv('DB_NAME')

            # Validate required parameters
            if not all([db_user, db_password, db_name]):
                raise ValueError("Missing required database configuration parameters")

            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            # Create engine with connection pooling
            self.engine = create_engine(
                db_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_pre_ping=True
            )

            # Create session factory
            session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            self.SessionLocal = scoped_session(session_factory)

            # Import and create tables
            from db.models import Base
            Base.metadata.create_all(bind=self.engine)

            logger.info("Database initialized successfully")
            return self.engine, self.SessionLocal

        except ValueError as ve:
            logger.error(f"Database configuration error: {str(ve)}")
            raise

        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            raise

    def get_session(self):
        """Get a database session."""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self.SessionLocal()

    def cleanup(self):
        """Cleanup database resources."""
        if self.SessionLocal:
            self.SessionLocal.remove()