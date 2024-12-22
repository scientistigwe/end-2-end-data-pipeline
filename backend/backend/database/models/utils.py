# models/utils.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Table, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel

# Tags for various entities
class Tag(BaseModel):
    __tablename__ = 'tags'

    name = Column(String(100), nullable=False)
    color = Column(String(7))  # Hex color
    description = Column(Text)
    entity_type = Column(String(50))  # pipeline, datasource, etc.

# Many-to-Many relationship tables for tags
pipeline_tags = Table('pipeline_tags', BaseModel.metadata,
    Column('pipeline_id', UUID(as_uuid=True), ForeignKey('pipelines.id')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id'))
)

datasource_tags = Table('datasource_tags', BaseModel.metadata,
    Column('datasource_id', UUID(as_uuid=True), ForeignKey('data_sources.id')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id'))
)

# Audit Logging
class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    changes = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(String(255))

# Notifications
class Notification(BaseModel):
    __tablename__ = 'notifications'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    type = Column(String(100))
    title = Column(String(255))
    content = Column(Text)
    priority = Column(Integer, default=0)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    notification_meta = Column(JSONB)

# Comments (generic for multiple entities)
class Comment(BaseModel):
    __tablename__ = 'comments'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    content = Column(Text)
    parent_id = Column(UUID(as_uuid=True), ForeignKey('comments.id'))
    comment_meta = Column(JSONB)

# File Storage
class File(BaseModel):
    __tablename__ = 'files'

    name = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False)
    mime_type = Column(String(100))
    size = Column(Integer)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    file_meta = Column(JSONB)