# backend/flask_api/app/services/data_sources/base_service.py

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
from .....database.models.data_source import (
    DataSource, 
    APISourceConfig, 
    DatabaseSourceConfig,
    S3SourceConfig, 
    StreamSourceConfig, 
    FileSourceInfo,
    SourceConnection, 
    SourceSyncHistory,
)
from .....database.models.validation import ValidationResult

class BaseSourceService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.source_type: str = None  # To be defined by child classes

    def list_sources(self) -> List[Dict[str, Any]]:
        """List all sources of this type."""
        try:
            sources = self.db_session.query(DataSource).filter_by(
                type=self.source_type
            ).all()
            return [self._format_source(source) for source in sources]
        except Exception as e:
            self.logger.error(f"Error listing sources: {str(e)}")
            raise

    def get_source(self, source_id: UUID) -> Optional[Dict[str, Any]]:
        """Get specific source details."""
        try:
            source = self.db_session.query(DataSource).get(source_id)
            if source and source.type == self.source_type:
                return self._format_source(source)
            return None
        except Exception as e:
            self.logger.error(f"Error getting source: {str(e)}")
            raise

    def _format_source(self, source: DataSource) -> Dict[str, Any]:
        """Format source for API response."""
        base_info = {
            'id': str(source.id),
            'name': source.name,
            'type': source.type,
            'status': source.status,
            'config': source.config,
            'meta_data': source.meta_data,
            'refresh_interval': source.refresh_interval,
            'error': source.error,
            'last_sync': source.last_sync.isoformat() if source.last_sync else None,
            'created_at': source.created_at.isoformat(),
            'updated_at': source.updated_at.isoformat(),
            'created_by': str(source.created_by) if source.created_by else None,
            'updated_by': str(source.updated_by) if source.updated_by else None,
            'owner_id': str(source.owner_id) if source.owner_id else None,
        }

        # Add source-specific configuration
        if source.type == 'file' and source.file_info:
            base_info['source_config'] = {
                'original_filename': source.file_info.original_filename,
                'file_type': source.file_info.file_type,
                'mime_type': source.file_info.mime_type,
                'size': source.file_info.size,
                'hash': source.file_info.hash,
                'encoding': source.file_info.encoding,
                'delimiter': source.file_info.delimiter,
                'compression': source.file_info.compression
            }
        elif source.type == 'database' and source.db_config:
            base_info['source_config'] = {
                'dialect': source.db_config.dialect,
                'schema': source.db_config.schema,
                'pool_size': source.db_config.pool_size,
                'max_overflow': source.db_config.max_overflow,
                'connection_timeout': source.db_config.connection_timeout,
                'query_timeout': source.db_config.query_timeout,
                'ssl_config': source.db_config.ssl_config
            }
        elif source.type == 'api' and source.api_config:
            base_info['source_config'] = {
                'auth_type': source.api_config.auth_type,
                'rate_limit': source.api_config.rate_limit,
                'timeout': source.api_config.timeout,
                'headers': source.api_config.headers,
                'retry_config': source.api_config.retry_config,
                'webhook_url': source.api_config.webhook_url
            }
        elif source.type == 's3' and source.s3_config:
            base_info['source_config'] = {
                'bucket': source.s3_config.bucket,
                'region': source.s3_config.region,
                'prefix': source.s3_config.prefix,
                'storage_class': source.s3_config.storage_class,
                'versioning_enabled': source.s3_config.versioning_enabled,
                'transfer_config': source.s3_config.transfer_config
            }
        elif source.type == 'stream' and source.stream_config:
            base_info['source_config'] = {
                'stream_type': source.stream_config.stream_type,
                'partitions': source.stream_config.partitions,
                'batch_size': source.stream_config.batch_size,
                'processing_config': source.stream_config.processing_config,
                'error_handling': source.stream_config.error_handling,
                'checkpoint_config': source.stream_config.checkpoint_config,
                'scaling_config': source.stream_config.scaling_config
            }

        # Add validation results
        if hasattr(source, 'validation_results') and source.validation_results:
            base_info['validation_results'] = [{
                'id': str(result.id),
                'name': result.name,
                'type': result.type,
                'status': result.status,
                'error_count': result.error_count,
                'warning_count': result.warning_count,
                'impact_score': result.impact_score,
                'validated_at': result.validated_at.isoformat() if result.validated_at else None,
                'expires_at': result.expires_at.isoformat() if result.expires_at else None
            } for result in source.validation_results]

        # Add latest connection status
        latest_connection = (
            self.db_session.query(SourceConnection)
            .filter_by(source_id=source.id)
            .order_by(SourceConnection.created_at.desc())
            .first()
        )
        if latest_connection:
            base_info['connection_status'] = {
                'status': latest_connection.status,
                'connected_at': latest_connection.connected_at.isoformat() if latest_connection.connected_at else None,
                'disconnected_at': latest_connection.disconnected_at.isoformat() if latest_connection.disconnected_at else None,
                'error': latest_connection.error,
                'metrics': latest_connection.metrics
            }

        # Add latest sync history
        latest_sync = (
            self.db_session.query(SourceSyncHistory)
            .filter_by(source_id=source.id)
            .order_by(SourceSyncHistory.start_time.desc())
            .first()
        )
        if latest_sync:
            base_info['sync_history'] = {
                'status': latest_sync.status,
                'start_time': latest_sync.start_time.isoformat(),
                'end_time': latest_sync.end_time.isoformat() if latest_sync.end_time else None,
                'records_processed': latest_sync.records_processed,
                'bytes_processed': latest_sync.bytes_processed,
                'error': latest_sync.error
            }

        return base_info

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate source configuration."""
        raise NotImplementedError("Subclasses must implement validate_config")

    def test_connection(self, source_id: UUID) -> Dict[str, Any]:
        """Test connection to the source."""
        raise NotImplementedError("Subclasses must implement test_connection")