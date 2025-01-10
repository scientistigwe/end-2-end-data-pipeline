from sqlalchemy import (
    Column, 
    DateTime, 
    String, 
    UUID, 
    event, 
    DDL, 
    ForeignKey,
    MetaData,
    Boolean,
    Integer,
    Text,
    JSON
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
import uuid

# Create base metadata with comprehensive naming convention
base_meta = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(column_0_N_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s",
        "pk": "pk_%(table_name)s"
    }
)

Base = declarative_base(metadata=base_meta)


# backend/database/models/base.py
class BaseModel(Base):
    __abstract__ = True

    # Keep the basic columns that don't reference users
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Use declared_attr for all user references
    @declared_attr
    def created_by(cls):
        if cls.__name__ == 'User':
            return Column(UUID(as_uuid=True), nullable=True)
        return Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'), index=True)

    @declared_attr
    def updated_by(cls):
        if cls.__name__ == 'User':
            return Column(UUID(as_uuid=True), nullable=True)
        return Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    @declared_attr
    def deleted_by(cls):
        if cls.__name__ == 'User':
            return Column(UUID(as_uuid=True), nullable=True)
        return Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    @declared_attr
    def last_audit_by(cls):
        if cls.__name__ == 'User':
            return Column(UUID(as_uuid=True), nullable=True)
        return Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    # Soft Delete Support
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    # Versioning Support
    version = Column(Integer, default=1, nullable=False)
    version_notes = Column(Text)
    previous_version = Column(UUID(as_uuid=True))

    # Audit Support
    audit_trail = Column(JSONB)
    last_audit_at = Column(DateTime)
    last_audit_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))

    @validates('created_at', 'updated_at', 'deleted_at')
    def validate_dates(self, key, value):
        """Validate date fields."""
        if not isinstance(value, datetime):
            raise ValueError(f"{key} must be a datetime object")
        return value

    @hybrid_property
    def age(self):
        """Returns the age of the record in days."""
        return (datetime.utcnow() - self.created_at).days

    @hybrid_property
    def is_new(self):
        """Returns True if the record is less than 24 hours old."""
        return (datetime.utcnow() - self.created_at).days < 1

    @hybrid_property
    def is_modified(self):
        """Returns True if the record has been modified since creation."""
        return self.updated_at > self.created_at

    @hybrid_property
    def modification_age(self):
        """Returns the age of the last modification in days."""
        return (datetime.utcnow() - self.updated_at).days if self.is_modified else 0

    def soft_delete(self, user_id=None):
        """Soft delete the record."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
        self.deleted_by = user_id

    def increment_version(self, notes=None, user_id=None):
        """Increment the version of the record."""
        self.previous_version = self.id
        self.version += 1
        self.version_notes = notes
        self.updated_at = datetime.utcnow()
        self.updated_by = user_id

    def update_audit_trail(self, action, user_id=None, details=None):
        """Update the audit trail of the record."""
        if self.audit_trail is None:
            self.audit_trail = []
        
        audit_entry = {
            'action': action,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': str(user_id) if user_id else None,
            'details': details
        }
        
        self.audit_trail.append(audit_entry)
        self.last_audit_at = datetime.utcnow()
        self.last_audit_by = user_id

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
            if not column.name.startswith('_')
        }

    def update(self, **kwargs):
        """Update multiple attributes at once."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{key}'")
        
        self.updated_at = datetime.utcnow()

    @classmethod
    def __declare_last__(cls):
        """Add database constraints after table creation."""
        event.listen(
            cls.__table__,
            'after_create',
            DDL(
                f'''
                ALTER TABLE {cls.__tablename__} 
                ADD CONSTRAINT valid_dates 
                CHECK (
                    updated_at >= created_at AND
                    (deleted_at IS NULL OR deleted_at >= created_at) AND
                    (last_audit_at IS NULL OR last_audit_at >= created_at)
                )
                '''
            )
        )

    def __repr__(self):
        """Return string representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"