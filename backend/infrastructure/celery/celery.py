# backend/infrastructure/celery/celery.py

from celery import Celery
from config import celery_config

# Initialize Celery app with configuration
celery_app = Celery('analyst_pa')
celery_app.config_from_object(celery_config)