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

class Decision(BaseModel):
    """Model for managing decisions in the data pipeline."""
    __tablename__ = 'decisions'

    # Basic information
    pipeline_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('pipelines.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    type = Column(
        Enum(
            'data_quality',
            'pipeline_config',
            'alert_response',
            'resource_allocation',
            'optimization',
            name='decision_type'
        )
    )
    status = Column(
        Enum(
            'pending',
            'in_review',
            'approved',
            'rejected',
            'deferred',
            name='decision_status'
        ),
        default='pending',
        nullable=False
    )
    priority = Column(
        Enum(
            'low',
            'medium',
            'high',
            'critical',
            name='priority_level'
        ),
        default='medium'
    )

    # Timing and deadlines
    deadline = Column(DateTime)
    decision_made_at = Column(DateTime)
    implementation_date = Column(DateTime)
    review_date = Column(DateTime)

    # Decision details
    meta_info = Column(JSONB)
    context = Column(JSONB)
    impact_analysis = Column(JSONB)
    risk_assessment = Column(JSONB)
    implementation_plan = Column(JSONB)
    success_criteria = Column(JSONB)

    # Metrics
    confidence_score = Column(Float)
    impact_score = Column(Float)
    risk_score = Column(Float)
    implementation_cost = Column(Float)
    estimated_roi = Column(Float)
    
    # Relationships
    made_by = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'),
        index=True
    )
    recommendation_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('recommendations.id')
    )
    validation_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey('validation_results.id'),
        nullable=True
    )
    
    # Relationship definitions
    options = relationship(
        'DecisionOption', 
        back_populates='decision',
        cascade='all, delete-orphan'
    )
    comments = relationship(
        'DecisionComment', 
        back_populates='decision',
        cascade='all, delete-orphan'
    )
    history = relationship(
        'DecisionHistory', 
        back_populates='decision',
        cascade='all, delete-orphan'
    )
    validation_result = relationship(
        'ValidationResult',
        back_populates='decision',
        uselist=False
    )
    pipeline = relationship('Pipeline', back_populates='decisions')
    recommendation = relationship('Recommendation', back_populates='decisions')

    __table_args__ = (
        Index('ix_decisions_status_priority', 'status', 'priority'),
        CheckConstraint(
            'deadline > created_at',
            name='ck_decision_deadline_valid'
        ),
        CheckConstraint(
            'confidence_score >= 0 AND confidence_score <= 1',
            name='ck_decision_confidence_valid'
        ),
        CheckConstraint(
            'risk_score >= 0 AND risk_score <= 1',
            name='ck_decision_risk_valid'
        ),
        {'extend_existing': True}
    )

    @validates('deadline')
    def validate_deadline(self, key, value):
        """Validate that deadline is in the future."""
        if value and value <= datetime.utcnow():
            raise ValueError("Deadline must be in the future")
        return value

    def __repr__(self):
        return f"<Decision(type='{self.type}', status='{self.status}', priority='{self.priority}')>"


class DecisionOption(BaseModel):
    """Model for storing decision options and their evaluations."""
    __tablename__ = 'decision_options'

    decision_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('decisions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    name = Column(String(255), nullable=False)
    description = Column(Text)
    impact_score = Column(Float)
    feasibility_score = Column(Float)
    risks = Column(JSONB)
    benefits = Column(JSONB)
    costs = Column(JSONB)
    dependencies = Column(JSONB)
    is_selected = Column(Boolean, default=False)
    selection_reason = Column(Text)
    
    # Implementation details
    implementation_complexity = Column(
        Enum('low', 'medium', 'high', name='complexity_level')
    )
    estimated_duration = Column(Integer)  # in days
    resource_requirements = Column(JSONB)
    
    decision = relationship('Decision', back_populates='options')

    __table_args__ = (
        CheckConstraint(
            'impact_score >= 0 AND impact_score <= 1',
            name='ck_option_impact_valid'
        ),
        CheckConstraint(
            'feasibility_score >= 0 AND feasibility_score <= 1',
            name='ck_option_feasibility_valid'
        ),
        CheckConstraint(
            'estimated_duration > 0',
            name='ck_option_duration_valid'
        )
    )

    def __repr__(self):
        return f"<DecisionOption(name='{self.name}', selected={self.is_selected})>"


class DecisionComment(BaseModel):
    """Model for storing comments and discussions on decisions."""
    __tablename__ = 'decision_comments'

    decision_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('decisions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'),
        nullable=False
    )
    content = Column(Text, nullable=False)
    parent_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('decision_comments.id', ondelete='CASCADE')
    )
    
    # Additional fields
    comment_type = Column(
        Enum('question', 'concern', 'suggestion', 'approval', name='comment_type')
    )
    attachments = Column(JSONB)
    is_internal = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    resolved_at = Column(DateTime)
    
    # Fix the relationships
    decision = relationship('Decision', back_populates='comments')
    parent = relationship(
        'DecisionComment',
        remote_side='[DecisionComment.id]',  # Fix: Use string to avoid circular reference
        backref='children'  # Use backref instead of separate children relationship
    )

    def __repr__(self):
        return f"<DecisionComment(decision_id='{self.decision_id}', user_id='{self.user_id}')>"


class DecisionHistory(BaseModel):
    """Model for tracking decision history and changes."""
    __tablename__ = 'decision_history'

    decision_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('decisions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    action = Column(String(100), nullable=False)
    previous_status = Column(String(50))
    new_status = Column(String(50))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    event_meta = Column(JSONB)
    
    # Additional tracking
    change_reason = Column(Text)
    affected_fields = Column(JSONB)
    system_generated = Column(Boolean, default=False)
    
    # Fixed relationships with explicit foreign keys
    decision = relationship('Decision', back_populates='history')
    user = relationship('User', foreign_keys=[user_id])  # Specify foreign key explicitly

    def __repr__(self):
        return f"<DecisionHistory(decision_id='{self.decision_id}', action='{self.action}')>"


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