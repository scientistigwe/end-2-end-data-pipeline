# config/app_config.py

from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import logging
from functools import lru_cache

from pydantic import (
    BaseModel,
    Field,
    SecretStr,
    field_validator,
    ConfigDict
)
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()

logger = logging.getLogger(__name__)


class JWTSettings(BaseModel):
    """JWT configuration settings."""
    secret_key: SecretStr = Field(..., description="JWT secret key")
    private_key: SecretStr = Field(..., description="JWT private key")
    public_key: str = Field(..., description="JWT public key")
    access_token_expires: int = Field(
        default=3600,
        description="JWT access token expiration in seconds"
    )
    refresh_token_expires: int = Field(
        default=2592000,
        description="JWT refresh token expiration in seconds"
    )

    def get_secret_key(self) -> str:
        """Get JWT secret key value."""
        return self.secret_key.get_secret_value()


class CORSSettings(BaseModel):
    """CORS configuration settings."""
    allow_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174"
        ],
        description="Allowed CORS origins"
    )
    allow_credentials: bool = Field(default=True)
    allow_methods: List[str] = Field(default_factory=lambda: ["*"])
    allow_headers: List[str] = Field(default_factory=lambda: ["*"])
    expose_headers: List[str] = Field(default_factory=lambda: ["Set-Cookie"])
    max_age: int = Field(default=3600)

    def get_settings(self) -> Dict[str, Any]:
        """Get CORS settings as a dictionary."""
        return {
            'allow_origins': self.allow_origins,
            'allow_credentials': self.allow_credentials,
            'allow_methods': self.allow_methods,
            'allow_headers': self.allow_headers,
            'expose_headers': self.expose_headers,
            'max_age': self.max_age
        }


class SecurityHeaders(BaseModel):
    """Security headers configuration."""
    x_content_type_options: str = Field(
        default="nosniff",
        alias="X-Content-Type-Options"
    )
    x_frame_options: str = Field(
        default="SAMEORIGIN",
        alias="X-Frame-Options"
    )
    x_xss_protection: str = Field(
        default="1; mode=block",
        alias="X-XSS-Protection"
    )
    strict_transport_security: str = Field(
        default="max-age=31536000; includeSubDomains",
        alias="Strict-Transport-Security"
    )

    model_config = ConfigDict(
        populate_by_name=True
    )

    def get_headers(self) -> Dict[str, str]:
        """Get security headers as a dictionary."""
        return {
            'X-Content-Type-Options': self.x_content_type_options,
            'X-Frame-Options': self.x_frame_options,
            'X-XSS-Protection': self.x_xss_protection,
            'Strict-Transport-Security': self.strict_transport_security
        }


class Config:
    """Base configuration class for FastAPI application."""

    def __init__(self):
        """Initialize application configuration."""
        try:
            # Core paths
            self.BASE_DIR = Path(__file__).parent.parent
            self._setup_folders()

            # Application environment
            self.ENV = os.getenv('ENVIRONMENT', 'development')
            self.DEBUG = self.ENV == 'development'
            self.TESTING = False
            self.SECRET_KEY = os.getenv('SECRET_KEY')

            # Logging Configuration
            self.LOG_FILENAME = os.getenv('LOG_FILENAME', 'app.log')
            self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
            self.LOG_FORMAT = os.getenv(
                'LOG_FORMAT',
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            self.LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
            self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

            # API Settings
            self.API_V1_PREFIX = "/api/v1"
            self.PROJECT_NAME = "Analytix Flow API"
            self.API_URL = os.getenv('API_URL', 'http://localhost:8000')

            # JWT Configuration
            self.jwt = JWTSettings(
                secret_key=os.getenv('JWT_SECRET_KEY', 'default_secret'),
                private_key=os.getenv('JWT_PRIVATE_KEY', 'default_private_key'),
                public_key=os.getenv('JWT_PUBLIC_KEY', 'default_public_key'),
                access_token_expires=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', '3600')),
                refresh_token_expires=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', '2592000'))
            )

            # CORS Settings
            self.cors = CORSSettings(
                allow_origins=[
                    origin.strip()
                    for origin in os.getenv(
                        'CORS_ORIGINS',
                        'http://localhost:3000,http://localhost:5173'
                    ).split(',')
                    if origin.strip()
                ]
            )

            # Security Headers
            self.security_headers = SecurityHeaders()

            # Additional Settings
            self.ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
            self.ENABLE_SSL = os.getenv('ENABLE_SSL', 'False').lower() == 'true'
            self.SSL_CERT_PATH = os.getenv('SSL_CERT_PATH')

            logger.info(f"Configuration loaded for environment: {self.ENV}")

        except Exception as e:
            logger.error(f"Failed to initialize configuration: {str(e)}")
            raise

    def _setup_folders(self) -> None:
        """Setup required application folders."""
        folders = {
            'UPLOAD_FOLDER': 'uploads',
            'LOG_FOLDER': 'logs',
            'STAGING_FOLDER': 'staging',
            'TEMP_FOLDER': 'temp',
            'CACHE_FOLDER': 'cache'
        }

        for attr, folder_name in folders.items():
            folder_path = self.BASE_DIR / folder_name
            folder_path.mkdir(parents=True, exist_ok=True)
            setattr(self, attr, folder_path)

    @property
    def cors_settings(self) -> Dict[str, Any]:
        """Get CORS settings dictionary."""
        return self.cors.get_settings()

    @property
    def security_header_settings(self) -> Dict[str, str]:
        """Get security headers dictionary."""
        return self.security_headers.get_headers()

    def get_jwt_secret(self) -> str:
        """Get JWT secret key."""
        return self.jwt.get_secret_key()

    def validate_db_config(self) -> None:
        """Validate database configuration."""
        required_attrs = [
            'SQLALCHEMY_DATABASE_URI',
            'SQLALCHEMY_POOL_SIZE',
            'SQLALCHEMY_MAX_OVERFLOW',
            'SQLALCHEMY_POOL_TIMEOUT',
            'SQLALCHEMY_ISOLATION_LEVEL'
        ]

        missing_attrs = [attr for attr in required_attrs if not hasattr(self, attr)]
        if missing_attrs:
            raise ValueError(f"Missing required database attributes: {', '.join(missing_attrs)}")


class DevelopmentConfig(Config):
    """Development configuration."""

    def __init__(self):
        super().__init__()
        # Debug settings
        self.DEBUG = True

        # Database connection settings
        db_user = os.getenv('DB_USER', 'postgres')
        db_password = os.getenv('DB_PASSWORD', 'mercy')
        db_host = os.getenv('DB_HOST', 'localhost')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME', 'enterprise_pipeline_db')

        # Construct database URI
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )

        # SQLAlchemy settings
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', '5'))
        self.SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', '10'))
        self.SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('SQLALCHEMY_POOL_TIMEOUT', '30'))
        self.SQLALCHEMY_POOL_RECYCLE = int(os.getenv('SQLALCHEMY_POOL_RECYCLE', '1800'))
        self.SQLALCHEMY_POOL_PRE_PING = True
        self.SQLALCHEMY_ECHO = True
        self.SQLALCHEMY_ISOLATION_LEVEL = "READ_COMMITTED"
        self.SQLALCHEMY_POOL_USE_LIFO = True


class ProductionConfig(Config):
    """Production configuration."""

    def __init__(self):
        super().__init__()
        # Debug settings
        self.DEBUG = False

        # Database connection settings
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT', '5432')
        db_name = os.getenv('DB_NAME')

        # Validate required database settings
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError(
                "Missing required database configuration. Please check environment variables."
            )

        # Construct database URI
        self.SQLALCHEMY_DATABASE_URI = (
            f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )

        # SQLAlchemy settings - more conservative for production
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_POOL_SIZE = int(os.getenv('SQLALCHEMY_POOL_SIZE', '10'))
        self.SQLALCHEMY_MAX_OVERFLOW = int(os.getenv('SQLALCHEMY_MAX_OVERFLOW', '20'))
        self.SQLALCHEMY_POOL_TIMEOUT = int(os.getenv('SQLALCHEMY_POOL_TIMEOUT', '30'))
        self.SQLALCHEMY_POOL_RECYCLE = int(os.getenv('SQLALCHEMY_POOL_RECYCLE', '1800'))
        self.SQLALCHEMY_POOL_PRE_PING = True
        self.SQLALCHEMY_ECHO = False
        self.SQLALCHEMY_ISOLATION_LEVEL = "READ_COMMITTED"
        self.SQLALCHEMY_POOL_USE_LIFO = True


@lru_cache()
def get_config(config_name: str = os.getenv('ENVIRONMENT', 'development')) -> Config:
    """Get configuration instance by name."""
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }

    try:
        config_class = configs.get(config_name, DevelopmentConfig)
        config = config_class()
        config.validate_db_config()  # Add validation
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration '{config_name}': {str(e)}")
        raise ValueError(f"Configuration initialization failed: {str(e)}")

# Create configuration instance
app_config = get_config()