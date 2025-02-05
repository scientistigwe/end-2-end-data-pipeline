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
        self.SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', 5))
        self.SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', 10))
        self.SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('SQLALCHEMY_POOL_TIMEOUT', 30))
        self.SQLALCHEMY_ISOLATION_LEVEL = os.getenv('SQLALCHEMY_ISOLATION_LEVEL', 'READ_COMMITTED')

        # Logging configuration
        self.LOG_FILENAME = 'app.log'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

        # Security configuration
        # JWT Settings - Consolidated and Enhanced
        self.JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
        self.JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))  # 1 hour
        self.JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days

        # JWT Cookie Configuration
        self.JWT_TOKEN_LOCATION = ['cookies']
        self.JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'  # Must match exactly
        self.JWT_REFRESH_COOKIE_NAME = 'refresh_token_cookie'  # Must match exactly
        self.JWT_ACCESS_COOKIE_PATH = '/'
        self.JWT_REFRESH_COOKIE_PATH = '/api/v1/auth/refresh'
        self.JWT_COOKIE_CSRF_PROTECT = False  # Set to True in production
        self.JWT_COOKIE_SECURE = self.ENV != 'development'  # True in production
        self.JWT_COOKIE_SAMESITE = 'Lax' if self.ENV == 'development' else 'Strict'

        # Enhanced CORS Settings
        self.CORS_SETTINGS = {
            'origins': [
                'http://localhost:3000',
                'http://localhost:5000',
                'http://localhost:5173',
                os.getenv('FRONTEND_URL', ''),  # Add your frontend URL
                os.getenv('PRODUCTION_DOMAIN', '')
            ],
            'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            'allow_headers': [
                'Content-Type',
                'Authorization',
                'X-CSRF-TOKEN',  # Add CSRF token header
                'X-Requested-With'
            ],
            'expose_headers': [
                'Content-Type',
                'Authorization',
                'Set-Cookie'  # Important for cookie handling
            ],
            'supports_credentials': True,
            'max_age': 600  # Cache preflight requests
        }

        # Additional Security Headers
        self.SECURITY_HEADERS = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block'
        }

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
        self.CORS_SETTINGS['origins'] = [os.getenv('PRODUCTION_DOMAIN')]


def get_config(config_name: str) -> Config:
    """Get configuration by name."""
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    return configs.get(config_name, DevelopmentConfig)()