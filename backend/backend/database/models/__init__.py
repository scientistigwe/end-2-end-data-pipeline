# backend/database/models/__init__.py
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

    logger.info("Importing data source models...")
    from .data_source import (
        DataSource, APISourceConfig, DatabaseSourceConfig,
        S3SourceConfig, StreamSourceConfig, FileSourceInfo,
        SourceConnection, SourceSyncHistory
    )

    logger.info("Importing pipeline models...")
    from .pipeline import (
        Pipeline, PipelineStep, PipelineRun,
        PipelineStepRun, QualityGate, PipelineLog, PipelineVersion, PipelineTemplate
    )

    logger.info("Importing decision models...")
    from .decision import Decision, DecisionOption, DecisionComment, DecisionHistory

    logger.info("Importing recommendation models...")
    from .recommendation import Recommendation, RecommendationFeedback


    logger.info("Importing monitoring models...")
    from .monitoring import MonitoringMetric, ResourceUsage, Alert, AlertRule, HealthCheck

    logger.info("Importing report models...")
    from .report_model import (
        ReportVisualization,
        ReportValidation,
        ReportTemplate,
        ReportSection,
        ReportSchedule,
        ReportRun
    )

    logger.info("Importing settings models...")
    from .settings import (
        UserSettings, SystemSettings, Integration
    )

    logger.info("Importing utility models...")
    from .utils import (
        Tag, AuditLog, Notification, Comment, File
    )

    logger.info("Importing staging models...")
    from .staging_model import StagingDecision, StagingEvent, StagingModification, StagedResource

    logger.info("Importing event models...")
    from .events import EventSubscription, Event, EventProcessor

    logger.info("Importing advanced analytics models...")
    from .advanced_analytics_model import (
        AnalyticsModel,
        AnalyticsRun,
        AnalyticsResult,
        AnalyticsFeature,
        AnalyticsVisualization,
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