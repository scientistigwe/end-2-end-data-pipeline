from sqlalchemy import Column, String, DateTime, Boolean, Enum, ForeignKey, Text, Integer, Float, JSON, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

# Import base model
from .base import Base, BaseModel

# Import all models
from .auth import User, UserSession
from .dataset import Dataset
from .validation import (  # Updated: QualityCheck moved to validation
    ValidationRule,
    QualityCheck,
    ValidationResult,
    RemediationAction
)
from .analysis import (  # Removed QualityCheck from here
    InsightAnalysis,
    Pattern,
    Correlation,
    Anomaly
)
from .data_source import (
    DataSource, APISourceConfig, DatabaseSourceConfig,
    S3SourceConfig, StreamSourceConfig, FileSourceInfo,
    SourceConnection, SourceSyncHistory
)
from .pipeline import (
    Pipeline, PipelineStep, PipelineRun,
    PipelineStepRun, QualityGate
)
from .decisions_recommendations import (
    Decision, DecisionOption, DecisionComment,
    DecisionHistory, Recommendation, RecommendationFeedback
)
from .monitoring import (
    MonitoringMetric, ResourceUsage, Alert,
    AlertRule, HealthCheck
)
from .reports import (
    Report, ReportTemplate, ReportSection,
    ReportSchedule, ReportExecution
)
from .settings import (
    UserSettings, SystemSettings, Integration
)
from .utils import (
    Tag, AuditLog, Notification, Comment, File
)

# Export all models
__all__ = [
    'Base',
    'BaseModel',
    # Dataset
    'Dataset',
    # Validation
    'ValidationRule',
    'QualityCheck',  # Moved to validation section
    'ValidationResult',
    'RemediationAction',
    # Auth
    'User',
    'UserSession',
    # Analysis
    'InsightAnalysis',
    'Pattern',
    'Correlation',
    'Anomaly',
    # Data Sources
    'DataSource',
    'APISourceConfig',
    'DatabaseSourceConfig',
    'S3SourceConfig',
    'StreamSourceConfig',
    'FileSourceInfo',
    'SourceConnection',
    'SourceSyncHistory',
    # Pipeline
    'Pipeline',
    'PipelineStep',
    'PipelineRun',
    'PipelineStepRun',
    'QualityGate',
    # Decisions & Recommendations
    'Decision',
    'DecisionOption',
    'DecisionComment',
    'DecisionHistory',
    'Recommendation',
    'RecommendationFeedback',
    # Monitoring
    'MonitoringMetric',
    'ResourceUsage',
    'Alert',
    'AlertRule',
    'HealthCheck',
    # Reports
    'Report',
    'ReportTemplate',
    'ReportSection',
    'ReportSchedule',
    'ReportExecution',
    # Settings
    'UserSettings',
    'SystemSettings',
    'Integration',
    # Utils
    'Tag',
    'AuditLog',
    'Notification',
    'Comment',
    'File'
]