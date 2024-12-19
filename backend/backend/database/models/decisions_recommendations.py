# models/decisions_recommendations.py
from sqlalchemy import Column, String, DateTime, JSON, Enum, ForeignKey, Float, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

class Decision(BaseModel):
    __tablename__ = 'decisions'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    type = Column(String(100))
    status = Column(Enum('pending', 'approved', 'rejected', 'deferred', name='decision_status'))
    priority = Column(Enum('low', 'medium', 'high', 'critical', name='priority_level'))
    deadline = Column(DateTime)
    metadata = Column(JSONB)
    context = Column(JSONB)
    impact_analysis = Column(JSONB)
    
    # Relationships
    made_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey('recommendations.id'))
    validation_result_id = Column(UUID(as_uuid=True), ForeignKey('validation_results.id'))
    
    options = relationship('DecisionOption', back_populates='decision')
    comments = relationship('DecisionComment', back_populates='decision')
    history = relationship('DecisionHistory', back_populates='decision')

class DecisionOption(BaseModel):
    __tablename__ = 'decision_options'

    decision_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id'), nullable=False)
    name = Column(String(255))
    description = Column(Text)
    impact_score = Column(Float)
    risks = Column(JSONB)
    benefits = Column(JSONB)
    is_selected = Column(Boolean, default=False)
    
    decision = relationship('Decision', back_populates='options')

class DecisionComment(BaseModel):
    __tablename__ = 'decision_comments'

    decision_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    content = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('decision_comments.id'))
    
    decision = relationship('Decision', back_populates='comments')

class DecisionHistory(BaseModel):
    __tablename__ = 'decision_history'

    decision_id = Column(UUID(as_uuid=True), ForeignKey('decisions.id'), nullable=False)
    action = Column(String(100))
    previous_status = Column(String(50))
    new_status = Column(String(50))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    metadata = Column(JSONB)
    
    decision = relationship('Decision', back_populates='history')

class Recommendation(BaseModel):
    __tablename__ = 'recommendations'

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey('pipelines.id'), nullable=False)
    type = Column(String(100))
    status = Column(Enum('pending', 'applied', 'dismissed', 'failed', name='recommendation_status'))
    priority = Column(Integer)
    confidence = Column(Float)
    impact = Column(Float)
    description = Column(Text)
    rationale = Column(Text)
    action_details = Column(JSONB)
    metadata = Column(JSONB)
    applied_at = Column(DateTime)
    applied_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    dismissed_at = Column(DateTime)
    dismissed_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    dismiss_reason = Column(Text)

class RecommendationFeedback(BaseModel):
    __tablename__ = 'recommendation_feedback'

    recommendation_id = Column(UUID(as_uuid=True), ForeignKey('recommendations.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    rating = Column(Integer)  # 1-5
    comment = Column(Text)
    metadata = Column(JSONB)