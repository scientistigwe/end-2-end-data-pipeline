# backend/database/models/__init__.py
import logging
from sqlalchemy import Column, String, DateTime, Boolean, Enum, ForeignKey, Text, Integer, Float, JSON, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

logger = logging.getLogger(__name__)

try:
    logger.info("Importing base model...")
    from .base import Base, BaseModel

    # Import all models with error handling
    logger.info("Importing auth models...")
    from .auth import User, UserSession, UserActivityLog

    logger.info("Importing dataset model...")
    from .dataset import Dataset

    logger.info("Importing validation models...")
    from .validation import (
        ValidationRule,
        QualityCheck,
        ValidationResult,
        RemediationAction
    )

    logger.info("Importing analysis models...")
    from .analysis import (
        InsightAnalysis,
        Pattern,
        Correlation,
        Anomaly
    )

    logger.info("Importing data source models...")
    from .data_source import (
        DataSource, APISourceConfig, DatabaseSourceConfig,
        S3SourceConfig, StreamSourceConfig, FileSourceInfo,
        SourceConnection, SourceSyncHistory
    )

    logger.info("Importing pipeline models...")
    from .pipeline import (
        Pipeline, PipelineStep, PipelineRun,
        PipelineStepRun, QualityGate
    )

    logger.info("Importing decisions and recommendations models...")
    from .decisions_recommendations import (
        Decision, DecisionOption, DecisionComment,
        DecisionHistory, Recommendation, RecommendationFeedback
    )

    logger.info("Importing monitoring models...")
    from .monitoring import (
        MonitoringMetric, ResourceUsage, Alert,
        AlertRule, HealthCheck
    )

    logger.info("Importing report models...")
    from .reports import (
        Report, ReportTemplate, ReportSection,
        ReportSchedule, ReportExecution
    )

    logger.info("Importing settings models...")
    from .settings import (
        UserSettings, SystemSettings, Integration
    )

    logger.info("Importing utility models...")
    from .utils import (
        Tag, AuditLog, Notification, Comment, File
    )

    logger.info("All models imported successfully")

except Exception as e:
    logger.error(f"Error importing models: {str(e)}")
    import traceback

    logger.error(f"Traceback: {traceback.format_exc()}")
    raise

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
    'UserActivityLog',
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