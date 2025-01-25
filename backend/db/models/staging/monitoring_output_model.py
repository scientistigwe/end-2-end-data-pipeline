# backend/db/models/staging/monitoring_output_model.py
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import relationship
from sqlalchemy.orm import column_property
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, JSON, DateTime, Float, ForeignKey, Integer
from .base_staging_model import BaseStagedOutput

class StagedMonitoringOutput(BaseStagedOutput):
    """
    Model for storing monitoring metrics and system health data.
    Integrates with the staging system for consistent data management.
    """
    __tablename__ = 'staging_monitoring_output'

    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)

    # Resource metrics
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    disk_usage = Column(Float)
    network_in = Column(Float)
    network_out = Column(Float)

    # Component health status
    component_status = Column(JSON, default=dict)
    health_checks = Column(JSON, default=dict)

    # Performance metrics
    processing_time = Column(Float)
    throughput = Column(Float)
    error_count = Column(Integer, default=0)

    # Metadata and timestamps with unique column names
    staged_monitoring_metadata = Column(JSON, default=dict)
    monitoring_created_at = column_property(Column(DateTime, default=datetime.utcnow))
    monitoring_updated_at = column_property(Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow))

    # Relationships
    base_output = relationship("BaseStagedOutput", back_populates="monitoring_output")

    __mapper_args__ = {
        "polymorphic_identity": "staging.monitoring_output",
        "inherit_condition": base_id == BaseStagedOutput.id
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        return {
            'id': self.id,
            'reference_id': self.reference_id,
            'pipeline_id': self.pipeline_id,
            'resource_metrics': {
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'disk_usage': self.disk_usage,
                'network': {
                    'in': self.network_in,
                    'out': self.network_out
                }
            },
            'component_status': self.component_status,
            'health_checks': self.health_checks,
            'performance': {
                'processing_time': self.processing_time,
                'throughput': self.throughput,
                'error_count': self.error_count
            },
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MonitoringOutput':
        """Create model instance from dictionary."""
        instance = cls()

        # Map basic fields
        instance.id = data.get('id')
        instance.reference_id = data.get('reference_id')
        instance.pipeline_id = data.get('pipeline_id')

        # Map resource metrics
        resource_metrics = data.get('resource_metrics', {})
        instance.cpu_usage = resource_metrics.get('cpu_usage')
        instance.memory_usage = resource_metrics.get('memory_usage')
        instance.disk_usage = resource_metrics.get('disk_usage')

        network = resource_metrics.get('network', {})
        instance.network_in = network.get('in')
        instance.network_out = network.get('out')

        # Map status and health data
        instance.component_status = data.get('component_status', {})
        instance.health_checks = data.get('health_checks', {})

        # Map performance metrics
        performance = data.get('performance', {})
        instance.processing_time = performance.get('processing_time')
        instance.throughput = performance.get('throughput')
        instance.error_count = performance.get('error_count', 0)

        # Map metadata
        instance.metadata = data.get('metadata', {})

        return instance