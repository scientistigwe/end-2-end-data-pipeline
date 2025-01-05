# backend/flask_api/app/services/data_sources/database_service.py

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from contextlib import contextmanager
from .base_service import BaseSourceService
from .....database.models.data_source import DataSource, DatabaseSourceConfig
from datetime import datetime

class DatabaseSourceService(BaseSourceService):
    source_type = 'database'

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self._engine_registry: Dict[UUID, Engine] = {}

    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and validate database connection."""
        try:
            # Validate configuration
            validation_result = self.validate_config(data)
            if validation_result.status == 'failed':
                raise ValueError(f"Invalid database configuration: {validation_result.details}")

            # Test connection before creating records
            engine = self._create_engine(data)
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))

            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='pending',
                config={
                    'dialect': data['dialect'],
                    'host': data['host'],
                    'port': data['port'],
                    'database': data['database']
                }
            )

            # Create database config
            db_config = DatabaseSourceConfig(
                source=source,
                dialect=data['dialect'],
                schema=data.get('schema'),
                pool_size=data.get('pool_size', 5),
                max_overflow=data.get('max_overflow', 10),
                pool_timeout=data.get('pool_timeout', 30),
                pool_recycle=data.get('pool_recycle', 1800),
                ssl_config=data.get('ssl_config', {}),
                connection_args=data.get('connection_args', {})
            )

            source.status = 'active'
            self.db_session.add(source)
            self.db_session.add(db_config)
            self.db_session.commit()

            # Store engine in registry
            self._engine_registry[source.id] = engine

            return self._format_source(source)
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def execute_query(self, source_id: UUID, query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute database query with safety checks."""
        try:
            source = self._get_source_or_error(source_id)
            db_config = source.db_config

            # Validate query
            if not self._is_safe_query(query):
                raise ValueError("Query contains unsafe operations")

            engine = self._get_engine(source)
            with engine.connect() as conn:
                result = conn.execute(text(query), parameters=params or {})
                
                if result.returns_rows:
                    columns = result.keys()
                    rows = [dict(zip(columns, row)) for row in result.fetchall()]
                    return {
                        "columns": columns,
                        "rows": rows,
                        "row_count": len(rows)
                    }
                return {
                    "affected_rows": result.rowcount
                }
        except Exception as e:
            self.logger.error(f"Query execution error: {str(e)}")
            raise

    def get_schema(self, source_id: UUID) -> Dict[str, Any]:
        """Get database schema information."""
        try:
            source = self._get_source_or_error(source_id)
            engine = self._get_engine(source)
            inspector = inspect(engine)

            schemas = {}
            for schema_name in inspector.get_schema_names():
                tables = {}
                for table_name in inspector.get_table_names(schema=schema_name):
                    columns = []
                    for column in inspector.get_columns(table_name, schema=schema_name):
                        columns.append({
                            "name": column['name'],
                            "type": str(column['type']),
                            "nullable": column['nullable'],
                            "default": str(column['default']) if column['default'] else None,
                            "primary_key": column.get('primary_key', False)
                        })
                    
                    foreign_keys = []
                    for fk in inspector.get_foreign_keys(table_name, schema=schema_name):
                        foreign_keys.append({
                            "referred_schema": fk['referred_schema'],
                            "referred_table": fk['referred_table'],
                            "referred_columns": fk['referred_columns'],
                            "constrained_columns": fk['constrained_columns']
                        })
                    
                    indexes = []
                    for idx in inspector.get_indexes(table_name, schema=schema_name):
                        indexes.append({
                            "name": idx['name'],
                            "unique": idx['unique'],
                            "columns": idx['column_names']
                        })
                    
                    tables[table_name] = {
                        "columns": columns,
                        "foreign_keys": foreign_keys,
                        "indexes": indexes
                    }
                
                schemas[schema_name] = tables

            return {"schemas": schemas}
        except Exception as e:
            self.logger.error(f"Schema fetch error: {str(e)}")
            raise

    def list_sources(self) -> List[DataSource]:
        """
        List all database data sources.
        
        Returns:
            List[DataSource]: List of all database data sources
        """
        try:
            return (self.db_session.query(DataSource)
                    .filter(DataSource.type == self.source_type)
                    .all())
        except Exception as exc:
            self.logger.error(f"Error listing database sources: {str(exc)}")
            raise
        
    def _validate_source_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate database source configuration."""
        errors = []
        required_fields = ['dialect', 'host', 'port', 'database', 'username']
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        if 'port' in config:
            try:
                port = int(config['port'])
                if not 1 <= port <= 65535:
                    errors.append("Port must be between 1 and 65535")
            except ValueError:
                errors.append("Port must be a valid integer")

        valid_dialects = ['postgresql', 'mysql', 'oracle', 'mssql']
        if 'dialect' in config and config['dialect'] not in valid_dialects:
            errors.append(f"Invalid dialect. Must be one of: {', '.join(valid_dialects)}")

        return errors

    def _test_source_connection(self, source: DataSource) -> Dict[str, Any]:
        """Test database connection and return metrics."""
        engine = self._get_engine(source)
        start_time = datetime.utcnow()

        with engine.connect() as conn:
            version = conn.execute(text(self._get_version_query(source.db_config.dialect))).scalar()
            
            # Get database size
            size_query = self._get_database_size_query(source.db_config.dialect, source.config['database'])
            if size_query:
                size = conn.execute(text(size_query)).scalar()
            else:
                size = None

        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000

        return {
            "response_time_ms": response_time,
            "version": version,
            "database_size_bytes": size,
            "dialect": source.db_config.dialect
        }

    def _sync_source_data(self, source: DataSource) -> Dict[str, Any]:
        """Sync database metadata and statistics."""
        engine = self._get_engine(source)
        inspector = inspect(engine)
        
        total_tables = 0
        total_rows = 0
        schema_stats = {}

        for schema in inspector.get_schema_names():
            tables = inspector.get_table_names(schema=schema)
            schema_stats[schema] = {
                'table_count': len(tables),
                'tables': {}
            }
            
            for table in tables:
                total_tables += 1
                row_count = self._get_table_row_count(engine, schema, table)
                total_rows += row_count
                schema_stats[schema]['tables'][table] = {
                    'row_count': row_count
                }

        return {
            "records_processed": total_rows,
            "bytes_processed": None,  # Database-specific size calculation
            "table_count": total_tables,
            "schema_stats": schema_stats
        }

    def _get_source_preview(self, source: DataSource, limit: int) -> List[Dict[str, Any]]:
        """Get preview of database tables."""
        engine = self._get_engine(source)
        inspector = inspect(engine)
        preview_data = []

        for schema in inspector.get_schema_names():
            for table in inspector.get_table_names(schema=schema):
                query = text(f'SELECT * FROM {schema}.{table} LIMIT :limit')
                with engine.connect() as conn:
                    result = conn.execute(query, {'limit': limit})
                    columns = result.keys()
                    rows = [dict(zip(columns, row)) for row in result.fetchall()]
                    
                    preview_data.append({
                        'schema': schema,
                        'table': table,
                        'columns': columns,
                        'sample_data': rows
                    })

        return preview_data

    def _disconnect_source(self, source: DataSource) -> None:
        """Close database connection and clean up resources."""
        if source.id in self._engine_registry:
            engine = self._engine_registry[source.id]
            engine.dispose()
            del self._engine_registry[source.id]

    def _create_engine(self, config: Dict[str, Any]) -> Engine:
        """Create SQLAlchemy engine with connection pooling."""
        connection_url = self._build_connection_url(config)
        
        engine_args = {
            'poolclass': QueuePool,
            'pool_size': config.get('pool_size', 5),
            'max_overflow': config.get('max_overflow', 10),
            'pool_timeout': config.get('pool_timeout', 30),
            'pool_recycle': config.get('pool_recycle', 1800)
        }

        if config.get('ssl_config'):
            engine_args['connect_args'] = {'ssl': config['ssl_config']}

        return create_engine(connection_url, **engine_args)

    def _get_engine(self, source: DataSource) -> Engine:
        """Get or create database engine for source."""
        if source.id not in self._engine_registry:
            config = {
                'dialect': source.db_config.dialect,
                'host': source.config['host'],
                'port': source.config['port'],
                'database': source.config['database'],
                'username': source.config['username'],
                'password': source.config['password'],
                'ssl_config': source.db_config.ssl_config,
                'pool_size': source.db_config.pool_size,
                'max_overflow': source.db_config.max_overflow,
                'pool_timeout': source.db_config.pool_timeout,
                'pool_recycle': source.db_config.pool_recycle
            }
            self._engine_registry[source.id] = self._create_engine(config)
        
        return self._engine_registry[source.id]

    def _build_connection_url(self, config: Dict[str, Any]) -> str:
        """Build database connection URL."""
        dialect = config['dialect']
        username = config['username']
        password = config['password']
        host = config['host']
        port = config['port']
        database = config['database']
        
        return f"{dialect}://{username}:{password}@{host}:{port}/{database}"

    def _is_safe_query(self, query: str) -> bool:
        """Check if query is safe to execute."""
        unsafe_keywords = [
            'DROP', 'TRUNCATE', 'DELETE', 'UPDATE', 'INSERT', 
            'ALTER', 'CREATE', 'GRANT', 'REVOKE'
        ]
        
        query_upper = query.upper()
        return not any(keyword in query_upper for keyword in unsafe_keywords)

    def _get_version_query(self, dialect: str) -> str:
        """Get database-specific version query."""
        version_queries = {
            'postgresql': 'SELECT version()',
            'mysql': 'SELECT version()',
            'oracle': 'SELECT * FROM v$version WHERE banner LIKE \'Oracle%\'',
            'mssql': 'SELECT @@VERSION'
        }
        return version_queries.get(dialect, 'SELECT 1')

    def _get_database_size_query(self, dialect: str, database: str) -> Optional[str]:
        """Get database-specific size query."""
        size_queries = {
            'postgresql': f"SELECT pg_database_size('{database}')",
            'mysql': f"SELECT SUM(data_length + index_length) FROM information_schema.tables WHERE table_schema = '{database}'",
            'oracle': "SELECT sum(bytes) FROM dba_segments",
            'mssql': f"SELECT SUM(size * 8 * 1024) FROM sys.master_files WHERE name = '{database}'"
        }
        return size_queries.get(dialect)

    def _get_table_row_count(self, engine: Engine, schema: str, table: str) -> int:
        """Get row count for a specific table."""
        query = text(f'SELECT COUNT(*) FROM {schema}.{table}')
        with engine.connect() as conn:
            return conn.execute(query).scalar()