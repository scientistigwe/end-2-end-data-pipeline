# backend/config/app_config.py

import os
from pathlib import Path
from typing import Dict, Any


class Config:
    """Base configuration class for Flask application."""

    def __init__(self):
        # Core paths
        self.BASE_DIR = Path(__file__).parent.parent
        self.UPLOAD_FOLDER = self.BASE_DIR / 'uploads'
        self.LOG_FOLDER = self.BASE_DIR / 'logs'
        self.STAGING_FOLDER = self.BASE_DIR / 'staging'

        # Flask configuration
        self.SECRET_KEY = os.getenv('SECRET_KEY')
        self.ENV = os.getenv('FLASK_ENV', 'development')

        # Database configuration
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False

        # Logging configuration
        self.LOG_FILENAME = 'app.log'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # Security configuration
        self.JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
        self.JWT_PRIVATE_KEY = os.getenv('JWT_PRIVATE_KEY')
        self.JWT_PUBLIC_KEY = os.getenv('JWT_PUBLIC_KEY')
        self.JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
        self.ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

        # CORS configuration
        self.CORS_SETTINGS = {
            'origins': [os.getenv('VITE_API_URL', 'http://localhost:3000')],
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': ['Content-Type', 'Authorization'],
            'supports_credentials': True
        }


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    def __init__(self):
        super().__init__()
        self.CORS_SETTINGS['origins'] = [os.getenv('PRODUCTION_DOMAIN')]


def get_config(config_name: str) -> Config:
    """Get configuration by name."""
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    return configs.get(config_name, DevelopmentConfig)()