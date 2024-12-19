from pathlib import Path
import os
from typing import Dict, Set, Union
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
    
    # File handling configurations
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    ALLOWED_EXTENSIONS: Set[str] = {'csv', 'json', 'xlsx', 'parquet'}
    
    # CORS Configuration
    CORS_SETTINGS: Dict[str, Union[list, str]] = {
        "origins": [
            "http://localhost:3000",
            "http://localhost:3001",
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

    @classmethod
    def validate_config(cls) -> None:
        """Validate critical configuration settings."""
        if not cls.SECRET_KEY:
            raise ValueError("SECRET_KEY must be set")
            
        if not cls.UPLOAD_FOLDER.exists():
            cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

class DevelopmentConfig(Config):
    """Development environment specific configurations."""
    
    DEBUG: bool = True
    DEVELOPMENT: bool = True
    
    def __init__(self):
        super().__init__()
        self.validate_config()
        print("Running in Development mode")

class ProductionConfig(Config):
    """Production environment specific configurations."""
    
    CORS_SETTINGS: Dict[str, Union[list, str]] = {
        "origins": [os.getenv('PRODUCTION_DOMAIN', 'https://yourdomain.com')],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
    
    def __init__(self):
        super().__init__()
        self.validate_config()
        
        # Additional production checks
        if 'localhost' in str(self.CORS_SETTINGS['origins']):
            raise ValueError("Production config cannot use localhost origins")

def get_config(env: str = 'development') -> Config:
    """
    Retrieve configuration based on environment.
    
    Args:
        env: Environment mode ('development' or 'production')
    
    Returns:
        Config: Configuration class instance for the specified environment
    
    Raises:
        ValueError: If an invalid environment is specified
    """
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig
    }
    
    config_class = config_map.get(env.lower())
    if not config_class:
        raise ValueError(f"Invalid environment: {env}. Must be one of {list(config_map.keys())}")
    
    return config_class()