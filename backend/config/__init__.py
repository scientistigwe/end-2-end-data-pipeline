# backend/config/__init__.py

from pathlib import Path
from typing import Dict, Any, Optional

from .app_config import Config, DevelopmentConfig, ProductionConfig, get_config
from .celery_config import CeleryConfig, celery_app
from .config_manager import ConfigurationManager
from .database import DatabaseConfig

# Create base configuration instance
config_manager = ConfigurationManager(
    config_path=str(Path(__file__).parent / 'config.yaml')
)

# Initialize configurations
app_config = get_config('development')
celery_config = CeleryConfig()
db_config = DatabaseConfig(app_config)

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
    'db_config'
]