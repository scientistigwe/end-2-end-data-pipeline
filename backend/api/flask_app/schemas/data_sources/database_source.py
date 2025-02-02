# schemas/data_sources/database_source.py
from marshmallow import fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from typing import Dict, Any

from ..staging.base import StagingRequestSchema, StagingResponseSchema


class DatabaseSourceRequestSchema(StagingRequestSchema):
    """Schema for database data source requests"""
    dialect = fields.String(required=True, validate=OneOf(['postgresql', 'mysql', 'oracle', 'mssql', 'sqlite']))
    host = fields.String(required=True)
    port = fields.Integer(required=True)
    database = fields.String(required=True)
    username = fields.String(required=True)
    password = fields.String(required=True, load_only=True)

    # Optional Configuration
    schema = fields.String(allow_none=True)
    ssl_config = fields.Dict(default=dict)
    pool_config = fields.Dict(default=lambda: {
        'pool_size': 5,
        'max_overflow': 10
    })
    timeout_config = fields.Dict(default=lambda: {
        'connect_timeout': 30,
        'query_timeout': 60
    })

    @validates_schema
    def validate_port_ranges(self, data: Dict[str, Any], **kwargs) -> None:
        port_ranges = {
            'postgresql': 5432,
            'mysql': 3306,
            'oracle': 1521,
            'mssql': 1433
        }
        if data['dialect'] in port_ranges and data['port'] != port_ranges[data['dialect']]:
            raise ValidationError(f"Non-standard port for {data['dialect']}")


class DatabaseSourceResponseSchema(StagingResponseSchema):
    """Schema for database data source responses"""
    connection_status = fields.String(validate=OneOf(['connected', 'disconnected', 'error']))
    available_tables = fields.List(fields.String())
    connection_pool_status = fields.Dict()
    query_performance_metrics = fields.Dict()
    last_successful_connection = fields.DateTime(allow_none=True)

class DBUploadRequestSchema(StagingRequestSchema):
   query = fields.String(required=True)
   params = fields.Dict()
   chunk_size = fields.Integer()
   transaction = fields.Boolean(default=False)

class DBUploadResponseSchema(StagingResponseSchema):
   rows_affected = fields.Integer()
   execution_time = fields.Float()
   transaction_id = fields.String()

class DBMetadataResponseSchema(StagingResponseSchema):
   table_schema = fields.Dict()
   column_types = fields.Dict()
   row_count = fields.Integer()
   indices = fields.List(fields.Dict())
   preview_data = fields.List(fields.Dict())


class DatabaseSourceConfigSchema(StagingRequestSchema):
    """Schema for database source configuration and validation"""
    # Connection Settings
    dialect = fields.String(required=True, validate=OneOf([
        'postgresql', 'mysql', 'oracle', 'mssql', 'sqlite'
    ]))
    host = fields.String(required=True)
    port = fields.Integer(required=True)
    database = fields.String(required=True)
    username = fields.String(required=True)
    password = fields.String(required=True, load_only=True)

    # Connection Pool Settings
    pool_config = fields.Dict(default=lambda: {
        'pool_size': 5,
        'max_overflow': 10,
        'pool_timeout': 30,
        'pool_recycle': 3600
    })

    # SSL Configuration
    ssl_config = fields.Dict(default=lambda: {
        'require': False,
        'verify_cert': True,
        'ca_cert': None,
        'client_cert': None,
        'client_key': None
    })

    # Query Settings
    query_config = fields.Dict(default=lambda: {
        'timeout': 30,
        'execution_options': {},
        'paramstyle': 'pyformat',
        'stream_results': False
    })

    # Schema Settings
    schema_config = fields.Dict(default=lambda: {
        'schema': 'public',
        'exclude_tables': [],
        'include_views': True
    })

    # Performance Settings
    performance_config = fields.Dict(default=lambda: {
        'statement_cache_size': 100,
        'max_row_buffer': 10000,
        'use_batch_mode': True
    })

    # Monitoring Settings
    monitoring_config = fields.Dict(default=lambda: {
        'log_statements': False,
        'collect_metrics': True,
        'slow_query_threshold': 1.0
    })

    @validates_schema
    def validate_database_config(self, data: Dict[str, Any], **kwargs) -> None:
        # Validate port numbers
        default_ports = {
            'postgresql': 5432,
            'mysql': 3306,
            'oracle': 1521,
            'mssql': 1433
        }
        if data['port'] != default_ports.get(data['dialect']):
            logger.warning(f"Non-standard port {data['port']} for {data['dialect']}")