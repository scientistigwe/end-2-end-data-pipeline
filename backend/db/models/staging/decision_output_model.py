# backend/db/models/staging/decision_output_model.py

from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, String, JSON, ForeignKey, Float
from typing import Dict, Any, Optional
from sqlalchemy.orm import relationship
from .base_staging_model import BaseStagedOutput
from core.messaging.event_types import ComponentType, ReportSectionType


class StagedDecisionOutput(BaseStagedOutput):
    """Model for storing decision-related staged outputs"""
    __tablename__ = 'staged_decision_outputs'
    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)

    # Decision-specific fields
    decision_options = Column(JSON, default=[])
    selected_option = Column(JSON, nullable=True)
    decision_criteria = Column(JSON, default={})
    impact_analysis = Column(JSON, default={})
    confidence_score = Column(Float, nullable=True)

    # Add unique source column name
    decision_source_id = Column(
        'source_id',  # Actual column name in database
        UUID(as_uuid=True),
        ForeignKey('data_sources.id')
    )

    # Add relationship with unique name
    decision_source = relationship(
        "DataSource",
        back_populates="decision_outputs",
        foreign_keys=[decision_source_id]
    )

    # Relationship configuration
    __mapper_args__ = {
        'polymorphic_identity': ComponentType.DECISION_MANAGER,
        'inherit_condition': (base_id == BaseStagedOutput.id)
    }

    def __init__(self,
                 reference_id: str,
                 pipeline_id: str,
                 data: Dict[str, Any],
                 metadata: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """
        Initialize a staged decision output

        Args:
            reference_id: Unique reference ID
            pipeline_id: Associated pipeline ID
            data: Decision data
            metadata: Additional metadata
        """
        super().__init__(
            id=reference_id,
            pipeline_id=pipeline_id,
            component_type=ComponentType.DECISION_MANAGER,
            output_type=ReportSectionType.DECISION,
            **kwargs
        )

        # Process decision-specific data
        self.decision_options = data.get('options', [])
        self.selected_option = data.get('selected_option')
        self.decision_criteria = data.get('criteria', {})
        self.impact_analysis = data.get('impact_analysis', {})
        self.confidence_score = data.get('confidence_score')

        # Store additional metadata
        self.base_stage_metadata = metadata or {}
        self.data_size = len(str(data))