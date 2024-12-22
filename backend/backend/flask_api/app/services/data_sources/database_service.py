# backend/flask_api/app/services/data_sources/database_service.py

from typing import Dict, Any
from sqlalchemy import create_engine, inspect
from .....database.models.data_source import DataSource, DatabaseSourceConfig
from .base_service import BaseSourceService


class DatabaseSourceService(BaseSourceService):
    source_type = 'database'

    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create database connection and source."""
        try:
            # Test connection
            engine = create_engine(data['connection_string'])
            with engine.connect() as conn:
                conn.execute('SELECT 1')
            
            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='active',
                config={
                    'dialect': data['dialect'],
                    'connection_string': data['connection_string']
                }
            )
            
            # Create database config
            db_config = DatabaseSourceConfig(
                source=source,
                dialect=data['dialect'],
                schema=data.get('schema'),
                pool_size=data.get('pool_size', 5)
            )
            
            self.db_session.add(source)
            self.db_session.add(db_config)
            self.db_session.commit()
            
            return self._format_source(source)
        except Exception as e:
            self.logger.error(f"Database connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def get_schema(self, connection_id: str) -> Dict[str, Any]:
        """Get database schema."""
        try:
            source = self.db_session.query(DataSource).get(connection_id)
            if not source:
                raise ValueError("Database source not found")

            engine = create_engine(source.config['connection_string'])
            inspector = inspect(engine)
            
            return {
                'tables': [
                    {
                        'name': table_name,
                        'columns': [
                            {
                                'name': col['name'],
                                'type': str(col['type']),
                                'nullable': col['nullable']
                            }
                            for col in inspector.get_columns(table_name)
                        ]
                    }
                    for table_name in inspector.get_table_names()
                ]
            }
        except Exception as e:
            self.logger.error(f"Schema fetch error: {str(e)}")
            raise