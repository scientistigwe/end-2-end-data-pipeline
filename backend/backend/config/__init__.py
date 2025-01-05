# backend/config/__init__.py
import os
from pathlib import Path
from datetime import timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import logging

from dotenv import load_dotenv
load_dotenv()

logger = logging.Logger(__name__)


# Base Configuration
class BaseConfig:
    """Base configuration settings for all environments"""
    # Core Settings
    BASE_DIR = Path(__file__).parent.parent
    print('Base directory: ', BASE_DIR)
    SECRET_KEY = os.getenv('SECRET_KEY')
    print('Secret Key: ', SECRET_KEY)
    DEBUG = False
    TESTING = False

    # Database Settings
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'enterprise_pipeline_db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))
    SQLALCHEMY_ECHO = False

    # JWT Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_PRIVATE_KEY = os.getenv('JWT_PRIVATE_KEY')
    JWT_PUBLIC_KEY = os.getenv('JWT_PUBLIC_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 2592000)))
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_TOKEN_LOCATION = ['cookies', 'headers']

    # Validate required JWT keys
    if not all([JWT_SECRET_KEY, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, SECRET_KEY]):
        raise ValueError(
            "Missing required JWT keys in environment variables. "
            "Please set JWT_SECRET_KEY, JWT_PRIVATE_KEY, and JWT_PUBLIC_KEY"
        )
    
    # API Settings
    API_TITLE = "Data Pipeline API"
    API_VERSION = "v1"
    API_DESCRIPTION = "Enterprise Data Pipeline and Analysis System API"
    OPENAPI_VERSION = "3.0.2"
    OPENAPI_URL_PREFIX = "/"
    OPENAPI_SWAGGER_UI_PATH = "/swagger-ui"
    OPENAPI_SWAGGER_UI_URL = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Service Routes
    SERVICES = {
        'auth': '/auth',
        'pipeline': '/pipelines',
        'data-sources': '/data-sources',
        'analysis': '/analysis',
        'monitoring': '/monitoring',
        'reports': '/reports',
        'recommendations': '/recommendations',
        'decisions': '/decisions',
        'settings': '/settings'
    }

    # Logging Configuration
    LOG_FOLDER = BASE_DIR / 'logs'
    LOG_FILENAME = 'app.log'
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    # File Upload Settings
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {
        'csv', 'json', 'xlsx', 'parquet',
        'xls', 'txt', 'pdf', 'doc', 'docx'
    }

    # CORS Settings
    CORS_SETTINGS = {
        "origins": [
            "http://localhost:5173",    # Vite default
            "http://localhost:3000",    # React default
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Service",              
            "X-Decision-Context",     
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Headers"
        ],
        "expose_headers": ["Content-Range", "X-Total-Count"],
        "supports_credentials": True
    }

class DevelopmentConfig(BaseConfig):
    """Development environment specific configuration"""
    DEBUG = True
    DEVELOPMENT = True
    JWT_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = True
    LOG_LEVEL = 'DEBUG'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'

class TestingConfig(BaseConfig):
    """Testing environment specific configuration"""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = f"postgresql://{BaseConfig.DB_USER}:{BaseConfig.DB_PASSWORD}@{BaseConfig.DB_HOST}:{BaseConfig.DB_PORT}/test_{BaseConfig.DB_NAME}"
    JWT_COOKIE_SECURE = False
    SQLALCHEMY_ECHO = False
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(BaseConfig):
    """Production environment specific configuration"""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    LOG_LEVEL = 'WARNING'
    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
    CORS_SETTINGS = {
        "origins": [os.getenv('FRONTEND_URL', 'https://yourdomain.com')],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": [
            "Content-Type",
            "Authorization",
            "X-Service",
            "X-Decision-Context"
        ],
        "supports_credentials": True
    }

def get_config(env=os.getenv('FLASK_ENV', 'development')):
    """
    Factory function to get configuration class based on environment.
    Args:
        env (str): Environment name (development, testing, production)
    Returns:
        Config: Configuration class for the specified environment
    """
    configs = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig
    }
    return configs.get(env, DevelopmentConfig)

# Database initialization function
def init_db(app):
    """Initialize database with application configuration
    Args:
        app: Flask application instance
    Returns:
        tuple: (SQLAlchemy engine, SessionLocal class)
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(
        app.config['SQLALCHEMY_DATABASE_URI'],
        pool_size=app.config['SQLALCHEMY_POOL_SIZE'],
        max_overflow=app.config['SQLALCHEMY_MAX_OVERFLOW'],
        pool_timeout=app.config['SQLALCHEMY_POOL_TIMEOUT'],
        echo=app.config['SQLALCHEMY_ECHO']
    )
    
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    return engine, SessionLocal