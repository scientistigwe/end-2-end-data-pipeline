# models/base.py
from sqlalchemy import (
    Column, 
    DateTime, 
    String, 
    UUID, 
    event, 
    DDL, 
    ForeignKey  # Added this import
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import uuid

Base = declarative_base()

class BaseModel(Base):
    __abstract__ = True
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Rest of your code remains the same
    @validates('created_at', 'updated_at')
    def validate_dates(self, key, value):
        if not isinstance(value, datetime):
            raise ValueError(f"{key} must be a datetime object")
        return value

    @hybrid_property
    def age(self):
        """Returns the age of the record in days"""
        return (datetime.utcnow() - self.created_at).days

    @hybrid_property
    def is_new(self):
        """Returns True if the record is less than 24 hours old"""
        return (datetime.utcnow() - self.created_at).days < 1

    @classmethod
    def __declare_last__(cls):
        event.listen(
            cls.__table__,
            'after_create',
            DDL(f'ALTER TABLE {cls.__tablename__} ADD CONSTRAINT valid_dates CHECK (updated_at >= created_at)')
        )

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def update(self, **kwargs):
        """Update multiple attributes at once"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{key}'")

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id})>"