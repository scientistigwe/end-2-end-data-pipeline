from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator, List, Union
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
import aiopg  # For PostgreSQL
import aiomysql  # For MySQL
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.rate_limiter import AsyncRateLimiter
from .db_config import Config

logger = logging.getLogger(__name__)


@dataclass
class FetchContext:
    """Context for database fetch operations"""
    operation_id: str
    query: str
    start_time: datetime = field(default_factory=datetime.now)
    rows_processed: int = 0
    total_chunks: Optional[int] = None
    chunks_processed: int = 0
    status: str = "pending"
    error: Optional[str] = None


class DBFetcher:
    """Enhanced database fetcher with comprehensive capabilities"""

    def __init__(
            self,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize fetcher with configuration"""
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="db_fetcher",
            source_id="fetcher"
        )

        # Initialize rate limiter
        self.rate_limiter = AsyncRateLimiter(
            max_calls=self.config.MAX_CONCURRENT_QUERIES,
            period=1.0
        )

        # Engine and connection tracking
        self.engine = None
        self.pool = None
        self._engine_lock = asyncio.Lock()

        # Operation tracking
        self.active_operations: Dict[str, FetchContext] = {}

        # Connection time
        self.created_at = datetime.now()

        # Statistics
        self.stats = {
            'queries_executed': 0,
            'rows_processed': 0,
            'errors': 0,
            'total_duration': 0
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_engine()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_engine(self):
        """Ensure database engine exists"""
        async with self._engine_lock:
            if not self.engine:
                self.engine = await self._create_engine()
                self.pool = await self._create_connection_pool()

    async def _create_engine(self):
        """Create async SQLAlchemy engine"""
        db_type = self.config.DATABASE_TYPE.lower()

        if db_type == 'postgresql':
            driver = 'postgresql+asyncpg'
        elif db_type == 'mysql':
            driver = 'mysql+aiomysql'
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

        connection_string = self.config.build_connection_string(driver)

        return create_async_engine(
            connection_string,
            pool_size=self.config.MAX_POOL_SIZE,
            max_overflow=self.config.MAX_OVERFLOW,
            pool_timeout=self.config.POOL_TIMEOUT,
            pool_recycle=self.config.POOL_RECYCLE,
            echo=self.config.DEBUG
        )

    async def _create_connection_pool(self):
        """Create connection pool based on database type"""
        if self.config.DATABASE_TYPE.lower() == 'postgresql':
            return await aiopg.create_pool(
                dsn=self.config.build_connection_string('postgresql'),
                minsize=1,
                maxsize=self.config.MAX_POOL_SIZE,
                timeout=self.config.POOL_TIMEOUT
            )
        elif self.config.DATABASE_TYPE.lower() == 'mysql':
            return await aiomysql.create_pool(
                **self.config.get_mysql_config(),
                minsize=1,
                maxsize=self.config.MAX_POOL_SIZE
            )
        else:
            raise ValueError(f"Unsupported database type: {self.config.DATABASE_TYPE}")

    async def fetch_data_async(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None,
            chunk_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch data from database asynchronously

        Args:
            query: SQL query to execute
            params: Query parameters
            chunk_size: Optional chunk size for large results

        Returns:
            Dictionary containing query results and metadata
        """
        try:
            await self._ensure_engine()

            # Create fetch context
            context = FetchContext(
                operation_id=f"fetch_{datetime.now().timestamp()}",
                query=query
            )

            self.active_operations[context.operation_id] = context

            # Record start metrics
            await self.process_monitor.record_metric(
                'query_execution_start',
                1,
                query_type=self._get_query_type(query)
            )

            try:
                if chunk_size or self._should_use_chunks(query):
                    # Fetch in chunks
                    all_data = []
                    async for chunk in self.fetch_in_chunks_async(
                            query, params, chunk_size or self.config.CHUNK_SIZE
                    ):
                        all_data.append(chunk)

                    # Combine chunks
                    df = pd.concat(all_data, ignore_index=True)

                else:
                    # Direct fetch for smaller queries
                    df = await self._execute_query(query, params)

                # Update context
                context.status = "completed"
                context.rows_processed = len(df)

                # Record completion metrics
                duration = (datetime.now() - context.start_time).total_seconds()
                await self.process_monitor.record_operation_metric(
                    'query_execution',
                    success=True,
                    duration=duration,
                    rows_processed=len(df)
                )

                # Update statistics
                self.stats['queries_executed'] += 1
                self.stats['rows_processed'] += len(df)
                self.stats['total_duration'] += duration

                return {
                    'data': df,
                    'metadata': {
                        'row_count': len(df),
                        'columns': list(df.columns),
                        'execution_time': duration
                    }
                }

            except Exception as e:
                context.status = "error"
                context.error = str(e)
                self.stats['errors'] += 1
                raise

            finally:
                # Cleanup operation context
                if context.operation_id in self.active_operations:
                    del self.active_operations[context.operation_id]

        except Exception as e:
            logger.error(f"Data fetch error: {str(e)}")
            await self.process_monitor.record_error(
                'query_execution_error',
                error=str(e)
            )
            raise

    async def fetch_in_chunks_async(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None,
            chunk_size: int = None
    ) -> AsyncGenerator[pd.DataFrame, None]:
        """
        Fetch large datasets in chunks asynchronously

        Args:
            query: SQL query to execute
            params: Query parameters
            chunk_size: Number of rows per chunk

        Yields:
            DataFrame chunks
        """
        chunk_size = chunk_size or self.config.CHUNK_SIZE

        try:
            async with self.engine.connect() as conn:
                # Execute query
                result = await conn.stream(
                    text(query),
                    params or {}
                )

                chunk = []
                async for row in result:
                    chunk.append(dict(row))

                    if len(chunk) >= chunk_size:
                        yield pd.DataFrame(chunk)
                        chunk = []

                # Yield remaining rows
                if chunk:
                    yield pd.DataFrame(chunk)

        except Exception as e:
            logger.error(f"Chunk fetch error: {str(e)}")
            await self.process_monitor.record_error(
                'chunk_fetch_error',
                error=str(e)
            )
            raise

    async def _execute_query(
            self,
            query: str,
            params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """Execute single query"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text(query), params or {})
            rows = await result.fetchall()
            if not rows:
                return pd.DataFrame()
            return pd.DataFrame([dict(row) for row in rows])

    def _should_use_chunks(self, query: str) -> bool:
        """Determine if query should use chunked fetching"""
        query_upper = query.upper()
        # Check for patterns indicating large result sets
        return any(
            pattern in query_upper
            for pattern in ['GROUP BY', 'ORDER BY', 'DISTINCT']
        )

    def _get_query_type(self, query: str) -> str:
        """Determine query type"""
        query = query.strip().upper()
        if query.startswith('SELECT'):
            if 'GROUP BY' in query:
                return 'aggregate'
            elif 'JOIN' in query:
                return 'join'
            else:
                return 'select'
        elif query.startswith('WITH'):
            return 'cte'
        elif query.startswith('SHOW') or query.startswith('DESCRIBE'):
            return 'metadata'
        else:
            return 'unknown'

    async def get_schema_info_async(
            self,
            schema: str
    ) -> Dict[str, Any]:
        """Get schema metadata asynchronously"""
        try:
            await self._ensure_engine()

            async with self.engine.connect() as conn:
                # Get tables
                table_query = """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = :schema
                ORDER BY table_name, ordinal_position
                """

                result = await conn.execute(
                    text(table_query),
                    {'schema': schema}
                )
                tables = await result.fetchall()

                # Get views
                view_query = """
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = :schema
                """

                result = await conn.execute(
                    text(view_query),
                    {'schema': schema}
                )
                views = await result.fetchall()

                return {
                    'schema': schema,
                    'tables': [dict(row) for row in tables],
                    'views': [dict(row) for row in views],
                    'table_count': len(set(row['table_name'] for row in tables)),
                    'view_count': len(views)
                }

        except Exception as e:
            logger.error(f"Schema info error: {str(e)}")
            await self.process_monitor.record_error(
                'schema_info_error',
                error=str(e)
            )
            raise

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            'created_at': self.created_at.isoformat(),
            'uptime_seconds': (datetime.now() - self.created_at).total_seconds(),
            'queries_executed': self.stats['queries_executed'],
            'rows_processed': self.stats['rows_processed'],
            'errors': self.stats['errors'],
            'avg_query_duration': (
                self.stats['total_duration'] / self.stats['queries_executed']
                if self.stats['queries_executed'] > 0
                else 0
            ),
            'active_operations': len(self.active_operations)
        }

    async def close(self):
        """Close database connection and cleanup resources"""
        try:
            # Close all active operations
            for operation_id in list(self.active_operations.keys()):
                context = self.active_operations[operation_id]
                if context.status == "pending":
                    context.status = "cancelled"
                    context.error = "Connection closed"

            self.active_operations.clear()

            # Close connection pool
            if self.pool:
                self.pool.close()
                await self.pool.wait_closed()

            # Dispose engine
            if self.engine:
                await self.engine.dispose()

            # Record final metrics
            await self.process_monitor.record_metric(
                'connection_close',
                1,
                duration=(datetime.now() - self.created_at).total_seconds(),
                queries_executed=self.stats['queries_executed']
            )

        except Exception as e:
            logger.error(f"Connection close error: {str(e)}")
            await self.process_monitor.record_error(
                'connection_close_error',
                error=str(e)
            )
            raise