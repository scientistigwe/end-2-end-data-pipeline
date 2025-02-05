# backend/config/database.py

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import event

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Database configuration with enhanced async support and connection pooling."""

    def __init__(self, app_config):
        self.app_config = app_config
        self.engine = None
        self._session_factory = None
        self._active_sessions = set()

    async def init_db(self) -> None:
        """Initialize database with async support and connection pooling."""
        try:
            # Normalize database URL for asyncpg
            db_url = self.app_config.SQLALCHEMY_DATABASE_URI
            if not db_url.startswith('postgresql+asyncpg://'):
                db_url = db_url.replace('postgresql://', 'postgresql+asyncpg://')

            # Get pool settings with defaults
            pool_size = getattr(self.app_config, 'SQLALCHEMY_POOL_SIZE', 5)
            max_overflow = getattr(self.app_config, 'SQLALCHEMY_MAX_OVERFLOW', 10)
            pool_timeout = getattr(self.app_config, 'SQLALCHEMY_POOL_TIMEOUT', 30)
            isolation_level = getattr(self.app_config, 'SQLALCHEMY_ISOLATION_LEVEL', 'READ_COMMITTED')

            # Create async engine with optimized settings
            self.engine = create_async_engine(
                db_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
                pool_pre_ping=True,
                pool_use_lifo=True,
                echo=self.app_config.SQLALCHEMY_ECHO,
                isolation_level=isolation_level
            )

            # Initialize async session factory with optimized settings
            self._session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )

            # Import and create tables if they don't exist
            from db.models.base import Base
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            # Setup event listeners for connection pool
            @event.listens_for(self.engine.sync_engine, 'connect')
            def on_connect(dbapi_connection, connection_record):
                logger.info("New database connection established")

            @event.listens_for(self.engine.sync_engine, 'checkout')
            def on_checkout(dbapi_connection, connection_record, connection_proxy):
                logger.debug("Database connection checked out from pool")

            @event.listens_for(self.engine.sync_engine, 'checkin')
            def on_checkin(dbapi_connection, connection_record):
                logger.debug("Database connection returned to pool")

            logger.info("Database initialized successfully")

        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            await self.cleanup()
            raise

    @property
    def async_session(self) -> async_sessionmaker[AsyncSession]:
        """Property to access the async session factory."""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init_db() first.")
        return self._session_factory

    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Return the session factory (alias for compatibility)."""
        return self.async_session

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async session with proper context management"""
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init_db() first.")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def cleanup(self) -> None:
        """Cleanup database resources properly"""
        try:
            if self.engine:
                await self.engine.dispose()
            self._session_factory = None
            logger.info("Database resources cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Perform a health check on the database connection.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            async with self.get_session() as session:
                await session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    async def reset_pool(self) -> None:
        """
        Reset the connection pool if needed.
        """
        try:
            if self.engine:
                await self.engine.dispose()
                await self.init_db()
                logger.info("Connection pool reset successfully")
        except Exception as e:
            logger.error(f"Failed to reset connection pool: {str(e)}")
            raise

    @property
    def pool_status(self) -> dict:
        """
        Get current status of the connection pool.

        Returns:
            dict: Pool status information
        """
        if not self.engine:
            return {"status": "not_initialized"}

        return {
            "size": self.engine.pool.size(),
            "checkedin": self.engine.pool.checkedin(),
            "overflow": self.engine.pool.overflow(),
            "checkedout": self.engine.pool.checkedout(),
            "active_sessions": len(self._active_sessions)
        }

    async def execute_in_transaction(self, operations):
        """
        Execute multiple database operations in a transaction.

        Args:
            operations: Async callable that takes a session parameter

        Returns:
            The result of the operations
        """
        async with self.get_session() as session:
            async with session.begin():
                return await operations(session)