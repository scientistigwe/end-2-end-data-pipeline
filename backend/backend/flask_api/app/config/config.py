# app/config/config.py
import os
from pathlib import Path


class BaseConfig:
    SECRET_KEY = os.getenv('SECRET_KEY', 'development_secret_key')
    BASE_DIR = Path(__file__).parent.parent

    # File upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'parquet'}

    # CORS settings
    CORS_SETTINGS = {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"]
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    DEVELOPMENT = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    CORS_SETTINGS = {
        "origins": ["https://yourdomain.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}

from pathlib import Path
import os

class Config:
    """Base configuration settings"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'development_secret_key')
    DEBUG = False
    TESTING = False
    BASE_DIR = Path(__file__).parent

    # Core application configurations
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS = {'csv', 'json', 'xlsx', 'parquet'}

    # CORS Configuration
    CORS_SETTINGS = {
        "origins": [
            "http://localhost:3000",  # React default
            "http://localhost:3001",  # Your specific frontend URL
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ],
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Requested-With"
        ]
    }

class DevelopmentConfig(Config):
    """Development-specific configurations"""
    DEBUG = True
    DEVELOPMENT = True

class ProductionConfig(Config):
    """Production-specific configurations"""
    CORS_SETTINGS = {
        "origins": ["https://yourdomain.com"],  # Restrict to production domain
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }

def get_config(env='development'):
    """
    Retrieve configuration based on environment.

    Args:
        env (str): Environment mode

    Returns:
        Config: Configuration class for the specified environment
    """
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    return config_map.get(env, DevelopmentConfig)


# app/config/config.py (add these settings)
class BaseConfig:
    # ... (existing settings)

    # JWT Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Spectacular Settings
    SPECTACULAR_SETTINGS = {
        "TITLE": "Data Pipeline API",
        "DESCRIPTION": "API documentation for the Data Pipeline system",
        "VERSION": "1.0.0",
        "SERVE_INCLUDE_SCHEMA": False,
    }

