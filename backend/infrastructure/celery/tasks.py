<<<<<<< HEAD
# backend/infrastructure/celery/tasks.py

from celery import shared_task
from typing import Dict, Any
import logging

from .celery import celery_app
from core.services import (
    FileProcessingService,
    AnalysisService,
    InsightService
)

logger = logging.getLogger(__name__)


class TaskBase:
    """Base class for Celery tasks with common error handling and logging."""

    @staticmethod
    def handle_error(task_instance, exc, task_name: str, **kwargs):
        """Common error handling logic for tasks."""
        logger.error(
            f"Error in {task_name}: {str(exc)}",
            extra={
                'task_id': task_instance.request.id,
                'args': kwargs
            }
        )
        raise task_instance.retry(exc=exc)
=======
# tasks.py
from celery import shared_task
from .config import celery_app
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce


@shared_task(
    bind=True,
<<<<<<< HEAD
    base=TaskBase,
=======
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
    max_retries=3,
    soft_time_limit=300,
    name='tasks.process_file'
)
<<<<<<< HEAD
def process_file(self, file_id: str) -> Dict[str, Any]:
    """
    Process uploaded file through the data pipeline.

    Args:
        file_id: Unique identifier for the file to process

    Returns:
        Dict containing processing results and metadata
    """
    try:
        service = FileProcessingService()
        result = service.process_file(file_id)

        logger.info(
            f"File processing completed",
            extra={
                'task_id': self.request.id,
                'file_id': file_id,
                'status': 'completed'
            }
        )

        return result

    except Exception as exc:
        self.handle_error(self, exc, 'process_file', file_id=file_id)
=======
def process_file(self, file_id: str):
    """Process uploaded file"""
    try:
        # File processing logic here
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce


@shared_task(
    bind=True,
<<<<<<< HEAD
    base=TaskBase,
=======
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
    max_retries=3,
    soft_time_limit=600,
    name='tasks.analyze_data'
)
<<<<<<< HEAD
def analyze_data(self, file_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze processed data with given context parameters.

    Args:
        file_id: Identifier for the processed file
        context: Analysis parameters and configuration

    Returns:
        Dict containing analysis results and metadata
    """
    try:
        service = AnalysisService()
        result = service.analyze_data(file_id, context)

        logger.info(
            f"Data analysis completed",
            extra={
                'task_id': self.request.id,
                'file_id': file_id,
                'analysis_type': context.get('type')
            }
        )

        return result

    except Exception as exc:
        self.handle_error(self, exc, 'analyze_data', file_id=file_id, context=context)
=======
def analyze_data(self, file_id: str, context: dict):
    """Analyze processed data"""
    try:
        # Analysis logic here
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=120)
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce


@shared_task(
    bind=True,
<<<<<<< HEAD
    base=TaskBase,
=======
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
    max_retries=3,
    soft_time_limit=300,
    name='tasks.generate_insights'
)
<<<<<<< HEAD
def generate_insights(self, analysis_id: str) -> Dict[str, Any]:
    """
    Generate insights from completed analysis.

    Args:
        analysis_id: Identifier for the completed analysis

    Returns:
        Dict containing generated insights and metadata
    """
    try:
        service = InsightService()
        result = service.generate_insights(analysis_id)

        logger.info(
            f"Insight generation completed",
            extra={
                'task_id': self.request.id,
                'analysis_id': analysis_id
            }
        )

        return result

    except Exception as exc:
        self.handle_error(self, exc, 'generate_insights', analysis_id=analysis_id)
=======
def generate_insights(self, analysis_id: str):
    """Generate insights from analysis"""
    try:
        # Insight generation logic here
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=60)
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
