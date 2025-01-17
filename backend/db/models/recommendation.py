# backend\backend\db\types\recommendation.py
from sqlalchemy import (
    Column, 
    String, 
    DateTime, 
    JSON, 
    Enum, 
    ForeignKey, 
    Float, 
    Text, 
    Integer, 
    Boolean,
    Index,
    CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from .base import BaseModel
from datetime import datetime

class Recommendation(BaseModel):
   """Model for pipeline recommendations."""
   __tablename__ = 'recommendations'

   pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id', ondelete='CASCADE'), nullable=False)
   type = Column(String(100))
   status = Column(
       Enum('pending', 'applied', 'dismissed', 'failed', name='recommendation_status'),
       default='pending'
   )
   priority = Column(Integer)
   confidence = Column(Float)
   impact = Column(Float)
   description = Column(Text, nullable=False)
   rationale = Column(Text)
   action_details = Column(JSONB)
   recommendation_meta = Column(JSONB)

   # Timestamps
   applied_at = Column(DateTime)
   applied_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
   dismissed_at = Column(DateTime)
   dismissed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
   dismiss_reason = Column(Text)
   expiry_date = Column(DateTime)

   # Additional fields
   category = Column(String(100))
   cost_estimate = Column(Float)
   benefit_estimate = Column(Float)
   implementation_complexity = Column(Enum('low', 'medium', 'high', name='complexity_level'))
   dependencies = Column(JSONB)
   required_resources = Column(JSONB)
   validation_rules = Column(JSONB)

   # Relationships
   pipeline = relationship('Pipeline', back_populates='recommendations')
   decisions = relationship('Decision', back_populates='recommendation')
   feedback = relationship('RecommendationFeedback', back_populates='recommendation', cascade='all, delete-orphan')

   __table_args__ = (
       Index('ix_recommendations_status', 'status'),
       Index('ix_recommendations_priority', 'priority'),
       CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_recommendation_confidence'),
       CheckConstraint('impact >= 0 AND impact <= 1', name='ck_recommendation_impact'),
       CheckConstraint('priority >= 0', name='ck_recommendation_priority'),
       {'extend_existing': True}
   )

   def __repr__(self):
       return f"<Recommendation(type='{self.type}', status='{self.status}')>"


class RecommendationFeedback(BaseModel):
    """Model for storing feedback on recommendations."""
    __tablename__ = 'recommendation_feedback'

    recommendation_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('recommendations.id', ondelete='CASCADE'), 
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=False
    )
    rating = Column(Integer)  # 1-5
    comment = Column(Text)
    feedback_meta = Column(JSONB)
    
    # Additional fields
    sentiment = Column(
        Enum('positive', 'neutral', 'negative', name='feedback_sentiment')
    )
    impact_assessment = Column(Text)
    implementation_feedback = Column(Text)
    suggestions = Column(JSONB)
    is_anonymous = Column(Boolean, default=False)

    # Fixed relationships with explicit foreign keys
    recommendation = relationship(
        'Recommendation', 
        back_populates='feedback'
    )
    user = relationship(
        'User',
        foreign_keys=[user_id]  # Explicitly specify foreign key
    )

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='ck_feedback_rating'),
        Index('ix_recommendation_feedback_rating', 'rating'),
        {'extend_existing': True}
    )

    def __repr__(self):
        return f"<RecommendationFeedback(recommendation_id='{self.recommendation_id}', rating={self.rating})>"