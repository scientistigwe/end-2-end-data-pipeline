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

    logger.info("Importing staging types...")
    from .staging.base_staging_model import BaseStagedOutput
    from .staging.advanced_analytics_output_model import StagedAnalyticsOutput
    from .staging.insight_output_model import StagedInsightOutput
    from .staging.quality_output_model import StagedQualityOutput
    from .staging.report_output_model import StagedReportOutput
    from .staging.staging_control_model import StagingControlPoint
    from .staging.staging_history_model import StagingProcessingHistory

    logger.info("Importing event types...")
    from .events import EventSubscription, Event, EventProcessor

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

    # Auth
    'User',
    'UserSession',
    'UserActivityLog',

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

    # Events
    'EventSubscription',
    'Event',
    'EventProcessor',
]