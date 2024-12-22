# database/config.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

class DatabaseConfig:
    def __init__(self, app_config):
        self.SQLALCHEMY_DATABASE_URI = self._get_database_uri(app_config)
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.SQLALCHEMY_POOL_SIZE = 5
        self.SQLALCHEMY_MAX_OVERFLOW = 10
        self.SQLALCHEMY_POOL_TIMEOUT = 30

    def _get_database_uri(self, config):
        # Use getattr() with a default value to safely check TESTING
        if getattr(config, 'TESTING', False):
            return 'postgresql://postgres:password@localhost:5432/pipeline_test'
        
        return self._construct_db_uri(
            username=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'password'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'pipeline_db')
        )
    def _construct_db_uri(self, username, password, host, port, database):
        return f'postgresql://{username}:{password}@{host}:{port}/{database}'

Base = declarative_base()

def init_db(app):
    db_config = DatabaseConfig(app.config)
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': db_config.SQLALCHEMY_DATABASE_URI,
        'SQLALCHEMY_TRACK_MODIFICATIONS': db_config.SQLALCHEMY_TRACK_MODIFICATIONS
    })

    engine = create_engine(
        db_config.SQLALCHEMY_DATABASE_URI,
        pool_size=db_config.SQLALCHEMY_POOL_SIZE,
        max_overflow=db_config.SQLALCHEMY_MAX_OVERFLOW,
        pool_timeout=db_config.SQLALCHEMY_POOL_TIMEOUT
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    return engine, SessionLocal