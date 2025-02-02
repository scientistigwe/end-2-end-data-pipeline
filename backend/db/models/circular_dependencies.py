# backend/db/models/circular_dependencies.py

import uuid
from sqlalchemy import Column, String, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import DateTime
from datetime import datetime

# Import the User model from the existing auth module
from .auth import User


class DecisionHistory(User.base.__class__):
    """
    Decision History model with careful relationship setup
    """
    __tablename__ = 'decision_history'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )

    # Add other relevant fields for decision history
    decision_type = Column(String(100))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship(
        "User",
        back_populates="decision_history",
        foreign_keys=[user_id]
    )

    def __repr__(self):
        return f"<DecisionHistory(user_id={self.user_id}, decision_type='{self.decision_type}')>"

# No need for additional mixin or base class setup
# Simply use the existing User model's base and configurations