# backend/db/types/__init__.py
import logging
from sqlalchemy import Column, String, DateTime, Boolean, Enum, ForeignKey, Text, Integer, Float, JSON, Table
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from .auth import User
from .events import EventSubscription

logger = logging.getLogger(__name__)

try:
    logger.info("Importing base model...")
    from .base import Base, BaseModel

    # Import all types with error handling
    logger.info("Importing auth types...")
    from .auth import User, UserSession, UserActivityLog

    logger.info("Importing dataset model...")
    from .dataset import Dataset

    logger.info("Importing validation types...")
    from .validation import (
        ValidationRule,
        QualityCheck,
        ValidationResult,
        RemediationAction
    )

    logger.info("Importing analysis types...")
    from .insight_model import (
        InsightRun,
        Insight,
        InsightFeedback,
        InsightAction,
        InsightImpact,
        InsightPattern,
        InsightCorrelation,
        InsightGoalMapping
    )

    logger.info("Importing data source types...")
    from .data_source import (
        DataSource, APISourceConfig, DatabaseSourceConfig,
        S3SourceConfig, StreamSourceConfig, FileSourceInfo,
        SourceConnection, SourceSyncHistory
    )

    logger.info("Importing pipeline types...")
    from .pipeline import (
        Pipeline, PipelineStep, PipelineRun,
        PipelineStepRun, QualityGate, PipelineLog, PipelineVersion, PipelineTemplate
    )

    logger.info("Importing decision types...")
    from .decision import Decision, DecisionOption, DecisionComment, DecisionHistory

    logger.info("Importing recommendation types...")
    from .recommendation import Recommendation, RecommendationFeedback


    logger.info("Importing monitoring types...")
    from .monitoring import MonitoringMetric, ResourceUsage, Alert, AlertRule, HealthCheck

    logger.info("Importing report types...")
    from .report_model import (
        ReportVisualization,
        ReportValidation,
        ReportTemplate,
        ReportSection,
        ReportSchedule,
        ReportRun
    )

    logger.info("Importing settings types...")
    from .settings import (
        UserSettings, SystemSettings, Integration
    )

    logger.info("Importing utility types...")
    from .utils import (
        Tag, AuditLog, Notification, Comment, File
    )

    logger.info("Importing staging types...")
    from .staging_model import StagingDecision, StagingEvent, StagingModification, StagedResource

    logger.info("Importing event types...")
    from .events import EventSubscription, Event, EventProcessor

    logger.info("Importing advanced_analytics analytics types...")
    from .advanced_analytics_model import (
        AnalyticsModel,
        AnalyticsRun,
        AnalyticsResult,
        AnalyticsFeature,
        AnalyticsVisualization,
    )
    logger.info("All types imported successfully")

except Exception as e:
    logger.error(f"Error importing types: {str(e)}")
    import traceback

    logger.error(f"Traceback: {traceback.format_exc()}")
    raise

# Export all types
__all__ = [
    'Base',
    'BaseModel',

    # Dataset
    'Dataset',

    # Validation
    'ValidationRule',
    'QualityCheck',
    'ValidationResult',
    'RemediationAction',

    # Auth
    'User',
    'UserSession',
    'UserActivityLog',

    # Analysis
    'InsightRun',
    'Insight',
    'InsightFeedback',
    'InsightAction',
    'InsightImpact',
    'InsightPattern',
    'InsightCorrelation',
    'InsightGoalMapping',

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
    'PipelineLog',
    'PipelineVersion',
    'PipelineTemplate',

    # Decision
    'Decision',
    'DecisionOption',
    'DecisionComment',
    'DecisionHistory',

    # Recommendation
    'Recommendation',
    'RecommendationFeedback',

    # Monitoring
    'MonitoringMetric',
    'ResourceUsage',
    'Alert',
    'AlertRule',
    'HealthCheck',

    # Report
    'ReportVisualization',
    'ReportValidation',
    'ReportTemplate',
    'ReportSection',
    'ReportSchedule',
    'ReportRun',

    # Settings
    'UserSettings',
    'SystemSettings',
    'Integration',

    # Utils
    'Tag',
    'AuditLog',
    'Notification',
    'Comment',
    'File',

    # Staging Model
    'StagingDecision',
    'StagingEvent',
    'StagingModification',
    'StagedResource',

    # Events
    'EventSubscription',
    'Event',
    'EventProcessor',

    # Advanced Analytics Models
    'AnalyticsModel',
    'AnalyticsRun',
    'AnalyticsResult',
    'AnalyticsFeature',
    'AnalyticsVisualization',
]