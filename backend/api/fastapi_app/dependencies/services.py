# api/fastapi_app/dependencies/services.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from core.services.quality import QualityService
from core.services.advanced_analytics import AnalyticsService
from core.services.insight import InsightService
from core.services.reports import ReportService
from core.services.recommendation import RecommendationService
from config.database import get_db_session
from core.services.pipeline.pipeline_service import PipelineService
from core.managers.staging_manager import StagingManager


# Cache for service instances
_pipeline_service_instance: Optional[PipelineService] = None
_staging_manager_instance: Optional[StagingManager] = None

# Cache instances
_service_instances = {}

async def get_analytics_service(
    db: AsyncSession = Depends(get_db_session)
) -> AnalyticsService:
    if 'analytics' not in _service_instances:
        _service_instances['analytics'] = AnalyticsService(db)
    return _service_instances['analytics']

async def get_insight_service(
    db: AsyncSession = Depends(get_db_session)
) -> InsightService:
    if 'insight' not in _service_instances:
        _service_instances['insight'] = InsightService(db)
    return _service_instances['insight']

async def get_quality_service(
    db: AsyncSession = Depends(get_db_session)
) -> QualityService:
    if 'quality' not in _service_instances:
        _service_instances['quality'] = QualityService(db)
    return _service_instances['quality']

async def get_staging_service(
    db: AsyncSession = Depends(get_db_session)
) -> StagingManager:
    if 'staging' not in _service_instances:
        _service_instances['staging'] = StagingManager(db)
    return _service_instances['staging']

async def get_report_service(
    db: AsyncSession = Depends(get_db_session)
) -> ReportService:
    if 'report' not in _service_instances:
        _service_instances['report'] = ReportService(db)
    return _service_instances['report']

async def get_recommendation_service(
    db: AsyncSession = Depends(get_db_session)
) -> RecommendationService:
    if 'recommendation' not in _service_instances:
        _service_instances['recommendation'] = RecommendationService(db)
    return _service_instances['recommendation']

async def get_staging_manager(
    db: AsyncSession = Depends(get_db_session)
) -> StagingManager:
    if 'staging_manager' not in _service_instances:
        _service_instances['staging_manager'] = StagingManager(db)
    return _service_instances['staging_manager']

async def get_pipeline_service(
    db: AsyncSession = Depends(get_db_session)
) -> PipelineService:
    """Get or create PipelineService instance"""
    global _pipeline_service_instance
    if not _pipeline_service_instance:
        _pipeline_service_instance = PipelineService(db)
    return _pipeline_service_instance
