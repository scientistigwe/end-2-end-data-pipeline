# database/models/base.py
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from ..config import Base

class BaseModel(Base):
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(50))
    updated_by = Column(String(50))