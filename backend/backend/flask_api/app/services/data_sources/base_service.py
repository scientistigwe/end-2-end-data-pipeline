# backend/flask_api/app/services/data_sources/base_service.py

from typing import Dict, Any, List, Optional, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from .....database.models.data_source import (
    DataSource, 
    SourceConnection,
    SourceSyncHistory
)
from .....database.models.validation import ValidationResult
from flask import current_app
from werkzeug.datastructures import FileStorage
import logging

class BaseSourceService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)
        self.source_type: str = None

    def list_sources(self) -> List[DataSource]:
        """
        List all data sources of the specific type.
        
        Returns:
            List[DataSource]: List of all data sources of the specific type
        """
        try:
            return (self.db_session.query(DataSource)
                    .filter(DataSource.type == self.source_type)
                    .all())
        except Exception as exc:
            self.logger.error(f"Error listing {self.source_type} sources: {str(exc)}")
            raise
        
    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate source configuration and return validation result."""
        try:
            validation = ValidationResult(
                source_id=None,  # Will be set after source creation
                name=f"{self.source_type}_config_validation",
                type="configuration",
                status="pending",
                validated_at=datetime.utcnow()
            )
            
            # Implement source-specific validation
            validation_errors = self._validate_source_config(config)
            
            if validation_errors:
                validation.status = "failed"
                validation.error_count = len(validation_errors)
                validation.details = {"errors": validation_errors}
            else:
                validation.status = "passed"
                validation.error_count = 0
            
            self.db_session.add(validation)
            self.db_session.commit()
            
            return validation
        except Exception as e:
            self.logger.error(f"Config validation error: {str(e)}")
            raise

    def test_connection(self, source_id: UUID) -> Dict[str, Any]:
        """Test connection to the source."""
        try:
            source = self._get_source_or_error(source_id)
            
            connection = SourceConnection(
                source_id=source.id,
                status="testing",
                connected_at=datetime.utcnow()
            )
            self.db_session.add(connection)
            
            try:
                # Perform source-specific connection test
                test_result = self._test_source_connection(source)
                connection.status = "connected"
                connection.metrics = test_result
            except Exception as e:
                connection.status = "failed"
                connection.error = str(e)
                raise
            finally:
                if connection.status == "testing":
                    connection.status = "failed"
                connection.disconnected_at = datetime.utcnow()
                self.db_session.commit()
            
            return {
                "status": connection.status,
                "metrics": connection.metrics,
                "error": connection.error,
                "connected_at": connection.connected_at.isoformat(),
                "disconnected_at": connection.disconnected_at.isoformat() if connection.disconnected_at else None
            }
        except Exception as e:
            self.logger.error(f"Connection test error: {str(e)}")
            raise

    def sync_source(self, source_id: UUID) -> Dict[str, Any]:
        """Synchronize source data."""
        try:
            source = self._get_source_or_error(source_id)
            
            sync_history = SourceSyncHistory(
                source_id=source.id,
                status="in_progress",
                start_time=datetime.utcnow()
            )
            self.db_session.add(sync_history)
            
            try:
                # Perform source-specific sync
                sync_result = self._sync_source_data(source)
                sync_history.status = "completed"
                sync_history.records_processed = sync_result.get("records_processed", 0)
                sync_history.bytes_processed = sync_result.get("bytes_processed", 0)
            except Exception as e:
                sync_history.status = "failed"
                sync_history.error = str(e)
                raise
            finally:
                sync_history.end_time = datetime.utcnow()
                self.db_session.commit()
            
            return {
                "status": sync_history.status,
                "records_processed": sync_history.records_processed,
                "bytes_processed": sync_history.bytes_processed,
                "error": sync_history.error,
                "start_time": sync_history.start_time.isoformat(),
                "end_time": sync_history.end_time.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Source sync error: {str(e)}")
            raise

    def preview_data(self, source_id: UUID, limit: int = 100) -> Dict[str, Any]:
        """Preview source data with limit."""
        try:
            source = self._get_source_or_error(source_id)
            preview_data = self._get_source_preview(source, limit)
            
            return {
                "data": preview_data,
                "total_records": len(preview_data),
                "has_more": len(preview_data) == limit
            }
        except Exception as e:
            self.logger.error(f"Data preview error: {str(e)}")
            raise

    def disconnect(self, connection_id: UUID) -> Dict[str, Any]:
        """Disconnect from source."""
        try:
            connection = self.db_session.query(SourceConnection).get(connection_id)
            if not connection:
                raise ValueError(f"Connection {connection_id} not found")
            
            if connection.status == "connected":
                # Perform source-specific disconnect
                self._disconnect_source(connection.source)
                
                connection.status = "disconnected"
                connection.disconnected_at = datetime.utcnow()
                self.db_session.commit()
            
            return {
                "status": "success",
                "message": f"Disconnected from source {connection.source_id}"
            }
        except Exception as e:
            self.logger.error(f"Disconnect error: {str(e)}")
            raise

    def get_connection_status(self, connection_id: UUID) -> Dict[str, Any]:
        """Get current connection status."""
        try:
            connection = self.db_session.query(SourceConnection).get(connection_id)
            if not connection:
                raise ValueError(f"Connection {connection_id} not found")
            
            return {
                "status": connection.status,
                "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
                "disconnected_at": connection.disconnected_at.isoformat() if connection.disconnected_at else None,
                "error": connection.error,
                "metrics": connection.metrics
            }
        except Exception as e:
            self.logger.error(f"Status check error: {str(e)}")
            raise

    def _get_source_or_error(self, source_id: Union[UUID, str]) -> DataSource:
        """Get source by ID or raise error."""
        if isinstance(source_id, str):
            source_id = UUID(source_id)
        
        source = self.db_session.query(DataSource).get(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        if source.type != self.source_type:
            raise ValueError(f"Invalid source type {source.type} for {self.source_type} service")
        
        return source

    # Abstract methods to be implemented by specific source services
    def _validate_source_config(self, config: Dict[str, Any]) -> List[str]:
        raise NotImplementedError("Subclasses must implement _validate_source_config")

    def _test_source_connection(self, source: DataSource) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement _test_source_connection")

    def _sync_source_data(self, source: DataSource) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement _sync_source_data")

    def _get_source_preview(self, source: DataSource, limit: int) -> List[Dict[str, Any]]:
        raise NotImplementedError("Subclasses must implement _get_source_preview")

    def _disconnect_source(self, source: DataSource) -> None:
        raise NotImplementedError("Subclasses must implement _disconnect_source")
