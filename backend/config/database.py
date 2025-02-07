# backend/core/database.py

from typing import AsyncGenerator, Optional, Any, Dict
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import event
from sqlalchemy.engine.url import make_url
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings
import logging
from datetime import datetime

from fastapi import FastAPI
from contextlib import asynccontextmanager as fastapi_lifespan

logger = logging.getLogger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration settings using Pydantic"""
    SQLALCHEMY_DATABASE_URI: PostgresDsn
    SQLALCHEMY_POOL_SIZE: int = 5
    SQLALCHEMY_MAX_OVERFLOW: int = 10
    SQLALCHEMY_POOL_TIMEOUT: int = 30
    SQLALCHEMY_ECHO: bool = False
    SQLALCHEMY_ISOLATION_LEVEL: str = "READ_COMMITTED"
    SQLALCHEMY_POOL_PRE_PING: bool = True
    SQLALCHEMY_POOL_USE_LIFO: bool = True

    class Config:
        case_sensitive = True


class DatabaseMetrics:
    """Class to track database performance metrics"""

    def __init__(self):
        self.connection_attempts: int = 0
        self.successful_connections: int = 0
        self.failed_connections: int = 0
        self.active_transactions: int = 0
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[datetime] = None
        self.average_query_time: float = 0.0
        self.total_queries: int = 0

    def record_connection_attempt(self, success: bool):
        self.connection_attempts += 1
        if success:
            self.successful_connections += 1
        else:
            self.failed_connections += 1

    def record_query_time(self, duration: float):
        self.total_queries += 1
        self.average_query_time = (
                (self.average_query_time * (self.total_queries - 1) + duration)
                / self.total_queries
        )


class DatabaseConfig:
    """Enhanced database configuration with FastAPI integration"""

    def __init__(self, settings: DatabaseSettings):
        self.settings = settings
        self.engine = None
        self._session_factory = None
        self._active_sessions = set()
        self.metrics = DatabaseMetrics()

    async def init_db(self) -> None:
        """Initialize database with enhanced async support"""
        try:
            # Normalize and validate database URL
            db_url = make_url(str(self.settings.SQLALCHEMY_DATABASE_URI))
            if db_url.drivername != 'postgresql+asyncpg':
                db_url = db_url.set(drivername='postgresql+asyncpg')

            # Create async engine with optimized settings
            self.engine = create_async_engine(
                db_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=self.settings.SQLALCHEMY_POOL_SIZE,
                max_overflow=self.settings.SQLALCHEMY_MAX_OVERFLOW,
                pool_timeout=self.settings.SQLALCHEMY_POOL_TIMEOUT,
                pool_pre_ping=self.settings.SQLALCHEMY_POOL_PRE_PING,
                pool_use_lifo=self.settings.SQLALCHEMY_POOL_USE_LIFO,
                echo=self.settings.SQLALCHEMY_ECHO,
                isolation_level=self.settings.SQLALCHEMY_ISOLATION_LEVEL,
                # Additional FastAPI-specific optimizations
                future=True,
                pool_recycle=3600,
                json_serializer=lambda obj: str(obj),
                connect_args={
                    "server_settings": {
                        "application_name": "fastapi_app",
                        "client_encoding": "utf8"
                    }
                }
            )

            # Initialize session factory with FastAPI optimizations
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False,
                future=True
            )

            # Setup enhanced event listeners
            self._setup_event_listeners()

            # Create tables
            from db.models.base import Base
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("Database initialized successfully with FastAPI configuration")

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            self.metrics.last_error = str(e)
            self.metrics.last_error_time = datetime.utcnow()
            await self.cleanup()
            raise

    def _setup_event_listeners(self):
        """Setup enhanced event listeners for monitoring"""

        @event.listens_for(self.engine.sync_engine, 'connect')
        def on_connect(dbapi_connection, connection_record):
            logger.info("New database connection established")
            self.metrics.record_connection_attempt(True)

        @event.listens_for(self.engine.sync_engine, 'checkout')
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            logger.debug("Database connection checked out from pool")
            connection_record.info['checkout_time'] = datetime.utcnow()

        @event.listens_for(self.engine.sync_engine, 'checkin')
        def on_checkin(dbapi_connection, connection_record):
            logger.debug("Database connection returned to pool")
            checkout_time = connection_record.info.get('checkout_time')
            if checkout_time:
                duration = (datetime.utcnow() - checkout_time).total_seconds()
                self.metrics.record_query_time(duration)

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Enhanced session context manager for FastAPI dependency injection"""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        session = self._session_factory()
        self._active_sessions.add(session)
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error: {str(e)}")
            self.metrics.last_error = str(e)
            self.metrics.last_error_time = datetime.utcnow()
            raise
        finally:
            self._active_sessions.remove(session)
            await session.close()

    async def get_db_session(self) -> AsyncGenerator[AsyncSession, None]:
        """FastAPI dependency for database sessions"""
        async with self.session() as session:
            yield session

    async def cleanup(self) -> None:
        """Enhanced cleanup with metrics reset"""
        try:
            if self.engine:
                await self.engine.dispose()
            self._session_factory = None
            self.metrics = DatabaseMetrics()
            logger.info("Database resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            raise

    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check with detailed status"""
        try:
            start_time = datetime.utcnow()
            async with self.session() as session:
                await session.execute("SELECT 1")
            response_time = (datetime.utcnow() - start_time).total_seconds()

            return {
                "status": "healthy",
                "response_time": response_time,
                "pool_status": self.pool_status,
                "metrics": {
                    "connections": {
                        "total": self.metrics.connection_attempts,
                        "successful": self.metrics.successful_connections,
                        "failed": self.metrics.failed_connections
                    },
                    "performance": {
                        "average_query_time": self.metrics.average_query_time,
                        "total_queries": self.metrics.total_queries
                    },
                    "last_error": {
                        "message": self.metrics.last_error,
                        "time": self.metrics.last_error_time
                    }
                }
            }
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow()
            }

    @property
    def pool_status(self) -> Dict[str, Any]:
        """Enhanced pool status information"""
        if not self.engine:
            return {"status": "not_initialized"}

        return {
            "size": self.engine.pool.size(),
            "checkedin": self.engine.pool.checkedin(),
            "overflow": self.engine.pool.overflow(),
            "checkedout": self.engine.pool.checkedout(),
            "active_sessions": len(self._active_sessions),
            "metrics": {
                "average_query_time": self.metrics.average_query_time,
                "active_transactions": self.metrics.active_transactions
            }
        }

    @fastapi_lifespan
    async def lifespan(self, app: FastAPI):
        """
        FastAPI lifespan context manager for database initialization and cleanup

        Usage:
        app = FastAPI(lifespan=db_config.lifespan)
        """
        try:
            # Initialize database connection
            await self.init_db()
            yield
        finally:
            # Cleanup database resources
            await self.cleanup()


# Create database settings and configuration
db_settings = DatabaseSettings()
db_config = DatabaseConfig(db_settings)


# Expose database session dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Global database session dependency for FastAPI routes

    Returns:
        AsyncGenerator of database sessions
    """
    async with db_config.session() as session:
        yield session