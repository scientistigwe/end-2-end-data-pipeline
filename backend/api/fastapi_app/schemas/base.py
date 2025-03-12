# # backend/api/fastapi_app/schemas/base.py
# backend/api/fastapi_app/schemas/base.py
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, model_validator, ConfigDict
from enum import Enum


class ComponentType(str, Enum):
    AUTH = "auth"
    DATA_SOURCE = "data_source"
    STAGING = "staging"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ProcessingStage(str, Enum):
    VALIDATION = "validation"
    PROCESSING = "processing"
    TRANSFORMATION = "transformation"
    LOADING = "loading"
    COMPLETION = "completion"


class BaseSchema(BaseModel):
    """
    Core base schema that all other schemas inherit from.
    Provides common fields and functionality.
    """
    id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True
    )


class BaseAuthSchema(BaseSchema):
    """
    Base schema for authentication-related models.
    Adds auth-specific fields and validation.
    """
    user_id: UUID
    tenant_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    auth_metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode='after')
    def validate_expiration(self) -> 'BaseAuthSchema':
        if self.expires_at and self.expires_at < datetime.utcnow():
            self.is_active = False
        return self


class BaseDataSourceSchema(BaseSchema):
    """
    Base schema for data source-related models.
    Adds data source-specific fields and validation.
    """
    source_type: str
    connection_id: UUID
    status: ProcessingStatus = ProcessingStatus.PENDING
    last_sync: Optional[datetime] = None
    configuration: Dict[str, Any] = Field(default_factory=dict)
    error_count: int = 0
    retry_count: int = 0

    @model_validator(mode='after')
    def validate_connection(self) -> 'BaseDataSourceSchema':
        if self.status == ProcessingStatus.FAILED:
            if self.retry_count >= self.configuration.get('max_retries', 3):
                self.status = ProcessingStatus.ARCHIVED
        return self


class BaseStagingSchema(BaseSchema):
    """
    Base schema for staging-related models.
    Adds staging-specific fields and validation.
    """
    pipeline_id: UUID
    stage: ProcessingStage
    status: ProcessingStatus = ProcessingStatus.PENDING
    component_type: ComponentType
    storage_path: Optional[str] = None
    data_size: int = 0
    expires_at: Optional[datetime] = None
    is_temporary: bool = True

    @model_validator(mode='after')
    def validate_storage(self) -> 'BaseStagingSchema':
        if self.data_size > 0 and not self.storage_path:
            raise ValueError("Storage path is required when data size is greater than 0")
        return self


class BaseRequestSchema(BaseModel):
    """
    Base schema for all request models.
    Provides common request-specific fields.
    """
    request_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    client_info: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class BaseResponseSchema(BaseModel):
    """
    Base schema for all response models.
    Provides common response-specific fields.
    """
    status: ProcessingStatus
    message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    processing_time: float = 0.0

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='after')
    def validate_error_details(self) -> 'BaseResponseSchema':
        if self.status == ProcessingStatus.FAILED and not self.error_details:
            raise ValueError("Error details required for failed status")
        return self


# Utility Mixins for additional functionality
class TimestampMixin(BaseModel):
    """Mixin to add timestamp fields to any schema"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditMixin(BaseModel):
    """Mixin to add audit fields to any schema"""
    created_by: UUID
    updated_by: UUID
    version: int = 1
    change_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MetadataMixin(BaseModel):
    """Mixin to add metadata fields to any schema"""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)
    labels: Dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class BaseSchema(BaseModel):
    """
    Core base schema that all other schemas inherit from.
    Provides common fields and functionality.
    """
    id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        orm_mode = True
        allow_population_by_field_name = True


