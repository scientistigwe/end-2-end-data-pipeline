# backend/config/celery_config.py

from celery import Celery
from kombu import Exchange, Queue
import os

celery_app = Celery('analyst_pa')


class CeleryConfig:
    """Celery task queue configuration."""

    # Broker settings
    broker_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    result_backend = os.getenv('REDIS_URL', 'redis://redis:6379/0')

    # Task settings
    task_serializer = 'json'
    result_serializer = 'json'
    accept_content = ['json']
    timezone = 'UTC'
    enable_utc = True

    # Queue definitions
    task_queues = (
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('file_processing', Exchange('file_processing'), routing_key='file_processing'),
        Queue('insight', Exchange('insight'), routing_key='insight'),
        Queue('insights', Exchange('insights'), routing_key='insights'),
    )

    # Task routing
    task_routes = {
        'tasks.process_file': {'queue': 'file_processing'},
        'tasks.analyze_data': {'queue': 'insight'},
        'tasks.generate_insights': {'queue': 'insights'},
    }

    # Task execution
    task_acks_late = True
    worker_prefetch_multiplier = 1
    task_always_eager = False

    # Retry policies
    task_publish_retry = True
    task_publish_retry_policy = {
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    }


# Apply Celery configuration
celery_app.config_from_object(CeleryConfig)