# tasks.py
from celery import shared_task
from .config import celery_app


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=300,
    name='tasks.process_file'
)
def process_file(self, file_id: str):
    """Process uploaded file"""
    try:
        # File processing logic here
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=60)


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=600,
    name='tasks.analyze_data'
)
def analyze_data(self, file_id: str, context: dict):
    """Analyze processed data"""
    try:
        # Analysis logic here
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=120)


@shared_task(
    bind=True,
    max_retries=3,
    soft_time_limit=300,
    name='tasks.generate_insights'
)
def generate_insights(self, analysis_id: str):
    """Generate insights from analysis"""
    try:
        # Insight generation logic here
        pass
    except Exception as exc:
        self.retry(exc=exc, countdown=60)