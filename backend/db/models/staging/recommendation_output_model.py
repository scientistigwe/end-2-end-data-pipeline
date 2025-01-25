# backend/db/models/staging/recommendation_output_model.py
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy import Column, String, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base_staging_model import BaseStagedOutput
from core.messaging.event_types import ComponentType, ReportSectionType
from typing import Dict, Any, Optional


class StagedRecommendationOutput(BaseStagedOutput):
    """Model for storing recommendation-related staged outputs"""
    __tablename__ = 'staged_recommendation_outputs'
    base_id = Column(UUID(as_uuid=True), ForeignKey('staged_outputs.id'), primary_key=True)

    # Recommendation-specific fields
    recommendation_candidates = Column(JSON, default=[])
    top_recommendations = Column(JSON, default=[])
    ranking_criteria = Column(JSON, default={})
    diversity_score = Column(Float, nullable=True)
    personalization_score = Column(Float, nullable=True)

    # Relationship configuration
    __mapper_args__ = {
        'polymorphic_identity': ComponentType.RECOMMENDATION_MANAGER,
        'inherit_condition': (base_id == BaseStagedOutput.id)
    }

    def __init__(self,
                 reference_id: str,
                 pipeline_id: str,
                 data: Dict[str, Any],
                 metadata: Optional[Dict[str, Any]] = None,
                 **kwargs):
        """
        Initialize a staged recommendation output

        Args:
            reference_id: Unique reference ID
            pipeline_id: Associated pipeline ID
            data: Recommendation data
            metadata: Additional metadata
        """
        super().__init__(
            id=reference_id,
            pipeline_id=pipeline_id,
            component_type=ComponentType.RECOMMENDATION_MANAGER,
            output_type=ReportSectionType.RECOMMENDATIONS,
            **kwargs
        )

        # Process recommendation-specific data
        self.recommendation_candidates = data.get('candidates', [])
        self.top_recommendations = data.get('top_recommendations', [])
        self.ranking_criteria = data.get('ranking_criteria', {})
        self.diversity_score = data.get('diversity_score')
        self.personalization_score = data.get('personalization_score')

        # Store additional metadata
        self.base_stage_metadata = metadata or {}
        self.data_size = len(str(data))