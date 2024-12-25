# backend/database/models/utils.py
from sqlalchemy import Column, String, Integer, Text, Boolean, Index
from sqlalchemy.orm import relationship
from .associations import dataset_tags, pipeline_tags, datasource_tags
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
from .base import BaseModel

class Tag(BaseModel):
    __tablename__ = 'tags'

    name = Column(String(100), nullable=False)
    color = Column(String(7))  
    description = Column(Text)
    entity_type = Column(String(50))  
    usage_count = Column(Integer, default=0)
    is_system = Column(Boolean, default=False)

    # Relationships
    datasets = relationship(
        'Dataset',
        secondary=dataset_tags,
        back_populates='tags'
    )
    pipelines = relationship(
        'Pipeline',
        secondary=pipeline_tags,
        back_populates='tags'
    )
    data_sources = relationship(
        'DataSource',
        secondary=datasource_tags,
        back_populates='tags'
    )

    __table_args__ = (
        Index('ix_tags_name_type', 'name', 'entity_type', unique=True),
    )

    def __repr__(self):
        return f"<Tag(name='{self.name}', entity_type='{self.entity_type}')>"
    

class AuditLog(BaseModel):
    __tablename__ = 'audit_logs'

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    changes = Column(JSONB)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    session_id = Column(UUID(as_uuid=True), ForeignKey('user_sessions.id'))

    __table_args__ = (
        Index('ix_audit_logs_entity', 'entity_type', 'entity_id'),
        Index('ix_audit_logs_user_action', 'user_id', 'action'),
    )


class Notification(BaseModel):
    __tablename__ = 'notifications'

    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'), 
        nullable=False,
        index=True
    )
    type = Column(String(100))
    title = Column(String(255))
    content = Column(Text)
    priority = Column(Integer, default=0)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime)
    expires_at = Column(DateTime)
    action_url = Column(String(255))
    notification_meta = Column(JSONB)

    # Fix: Specify foreign key explicitly
    user = relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='notifications'
    )


class Comment(BaseModel):
    __tablename__ = 'comments'

    parent_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('comments.id', ondelete='CASCADE'),
        nullable=True
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey('users.id'),
        nullable=False
    )
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    content = Column(Text)
    edited = Column(Boolean, default=False)
    edited_at = Column(DateTime)
    comment_meta = Column(JSONB)

    # Fix the self-referential relationship
    parent = relationship(
        'Comment',
        remote_side='[Comment.id]',  # Use string to avoid the id built-in function issue
        backref=backref('replies', remote_side='[Comment.parent_id]')
    )

    def __repr__(self):
        return f"<Comment(id='{self.id}', entity_type='{self.entity_type}')>"
    

class File(BaseModel):
    __tablename__ = 'files'

    name = Column(String(255), nullable=False)
    path = Column(String(512), nullable=False)
    mime_type = Column(String(100))
    size = Column(Integer)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    checksum = Column(String(64))
    storage_provider = Column(String(50))
    file_meta = Column(JSONB)

    __table_args__ = (
        Index('ix_files_entity', 'entity_type', 'entity_id'),
        Index('ix_files_checksum', 'checksum'),
    )

    def __repr__(self):
        return f"<File(name='{self.name}', type='{self.entity_type}')>"

# Export the models
__all__ = ['AuditLog', 'Notification', 'Comment', 'File']