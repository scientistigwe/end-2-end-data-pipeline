# backend/config/app_config.py

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    field_validator,
    ConfigDict
)
from pydantic_settings import BaseSettings


class Config:
    """Base configuration class maintaining original Flask-like structure."""

    def __init__(self):
        # Core paths
        self.BASE_DIR = Path(__file__).parent.parent
        self.UPLOAD_FOLDER = self.BASE_DIR / 'uploads'
        self.LOG_FOLDER = self.BASE_DIR / 'logs'
        self.STAGING_FOLDER = self.BASE_DIR / 'staging'

        # Application environment
        self.ENV = os.getenv('FLASK_ENV', 'development')
        self.SECRET_KEY = os.getenv('SECRET_KEY')

        # Database configuration
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', 5))
        self.SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', 10))
        self.SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('SQLALCHEMY_POOL_TIMEOUT', 30))
        self.SQLALCHEMY_ISOLATION_LEVEL = os.getenv('SQLALCHEMY_ISOLATION_LEVEL', 'READ_COMMITTED')
        self.SQLALCHEMY_ECHO = False

        # Logging configuration
        self.LOG_FILENAME = 'app.log'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # JWT Configuration
        self.JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
        self.JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
        self.JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days

        # JWT Cookie Configuration
        self.JWT_TOKEN_LOCATION = ['cookies']
        self.JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
        self.JWT_REFRESH_COOKIE_NAME = 'refresh_token_cookie'
        self.JWT_ACCESS_COOKIE_PATH = '/'
        self.JWT_REFRESH_COOKIE_PATH = '/api/v1/auth/refresh'
        self.JWT_COOKIE_CSRF_PROTECT = False
        self.JWT_COOKIE_SECURE = self.ENV != 'development'
        self.JWT_COOKIE_SAMESITE = 'Lax' if self.ENV == 'development' else 'Strict'

        # CORS Settings
        self.CORS_SETTINGS = {
            'origins': [
                'http://localhost:3000',
                'http://localhost:5000',
                'http://localhost:5173',
                os.getenv('FRONTEND_URL', ''),
                os.getenv('PRODUCTION_DOMAIN', '')
            ],
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': [
                'Content-Type',
                'Authorization',
                'X-CSRF-TOKEN',
                'X-Requested-With'
            ],
            'expose_headers': [
                'Content-Type',
                'Authorization',
                'Set-Cookie'
            ],
            'supports_credentials': True,
            'max_age': 600
        }

        # Additional Security Headers
        self.SECURITY_HEADERS = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block'
        }

        # Additional optional configurations
        self.JWT_PRIVATE_KEY = os.getenv('JWT_PRIVATE_KEY')
        self.JWT_PUBLIC_KEY = os.getenv('JWT_PUBLIC_KEY')
        self.ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
        self.LOG_FILE_PATH = os.getenv('LOG_FILE_PATH')
        self.ENABLE_SSL = os.getenv('ENABLE_SSL', 'False').lower() == 'true'
        self.SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')
        self.PRODUCTION_DOMAIN = os.getenv('PRODUCTION_DOMAIN')
        self.API_DOMAIN = os.getenv('API_DOMAIN')
        self.VITE_API_URL = os.getenv('VITE_API_URL')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False

    def __init__(self):
        super().__init__()
        # Override CORS origins for production
        self.CORS_SETTINGS['origins'] = [
            os.getenv('PRODUCTION_DOMAIN', ''),
            os.getenv('API_DOMAIN', '')
        ]


def get_config(config_name: str) -> Config:
    """
    Get configuration by name.

    Args:
        config_name (str): Name of the configuration environment

    Returns:
        Config: Configured settings object
    """
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    return configs.get(config_name, DevelopmentConfig)()


# Create Pydantic-based settings for enhanced type safety and environment variable handling
class Settings(BaseSettings):
    """
    Pydantic-based settings for type safety and environment variable support
    """
    model_config = ConfigDict(
        extra='allow',  # Allow extra fields
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    # Allow conversion of Config instance to Pydantic model
    @classmethod
    def from_config(cls, config: Config):
        """
        Convert a Config instance to a Pydantic Settings instance

        Args:
            config (Config): Original configuration object

        Returns:
            Settings: Pydantic settings instance
        """
        return cls(**{
            k: v for k, v in config.__dict__.items()
            if not k.startswith('_')
        })


# Singleton instances
config = get_config(os.getenv('FLASK_ENV', 'development'))
settings = Settings.from_config(config)