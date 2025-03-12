"""
Celery Configuration Module

This module provides a comprehensive configuration for Celery task queue management.
It includes settings for task routing, execution, monitoring, and performance optimization.

Features:
    - Redis-based message broker and result backend
    - Multiple task queues with specific routing
    - Optimized worker settings
    - Comprehensive retry policies
    - Performance monitoring
    - Resource limits and safeguards

Usage:
    from config.celery_config import celery_app

    @celery_app.task(queue='file_processing')
    def process_file(file_path: str):
        pass
"""

from celery import Celery
from kombu import Exchange, Queue
from typing import Dict, Any, Tuple, List
import os
from pathlib import Path

# Initialize Celery application
celery_app = Celery('analyst_pa')


class CeleryConfig:
    """
    Celery task queue configuration with comprehensive settings.

    This class defines all Celery-related configuration including broker settings,
    task routing, execution parameters, monitoring, and resource limits.

    Attributes:
        broker_url (str): Redis broker connection URL
        result_backend (str): Redis result backend URL
        task_queues (Tuple[Queue, ...]): Defined task queues with exchanges
        task_routes (Dict[str, Dict[str, str]]): Task routing configuration
        worker_max_tasks_per_child (int): Maximum tasks per worker before restart
        worker_max_memory_per_child (int): Memory limit per worker in KB
    """

    # Base directory for file operations
    BASE_DIR = Path(__file__).parent.parent

    # Broker and backend settings
    broker_url: str = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    result_backend: str = os.getenv('REDIS_URL', 'redis://redis:6379/0')

    # Serialization settings
    task_serializer: str = 'json'
    result_serializer: str = 'json'
    accept_content: Tuple[str, ...] = ('json',)
    timezone: str = 'UTC'
    enable_utc: bool = True

    # Queue definitions with explicit exchange types
    task_queues: Tuple[Queue, ...] = (
        Queue(
            'default',
            Exchange('default', type='direct', durable=True),
            routing_key='default',
            queue_arguments={'x-max-priority': 10}
        ),
        Queue(
            'file_processing',
            Exchange('file_processing', type='direct', durable=True),
            routing_key='file_processing',
            queue_arguments={'x-max-priority': 5}
        ),
        Queue(
            'insight',
            Exchange('insight', type='direct', durable=True),
            routing_key='insight',
            queue_arguments={'x-max-priority': 3}
        ),
        Queue(
            'insights',
            Exchange('insights', type='direct', durable=True),
            routing_key='insights',
            queue_arguments={'x-max-priority': 3}
        ),
    )

    # Task routing configuration
    task_routes: Dict[str, Dict[str, str]] = {
        'tasks.process_file': {'queue': 'file_processing'},
        'tasks.analyze_data': {'queue': 'insight'},
        'tasks.generate_insights': {'queue': 'insights'},
    }

    # Performance and execution settings
    task_acks_late: bool = True  # Tasks acknowledged after execution
    worker_prefetch_multiplier: int = 1  # One task per worker at a time
    task_always_eager: bool = False  # Never execute tasks eagerly in production
    worker_max_tasks_per_child: int = 1000  # Restart worker after 1000 tasks
    worker_max_memory_per_child: int = 50000  # 50MB memory limit per worker

    # Retry policies
    task_publish_retry: bool = True
    task_publish_retry_policy: Dict[str, Any] = {
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 0.5,
    }

    # Task time limits (in seconds)
    task_soft_time_limit: int = 300  # 5 minutes soft limit
    task_time_limit: int = 600  # 10 minutes hard limit

    # Task result settings
    task_ignore_result: bool = False
    result_expires: int = 24 * 60 * 60  # Results expire after 24 hours

    # Additional optimizations and monitoring
    worker_send_task_events: bool = True  # Enable task events for monitoring
    task_send_sent_event: bool = True  # Track task sending
    worker_disable_rate_limits: bool = True  # Disable rate limits for better performance
    task_track_started: bool = True  # Track when tasks are started
    task_store_errors_even_if_ignored: bool = True  # Store error info even for ignored tasks

    # File processing specific settings
    task_annotations: Dict[str, Dict[str, Any]] = {
        'tasks.process_file': {
            'rate_limit': '10/m',  # Limit to 10 file processing tasks per minute
            'time_limit': 1800,  # 30 minutes timeout for file processing
            'soft_time_limit': 1500  # 25 minutes soft timeout
        },
        'tasks.analyze_data': {
            'rate_limit': '30/m',  # Limit to 30 analysis tasks per minute
        }
    }

    # Logging configuration
    worker_log_format = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    worker_task_log_format = (
        "[%(asctime)s: %(levelname)s/%(processName)s] "
        "[%(task_name)s(%(task_id)s)] %(message)s"
    )

    @classmethod
    def get_task_queues(cls) -> List[str]:
        """Get list of available task queue names.

        Returns:
            List[str]: List of queue names
        """
        return [queue.name for queue in cls.task_queues]

    @classmethod
    def get_queue_for_task(cls, task_name: str) -> str:
        """Get queue name for specific task.

        Args:
            task_name (str): Full task name including module

        Returns:
            str: Queue name or 'default' if not found
        """
        return cls.task_routes.get(task_name, {}).get('queue', 'default')


# Apply Celery configuration
celery_app.config_from_object(CeleryConfig)


# Register task error handler
@celery_app.on_after_configure.connect
def setup_error_handlers(sender, **kwargs):
    """Setup error handlers for Celery tasks.

    This function is called after Celery is configured to set up error handling.
    """

    @sender.task_failure.connect
    def handle_task_failure(task_id, exception, args, kwargs, traceback, einfo):
        """Handle task failures by logging detailed error information."""
        error_msg = (
            f"Task {task_id} failed: {str(exception)}\n"
            f"Args: {args}\nKwargs: {kwargs}\n"
            f"Traceback: {einfo}"
        )
        sender.logger.error(error_msg)