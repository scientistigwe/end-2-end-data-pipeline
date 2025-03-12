# backend/db/models/__init__.py

from .core.base import Base, BaseModel

# Auth Models
from .auth.user import (
    User, UserActivityLog, PasswordResetToken, ServiceAccount
)
from .auth.session import (
    UserSession, SessionDevice, RefreshToken
)
from .auth.team import (
    Team, TeamMember, TeamResource, TeamInvitation
)

# Data Source Models
from .data.sources import (
    DataSource, DatabaseSourceConfig, APISourceConfig,
    S3SourceConfig, StreamSourceConfig, FileSourceInfo,
    SourceConnection, SourceSyncHistory,
    DatabaseDataSource, APIDataSource, S3DataSource,
    StreamDataSource, FileDataSource
)

# Pipeline Models
from .data.pipeline import (
    Pipeline, PipelineStep, PipelineRun, PipelineStepRun,
    QualityGate, QualityCheck, PipelineLog, PipelineTemplate,
    PipelineVersion, PipelineSchedule, Tag, PipelineDependency
)

# Staging Models - Base
from .staging.base import (
    BaseStagedOutput, StagingProcessingHistory,
    StagingControlPoint
)

# Staging Models - Processing
from .staging.processing import (
    StagedMonitoringOutput,
    StagedQualityOutput,
    StagedRecommendationOutput,
    StagedAnalyticsOutput,
    StagedInsightOutput,
    StagedDecisionOutput
)

# Staging Models - Reporting
from .staging.reporting import (
    StagedReportOutput,
    StagedMetricsOutput,
    StagedComplianceReport
)

__all__ = [
    # Base
    'Base',
    'BaseModel',

    # Auth Models
    'User',
    'UserActivityLog',
    'PasswordResetToken',
    'ServiceAccount',
    'UserSession',
    'SessionDevice',
    'RefreshToken',
    'Team',
    'TeamMember',
    'TeamResource',
    'TeamInvitation',

    # Data Source Models
    'DataSource',
    'DatabaseSourceConfig',
    'APISourceConfig',
    'S3SourceConfig',
    'StreamSourceConfig',
    'FileSourceInfo',
    'SourceConnection',
    'SourceSyncHistory',
    'DatabaseDataSource',
    'APIDataSource',
    'S3DataSource',
    'StreamDataSource',
    'FileDataSource',

    # Pipeline Models
    'Pipeline',
    'PipelineStep',
    'PipelineRun',
    'PipelineStepRun',
    'QualityGate',
    'QualityCheck',
    'PipelineLog',
    'PipelineTemplate',
    'PipelineVersion',
    'PipelineSchedule',
    'Tag',
    'PipelineDependency',

    # Staging Models - Base
    'BaseStagedOutput',
    'StagingProcessingHistory',
    'StagingControlPoint',

    # Staging Models - Analytics
    'StagedAnalyticsOutput',
    'StagedInsightOutput',
    'StagedDecisionOutput',

    # Staging Models - Processing
    'StagedMonitoringOutput',
    'StagedQualityOutput',
    'StagedRecommendationOutput',

    # Staging Models - Reporting
    'StagedReportOutput',
    'StagedMetricsOutput',
    'StagedComplianceReport'
]

# Ensure all models are loaded
import logging

logger = logging.getLogger(__name__)
logger.info(f"Loaded {len(__all__)} models")