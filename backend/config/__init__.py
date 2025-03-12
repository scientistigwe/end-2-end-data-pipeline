# backend/config/__init__.py

from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .app_config import Config, DevelopmentConfig, ProductionConfig, get_config
from .celery_config import CeleryConfig, celery_app
from .config_manager import ConfigurationManager
from .database import DatabaseSettings, DatabaseConfig
from .validation_config import (
    ValidationConfigs,
    FileValidationConfig,
    APIValidationConfig,
    DatabaseValidationConfig,
    StreamValidationConfig,
    S3ValidationConfig,
    StreamType
)

# Configure logging
logger = logging.getLogger(__name__)

# Create base configuration instance
config_manager = ConfigurationManager(
    config_path=str(Path(__file__).parent / 'config.yaml')
)

# Initialize configurations with proper error handling
try:
    # Get application config
    app_config = get_config('development')

    # Initialize Celery configuration
    celery_config = CeleryConfig()

    # Initialize database configuration with singleton pattern
    db_config = DatabaseConfig()
    db_config.configure(app_config)

    logger.info("All configurations initialized successfully")

except Exception as e:
    logger.error(f"Failed to initialize configurations: {str(e)}")
    raise

__all__ = [
    'Config',
    'DevelopmentConfig',
    'ProductionConfig',
    'get_config',
    'CeleryConfig',
    'celery_app',
    'ConfigurationManager',
    'config_manager',
    'DatabaseConfig',
    'DatabaseSettings',
    'db_config',
    'ValidationConfigs',
    'FileValidationConfig',
    'APIValidationConfig',
    'DatabaseValidationConfig',
    'StreamValidationConfig',
    'S3ValidationConfig',
    'StreamType'
]