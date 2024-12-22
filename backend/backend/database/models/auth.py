# models/auth.py
from sqlalchemy import (
   Column, 
   String, 
   DateTime, 
   Boolean, 
   Enum, 
   ForeignKey, 
   JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
import uuid

class User(BaseModel):
   """User model for authentication and authorization."""
   __tablename__ = 'users'

   # Authentication fields
   email = Column(String(255), unique=True, nullable=False)
   password_hash = Column(String(255), nullable=False)
   full_name = Column(String(255))
   status = Column(Enum('active', 'inactive', 'suspended', name='user_status'), default='active')
   role = Column(String(50), default='user')
   last_login = Column(DateTime)
   email_verified = Column(Boolean, default=False)
   profile_image = Column(String(255))
   preferences = Column(JSON)

   # Relationships
   sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

   def __repr__(self):
       return f"<User(email={self.email}, role={self.role}, status={self.status})>"

class UserSession(BaseModel):
   """Model for tracking user sessions."""
   __tablename__ = 'user_sessions'

   # Session fields
   user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
   token = Column(String(255), unique=True, nullable=False)
   expires_at = Column(DateTime, nullable=False)
   ip_address = Column(String(45))
   user_agent = Column(String(255))

   # Relationships
   user = relationship("User", back_populates="sessions")

   def __repr__(self):
       return f"<UserSession(user_id={self.user_id}, expires_at={self.expires_at})>"