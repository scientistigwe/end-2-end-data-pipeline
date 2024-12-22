# backend\backend\flask_api\config.py
from pathlib import Path
import os
from typing import Dict, Set, Union, List
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()

class Config:
    """Base configuration settings for the application."""
    
    # Security settings
    SECRET_KEY: str = os.getenv('SECRET_KEY') or os.urandom(32).hex()
    DEBUG: bool = False
    TESTING: bool = False
    
    # Path configurations
    BASE_DIR: Path = Path(__file__).resolve().parent
    UPLOAD_FOLDER: Path = BASE_DIR / 'uploads'
    LOG_FOLDER: Path = BASE_DIR / 'logs'
    
    # File handling configurations
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS: Set[str] = {'csv', 'json', 'xlsx', 'parquet'}
    
    # Database configurations
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_POOL_SIZE: int = 5
    SQLALCHEMY_MAX_OVERFLOW: int = 10
    SQLALCHEMY_POOL_TIMEOUT: int = 30
    SQLALCHEMY_POOL_RECYCLE: int = 1800  # Recycle connections after 30 minutes
    
    # Common CORS settings
    COMMON_HEADERS: List[str] = [
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Credentials",
        "X-CSRF-Token"
    ]

    COMMON_METHODS: List[str] = [
        "GET", 
        "POST", 
        "PUT", 
        "DELETE", 
        "OPTIONS", 
        "PATCH"
    ]
    
    # CORS Configuration
    CORS_SETTINGS: Dict[str, Union[List[str], str, bool, int]] = {
        "origins": [
            "http://localhost:5173",  # Vite default dev server
            "http://127.0.0.1:5173"
        ],
        "methods": COMMON_METHODS,
        "allow_headers": COMMON_HEADERS,
        "expose_headers": [
            "Content-Type",
            "X-Total-Count",
            "Authorization",
            "X-Request-ID"
        ],
        "supports_credentials": True,
        "max_age": 3600,  # 1 hour
        "send_wildcard": False,
        "automatic_options": True,
        "vary_header": True
    }

    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv('JWT_SECRET_KEY') or os.urandom(32).hex()
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES: int = 2592000  # 30 days
    JWT_ERROR_MESSAGE_KEY: str = "message"

    @classmethod
    def validate_config(cls) -> None:
        """Validate critical configuration settings."""
        required_dirs = [cls.UPLOAD_FOLDER, cls.LOG_FOLDER]
        
        # Validate secret keys
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set")
        if not cls.JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY must be set")
            
        # Create required directories
        for directory in required_dirs:
            if not directory.exists():
                directory.mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(Config):
    """Development environment specific configurations."""
    
    DEBUG: bool = True
    DEVELOPMENT: bool = True
    
    # Development Database URI
    SQLALCHEMY_DATABASE_URI: str = 'postgresql://{user}:{password}@{host}:{port}/{database}'.format(
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'enterprise_pipeline_db')
    )
    
    # Extended CORS for development
    CORS_SETTINGS = {
        **Config.CORS_SETTINGS,
        "origins": [
            "http://localhost:5173",  # Vite default
            "http://127.0.0.1:5173",
            "http://localhost:3000",  # React default
            "http://localhost:3001",  # Alternative ports
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001"
        ],
        "supports_credentials": True,
        "send_wildcard": False,
        "max_age": 3600
    }
    
    def __init__(self):
        super().__init__()
        self.validate_config()
        print("Running in Development mode")

class TestingConfig(Config):
    """Testing environment specific configurations."""
    
    DEBUG: bool = True
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = 'postgresql://postgres:password@localhost:5432/pipeline_test'
    
    # Simplified CORS for testing
    CORS_SETTINGS = {
        **Config.CORS_SETTINGS,
        "origins": ["*"],  # Allow all origins in testing
        "supports_credentials": False,  # Disable credentials in testing
        "send_wildcard": True,
        "max_age": 86400  # 24 hours
    }
    
    def __init__(self):
        super().__init__()
        self.validate_config()
        print("Running in Testing mode")

class ProductionConfig(Config):
    """Production environment specific configurations."""
    
    # Production Database URI
    SQLALCHEMY_DATABASE_URI: str = 'postgresql://{user}:{password}@{host}:{port}/{database}'.format(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME')
    )
    
    # Strict CORS for production
    CORS_SETTINGS = {
        **Config.CORS_SETTINGS,
        "origins": [
            os.getenv('PRODUCTION_DOMAIN', 'https://yourdomain.com'),
            os.getenv('API_DOMAIN', 'https://api.yourdomain.com')
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Restricted methods
        "supports_credentials": True,
        "send_wildcard": False,
        "max_age": 7200,  # 2 hours
        "vary_header": True
    }
    
    def __init__(self):
        super().__init__()
        self.validate_config()
        self._validate_production_settings()
    
    def _validate_production_settings(self):
        """Additional validation for production environment."""
        required_env_vars = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_NAME', 
                           'PRODUCTION_DOMAIN', 'JWT_SECRET_KEY']
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        if any('localhost' in origin for origin in self.CORS_SETTINGS['origins']):
            raise ValueError("Production config cannot use localhost origins")

def get_config(env: str = 'development') -> Config:
    """
    Retrieve configuration based on environment.
    
    Args:
        env: Environment mode ('development', 'testing', or 'production')
    
    Returns:
        Config: Configuration class instance for the specified environment
    
    Raises:
        ValueError: If an invalid environment is specified
    """
    config_map = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig
    }
    
    config_class = config_map.get(env.lower())
    if not config_class:
        raise ValueError(f"Invalid environment: {env}. Must be one of {list(config_map.keys())}")
    
    return config_class()