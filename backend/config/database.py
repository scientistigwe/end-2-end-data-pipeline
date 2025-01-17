# backend/config/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def init_db(app):
    """Initialize db connection and session management."""
    try:
        # Get credentials from environment variables
        db_url = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

        # Create engine with connection pooling
        engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_pre_ping=True
        )

        # Create session factory
        session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False
        )
        SessionLocal = scoped_session(session_factory)

        # Import and create tables
        from backend.db.models import Base
        Base.metadata.create_all(bind=engine)

        logger.info("Database initialized successfully")
        return engine, SessionLocal

    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise