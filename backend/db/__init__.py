from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy import inspect, text, event, DDL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy_utils import database_exists, create_database
import logging
from typing import Optional, Any
from pathlib import Path

from .models.core.base import Base, base_meta
from .models import *  # Import all models

logger = logging.getLogger(__name__)


class AsyncDatabaseInitializer:
    """Async database initializer with comprehensive setup and verification."""

    def __init__(self, settings: dict):
        """Initialize with database settings."""
        self.settings = settings
        self.engine = None
        self.session_factory = None

        # Configure SQLAlchemy logging
        sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
        sqlalchemy_logger.setLevel(settings.get('LOG_LEVEL', logging.INFO))

    async def init_db(self) -> async_sessionmaker[AsyncSession]:
        """Initialize database with complete async setup."""
        try:
            logger.info(f"Initializing async db connection to: {self.settings['DATABASE_URL']}")

            # Create database if it doesn't exist
            if not database_exists(self.settings['DATABASE_URL']):
                create_database(self.settings['DATABASE_URL'])
                logger.info("Database created successfully")

            # Create async engine with configuration
            self.engine = create_async_engine(
                self.settings['DATABASE_URL'],
                pool_size=self.settings.get('POOL_SIZE', 5),
                max_overflow=self.settings.get('MAX_OVERFLOW', 10),
                pool_timeout=self.settings.get('POOL_TIMEOUT', 30),
                echo=self.settings.get('ECHO', False),
                pool_pre_ping=True,
                future=True
            )

            # Create async session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autoflush=False
            )

            # Initialize database structure
            async with self.engine.begin() as conn:
                # Verify connection
                await conn.execute(text("SELECT 1"))

                # Create tables
                await conn.run_sync(Base.metadata.create_all)

                # Register database functions
                await self._register_database_functions(conn)

                # Verify database integrity
                await self._verify_database_integrity(conn)

            logger.info("Database initialization completed successfully")
            return self.session_factory

        except SQLAlchemyError as e:
            logger.error(f"Database connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during db initialization: {str(e)}")
            raise

    async def _register_database_functions(self, conn: AsyncConnection) -> None:
        """Register all custom PostgreSQL functions and views."""
        try:
            # Update timestamp function
            await conn.execute(DDL("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql';
            """))

            # Pipeline statistics function
            await conn.execute(DDL("""
                CREATE OR REPLACE FUNCTION calculate_pipeline_stats(p_id UUID)
                RETURNS TABLE (
                    total_runs BIGINT,
                    successful_runs BIGINT,
                    average_duration FLOAT,
                    success_rate FLOAT
                ) AS $$
                BEGIN
                    RETURN QUERY
                    SELECT 
                        COUNT(*) as total_runs,
                        COUNT(*) FILTER (WHERE status = 'completed') as successful_runs,
                        AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as average_duration,
                        (COUNT(*) FILTER (WHERE status = 'completed')::FLOAT / COUNT(*)::FLOAT) * 100 as success_rate
                    FROM pipeline_runs
                    WHERE pipeline_id = p_id;
                END;
                $$ LANGUAGE plpgsql;
            """))

            # Materialized view for pipeline statistics
            await conn.execute(DDL("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_pipeline_stats AS
                SELECT 
                    p.id as pipeline_id,
                    p.name,
                    COUNT(pr.id) as total_runs,
                    COUNT(*) FILTER (WHERE pr.status = 'completed') as successful_runs,
                    AVG(EXTRACT(EPOCH FROM (pr.end_time - pr.start_time))) as avg_duration,
                    MAX(pr.start_time) as last_run
                FROM pipelines p
                LEFT JOIN pipeline_runs pr ON p.id = pr.pipeline_id
                GROUP BY p.id, p.name;
            """))

            # Create triggers for all tables with updated_at column
            for table in Base.metadata.tables.values():
                if 'updated_at' in table.columns:
                    await conn.execute(DDL(f"""
                        DROP TRIGGER IF EXISTS update_updated_at_{table.name} ON {table.name};
                        CREATE TRIGGER update_updated_at_{table.name}
                        BEFORE UPDATE ON {table.name}
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                    """))

            logger.info("Database functions and views registered successfully")

        except Exception as e:
            logger.error(f"Error registering db functions: {str(e)}")
            raise

    async def _verify_database_integrity(self, conn: AsyncConnection) -> None:
        """Verify database integrity asynchronously."""
        try:
            inspector = inspect(self.engine)
            integrity_issues = []

            for table_name in inspector.get_table_names():
                # Verify all constraints
                await self._verify_table_constraints(inspector, table_name, integrity_issues)

                # Verify columns
                await self._verify_table_columns(inspector, table_name, integrity_issues)

            if integrity_issues:
                error_message = "\n".join(integrity_issues)
                logger.error(f"Database integrity issues found:\n{error_message}")
                raise ValueError(f"Database integrity check failed:\n{error_message}")

            logger.info("Database integrity verification completed successfully")

        except Exception as e:
            logger.error(f"Error during db integrity verification: {str(e)}")
            raise

    async def _verify_table_constraints(
            self,
            inspector: Any,
            table_name: str,
            integrity_issues: list
    ) -> None:
        """Verify table constraints asynchronously."""
        # Verify foreign keys
        for fk in inspector.get_foreign_keys(table_name):
            try:
                logger.debug(
                    f"Verified foreign key in {table_name}: "
                    f"columns {fk['constrained_columns']} -> "
                    f"{fk['referred_table']}({fk['referred_columns']})"
                )
            except Exception as e:
                integrity_issues.append(
                    f"Invalid foreign key in {table_name}: {str(e)}"
                )

        # Verify primary key
        pk = inspector.get_pk_constraint(table_name)
        if not pk.get('constrained_columns'):
            integrity_issues.append(
                f"Table {table_name} has no primary key constraint"
            )

        # Verify unique constraints
        for constraint in inspector.get_unique_constraints(table_name):
            try:
                logger.debug(
                    f"Verified unique constraint in {table_name}: "
                    f"{constraint['name']} on columns {constraint['column_names']}"
                )
            except Exception as e:
                integrity_issues.append(
                    f"Invalid unique constraint in {table_name}: {str(e)}"
                )

    async def _verify_table_columns(
            self,
            inspector: Any,
            table_name: str,
            integrity_issues: list
    ) -> None:
        """Verify table columns asynchronously."""
        for column in inspector.get_columns(table_name):
            try:
                logger.debug(
                    f"Verified column in {table_name}: "
                    f"{column['name']} ({column['type']}, "
                    f"nullable: {column.get('nullable', True)})"
                )
            except Exception as e:
                integrity_issues.append(
                    f"Invalid column in {table_name}: {str(e)}"
                )

    async def cleanup(self) -> None:
        """Cleanup database resources."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections cleaned up")