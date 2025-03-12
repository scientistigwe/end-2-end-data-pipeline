"""
Database Configuration Module

This module provides comprehensive database configuration and connection management
for FastAPI applications. It includes connection pooling, metrics tracking,
and session management.

Features:
    - Async database configuration
    - Connection pooling
    - Session management
    - Performance metrics
    - Health monitoring
    - Error tracking

Usage:
    from config.database import db_config, get_db_session

    async with get_db_session() as session:
        result = await session.execute("SELECT 1")
"""

from typing import AsyncGenerator, Optional, Any, Dict, Set, List, Callable, Union
from datetime import datetime
import logging
from contextlib import asynccontextmanager
from functools import wraps
import time
import asyncio

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy.engine.url import make_url, URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from pydantic import PostgresDsn, Field, field_validator
from pydantic_settings import BaseSettings

from .app_config import app_config, Config

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseSettings(BaseSettings):
    """Database connection and configuration settings."""

    # Database connection settings with default values for development
    DB_USER: str = Field(default="postgres", description="Database username")
    DB_PASSWORD: str = Field(default="postgres", description="Database password")
    DB_HOST: str = Field(default="localhost", description="Database host")
    DB_PORT: int = Field(default=5432, description="Database port")
    DB_NAME: str = Field(default="postgres", description="Database name")

    # Pool settings
    SQLALCHEMY_POOL_SIZE: int = Field(default=5, description="SQLAlchemy pool size")
    SQLALCHEMY_MAX_OVERFLOW: int = Field(default=10, description="Maximum pool overflow")
    SQLALCHEMY_POOL_TIMEOUT: int = Field(default=30, description="Pool timeout in seconds")
    SQLALCHEMY_ECHO: bool = Field(default=False, description="Echo SQL statements")
    SQLALCHEMY_ISOLATION_LEVEL: str = Field(
        default="READ_COMMITTED",
        description="Transaction isolation level"
    )
    SQLALCHEMY_POOL_PRE_PING: bool = Field(
        default=True,
        description="Enable pool pre-ping"
    )
    SQLALCHEMY_POOL_USE_LIFO: bool = Field(
        default=True,
        description="Use LIFO pool strategy"
    )

    # Computed DATABASE_URI
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_uri(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        """Assemble database URI from components."""
        if isinstance(v, str):
            return v

        # Make sure we have all required values
        required_values = ["DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME"]
        for value in required_values:
            if value not in values.data:
                raise ValueError(f"Missing required database configuration: {value}")

        try:
            return PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=values.data["DB_USER"],
                password=values.data["DB_PASSWORD"],
                host=values.data["DB_HOST"],
                port=values.data["DB_PORT"],
                path=f"/{values.data['DB_NAME']}"
            )
        except Exception as e:
            raise ValueError(f"Failed to build database URI: {str(e)}")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

class DatabaseMetrics:
    """Database performance metrics tracking."""

    def __init__(self):
        """Initialize metrics tracking."""
        self.connection_attempts: int = 0
        self.successful_connections: int = 0
        self.failed_connections: int = 0
        self.active_transactions: int = 0
        self.last_error: Optional[str] = None
        self.last_error_time: Optional[datetime] = None
        self.average_query_time: float = 0.0
        self.total_queries: int = 0
        self._query_times: List[float] = []
        self._max_query_times: int = 1000  # Keep last 1000 query times
        self._lock = asyncio.Lock()

    async def record_connection_attempt(self, success: bool) -> None:
        """Record connection attempt result."""
        async with self._lock:
            self.connection_attempts += 1
            if success:
                self.successful_connections += 1
            else:
                self.failed_connections += 1

    async def record_query_time(self, duration: float) -> None:
        """Record query execution time."""
        async with self._lock:
            self.total_queries += 1
            self._query_times.append(duration)

            if len(self._query_times) > self._max_query_times:
                self._query_times.pop(0)

            self.average_query_time = sum(self._query_times) / len(self._query_times)

    async def record_error(self, error: str) -> None:
        """Record database error."""
        async with self._lock:
            self.last_error = error
            self.last_error_time = datetime.utcnow()
            self.failed_connections += 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            'connection_attempts': self.connection_attempts,
            'successful_connections': self.successful_connections,
            'failed_connections': self.failed_connections,
            'active_transactions': self.active_transactions,
            'average_query_time': self.average_query_time,
            'total_queries': self.total_queries,
            'last_error': self.last_error,
            'last_error_time': self.last_error_time,
            'success_rate': (
                (self.successful_connections / self.connection_attempts * 100)
                if self.connection_attempts > 0 else 0
            )
        }


class DatabaseConfig:
    """Database configuration with FastAPI integration."""

    def __new__(cls):
        """Implement singleton pattern."""
        if not hasattr(cls, '_instance'):
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure(self, settings: Union[DatabaseSettings, Config]) -> None:
        """Configure database with settings."""
        self.settings = settings
        self.engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        self._active_sessions: Set[AsyncSession] = set()
        self.metrics = DatabaseMetrics()
        self._lock = asyncio.Lock()

        try:
            # Handle different config types
            if isinstance(settings, DatabaseSettings):
                self.uri = str(settings.SQLALCHEMY_DATABASE_URI)
            else:
                # Handle Config instance (DevelopmentConfig/ProductionConfig)
                if not hasattr(settings, 'SQLALCHEMY_DATABASE_URI'):
                    raise ValueError("Database URI not configured in settings")

                # Ensure URI uses the async driver
                uri = str(settings.SQLALCHEMY_DATABASE_URI)
                if not uri.startswith('postgresql+asyncpg://'):
                    uri = uri.replace('postgresql://', 'postgresql+asyncpg://')
                self.uri = uri

            # Set additional properties
            self.pool_size = getattr(settings, 'SQLALCHEMY_POOL_SIZE', 5)
            self.max_overflow = getattr(settings, 'SQLALCHEMY_MAX_OVERFLOW', 10)
            self.pool_timeout = getattr(settings, 'SQLALCHEMY_POOL_TIMEOUT', 30)
            self.echo = getattr(settings, 'SQLALCHEMY_ECHO', False)
            self.isolation_level = getattr(settings, 'SQLALCHEMY_ISOLATION_LEVEL', 'READ_COMMITTED')

            logger.info(f"Database configuration initialized with URI: {self.uri.split('@')[1] if '@' in self.uri else 'unknown'}")

        except Exception as e:
            logger.error(f"Failed to initialize database configuration: {str(e)}")
            raise

    def __init__(self):
        """Initialize database configuration."""
        self.settings = None
        self.engine = None
        self._session_factory = None
        self._active_sessions = set()
        self.metrics = DatabaseMetrics()
        self._lock = asyncio.Lock()
        self.uri = None
        self.pool_size = 5
        self.max_overflow = 10
        self.pool_timeout = 30
        self.echo = False
        self.isolation_level = "READ_COMMITTED"

    async def init_db(self) -> None:
        """Initialize database with engine and session factory."""
        if self._session_factory:
            logger.info("Database already initialized")
            return

        try:
            # Create async engine with settings from config
            if not self.engine:
                self.engine = create_async_engine(
                    self.uri,
                    # Remove poolclass as it's automatically handled for async engines
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_pre_ping=getattr(self.settings, 'SQLALCHEMY_POOL_PRE_PING', True),
                    pool_use_lifo=getattr(self.settings, 'SQLALCHEMY_POOL_USE_LIFO', True),
                    echo=self.echo,
                    isolation_level=self.isolation_level,
                    # Remove json_serializer as it's not needed for async engine
                    connect_args={
                        "server_settings": {
                            "application_name": "fastapi_app",
                            "client_encoding": "utf8",
                            "timezone": "UTC"
                        }
                    }
                )

            # Initialize session factory
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )

            # Test connection
            async with self._session_factory() as session:
                start_time = time.perf_counter()
                await session.execute(text("SELECT 1"))
                await session.commit()
                duration = time.perf_counter() - start_time

                await self.metrics.record_connection_attempt(True)
                await self.metrics.record_query_time(duration)

            logger.info("Database initialized successfully")

        except Exception as e:
            await self.metrics.record_error(str(e))
            logger.error(f"Database initialization failed: {str(e)}")
            await self.cleanup()
            raise

    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get the session factory."""
        if not self._session_factory:
            logger.error("Database session factory is None. Current state: "
                        f"Engine: {self.engine}, "
                        f"Active sessions: {len(self._active_sessions)}")
            raise RuntimeError("Database not initialized or was cleaned up. "
                             "Call init_db() first.")
        return self._session_factory

    @property
    def is_initialized(self) -> bool:
        return bool(self.engine and self._session_factory)

    async def ensure_initialized(self) -> None:
        if not self.is_initialized:
            await self.init_db()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with metrics tracking and validation."""
        if not self.is_initialized:
            await self.ensure_initialized()

        session = None
        try:
            async with self._lock:
                session = self._session_factory()
                self._active_sessions.add(session)
                self.metrics.active_transactions += 1
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Database session error: {e}")
            if session:
                await session.rollback()
            raise
        finally:
            if session:
                async with self._lock:
                    self._active_sessions.remove(session)
                    self.metrics.active_transactions -= 1
                await session.close()

    async def cleanup(self) -> None:
        """Cleanup database resources."""
        try:
            async with self._lock:
                # Close all active sessions
                for session in self._active_sessions:
                    await session.close()
                self._active_sessions.clear()

                # Dispose engine
                if self.engine:
                    await self.engine.dispose()

                self._session_factory = None
                logger.info("Database resources cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            raise

    def get_health_check(self) -> Dict[str, Any]:
        """Get database health check information."""
        metrics = self.metrics.get_metrics()
        engine_status = bool(self.engine and self._session_factory)

        return {
            'status': 'healthy' if engine_status else 'unhealthy',
            'engine_initialized': engine_status,
            'active_sessions': len(self._active_sessions),
            'metrics': metrics,
            'pool_size': self.settings.SQLALCHEMY_POOL_SIZE,
            'max_overflow': self.settings.SQLALCHEMY_MAX_OVERFLOW,
            'isolation_level': self.settings.SQLALCHEMY_ISOLATION_LEVEL
        }

# Create database settings and configuration
db_settings = DatabaseSettings()
db_config = DatabaseConfig()
db_config.configure(app_config)


def setup_database(app: FastAPI, settings: Optional[DatabaseSettings] = None) -> None:
    """Setup database for FastAPI application."""
    try:
        # Use provided settings or load from environment
        config_settings = settings or DatabaseSettings()

        # Configure database
        db_config.configure(config_settings)

        @app.on_event("startup")
        async def startup_db():
            """Initialize database on application startup."""
            try:
                await db_config.init_db()
                logger.info("Database initialized successfully")
            except Exception as e:
                logger.error(f"Database initialization failed: {str(e)}")
                raise

        @app.on_event("shutdown")
        async def shutdown_db():
            """Cleanup database resources on application shutdown."""
            await db_config.cleanup()

    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        raise

def track_query_time(func: Callable) -> Callable:
    """Decorator to track query execution time."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            await db_config.metrics.record_query_time(duration)
            return result
        except Exception as e:
            await db_config.metrics.record_error(str(e))
            raise
    return wrapper

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Global database session dependency for FastAPI routes."""
    async with db_config.session() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise

# Helper function to get a database session in routes
def get_session() -> AsyncSession:
    """Helper function to get database session dependency."""
    return Depends(get_db_session)