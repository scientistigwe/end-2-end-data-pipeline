# schemas/__init__.py
from .base import BaseRequestSchema, BaseResponseSchema

# Authentication schemas
from .auth import (
    LoginRequestSchema,
    LoginResponseSchema,
    RegisterRequestSchema,
    RegisterResponseSchema,
    TokenResponseSchema,
    PasswordResetRequestSchema,
    PasswordResetResponseSchema,
    EmailVerificationRequestSchema,
    EmailVerificationResponseSchema,
    ChangePasswordRequestSchema,
    ChangePasswordResponseSchema,
    UserProfileResponseSchema
)

# Pipeline schemas
from .pipeline import (
    PipelineListResponseSchema,
    PipelineRequestSchema,
    PipelineResponseSchema,
    PipelineUpdateRequestSchema,
    PipelineStartRequestSchema,
    PipelineStartResponseSchema,
    PipelineStatusResponseSchema,
    PipelineLogsRequestSchema,
    PipelineLogsResponseSchema,
    PipelineMetricsResponseSchema,
    PipelineConfigValidationRequestSchema,
    PipelineConfigValidationResponseSchema
)

# Analysis schemas
from .analysis import (
    QualityCheckRequestSchema,
    QualityCheckResponseSchema,
    InsightAnalysisRequestSchema,
    InsightAnalysisResponseSchema
)

# Data source schemas
from .data_sources.data_source import (
    DataSourceRequestSchema, 
    DataSourceResponseSchema
)
from .data_sources.file_source import (
    FileSourceConfigSchema, 
    FileSourceResponseSchema, 
    FileUploadRequestSchema, 
    FileMetadataResponseSchema
)
from .data_sources.database_source import (
    DatabaseSourceConfigSchema, 
    DatabaseSourceResponseSchema
)
from .data_sources.api_source import (
    APISourceConfigSchema, 
    APISourceResponseSchema
)
from .data_sources.s3_source import (
    S3SourceConfigSchema, 
    S3SourceResponseSchema
)
from .data_sources.stream_source import (
    StreamSourceConfigSchema, 
    StreamSourceResponseSchema
)

# Decision and recommendation schemas
from .decisions import (
    DecisionRequestSchema,
    DecisionResponseSchema,
    DecisionListResponseSchema,
    DecisionHistoryResponseSchema,
    DecisionImpactResponseSchema,
    DecisionFeedbackRequestSchema,
    DecisionFeedbackResponseSchema
)
from .recommendations import (
    RecommendationRequestSchema,
    RecommendationResponseSchema,
    RecommendationListResponseSchema,
    RecommendationStatusResponseSchema,
    RecommendationApplyRequestSchema,
    RecommendationDismissRequestSchema,
    RecommendationFeedbackRequestSchema,
    RecommendationFeedbackResponseSchema
)

# Monitoring schemas
from .monitoring import (
    MetricsRequestSchema,
    MetricsResponseSchema,
    HealthStatusResponseSchema,
    PerformanceMetricsResponseSchema,
    AlertConfigRequestSchema,
    AlertConfigResponseSchema,
    AlertHistoryResponseSchema,
    ResourceUsageResponseSchema,
    AggregatedMetricsResponseSchema
)

# Report schemas
from .reports import (
    ReportRequestSchema,
    ReportResponseSchema
)

# Validation schemas
from .validation import (
    ValidationResultRequestSchema,
    ValidationResultResponseSchema
)

# Settings schemas
from .settings import (
    UserSettingsRequestSchema,
    SystemSettingsRequestSchema
)

__all__ = [
    # Base schemas
    'BaseRequestSchema',
    'BaseResponseSchema',
    
    # Auth schemas
    'LoginRequestSchema',
    'LoginResponseSchema',
    'RegisterRequestSchema',
    'RegisterResponseSchema',
    'TokenResponseSchema',
    'PasswordResetRequestSchema',
    'PasswordResetResponseSchema',
    'EmailVerificationRequestSchema',
    'EmailVerificationResponseSchema',
    'ChangePasswordRequestSchema',
    'ChangePasswordResponseSchema',
    'UserProfileResponseSchema',
    'UserProfileUpdateRequestSchema',
    
    # Pipeline schemas
    'PipelineListResponseSchema',
    'PipelineRequestSchema',
    'PipelineResponseSchema',
    'PipelineUpdateRequestSchema',
    'PipelineStartRequestSchema',
    'PipelineStartResponseSchema',
    'PipelineStatusResponseSchema',
    'PipelineLogsRequestSchema',
    'PipelineLogsResponseSchema',
    'PipelineMetricsResponseSchema',
    'PipelineConfigValidationRequestSchema',
    'PipelineConfigValidationResponseSchema',
    
    # Analysis schemas
    'QualityCheckRequestSchema',
    'QualityCheckResponseSchema',
    'InsightAnalysisRequestSchema',
    'InsightAnalysisResponseSchema',
    
    # Data source schemas
    'DataSourceRequestSchema',
    'DataSourceResponseSchema',
    'FileSourceConfigSchema',
    'FileSourceResponseSchema',
    'FileUploadRequestSchema',
    'FileMetadataResponseSchema',
    'DatabaseSourceConfigSchema',
    'DatabaseSourceResponseSchema',
    'APISourceConfigSchema',
    'APISourceResponseSchema',
    'S3SourceConfigSchema',
    'S3SourceResponseSchema',
    'StreamSourceConfigSchema',
    'StreamSourceResponseSchema',
    
    # Decision schemas
    'DecisionRequestSchema',
    'DecisionResponseSchema',
    'DecisionListResponseSchema',
    'DecisionHistoryResponseSchema',
    'DecisionImpactResponseSchema',
    'DecisionFeedbackRequestSchema',
    'DecisionFeedbackResponseSchema',
    
    # Recommendation schemas
    'RecommendationRequestSchema',
    'RecommendationResponseSchema',
    'RecommendationListResponseSchema',
    'RecommendationStatusResponseSchema',
    'RecommendationApplyRequestSchema',
    'RecommendationDismissRequestSchema',
    'RecommendationFeedbackRequestSchema',
    'RecommendationFeedbackResponseSchema',
    
    # Monitoring schemas
    'MetricsRequestSchema',
    'MetricsResponseSchema',
    'HealthStatusResponseSchema',
    'PerformanceMetricsResponseSchema',
    'AlertConfigRequestSchema',
    'AlertConfigResponseSchema',
    'AlertHistoryResponseSchema',
    'ResourceUsageResponseSchema',
    'AggregatedMetricsResponseSchema',
    
    # Report schemas
    'ReportRequestSchema',
    'ReportResponseSchema',
    
    # Validation schemas
    'ValidationResultRequestSchema',
    'ValidationResultResponseSchema',
    
    # Settings schemas
    'UserSettingsRequestSchema',
    'SystemSettingsRequestSchema'
]