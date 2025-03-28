import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config, create_async_engine

from alembic import context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your models
from db.models.core.base import BaseModel
from db.models.auth.user import User
from db.models.data.sources import DataSource
from db.models.data.pipeline import Pipeline
from db.models.staging.base import BaseStagedOutput
from db.models.staging.processing import (
    StagedAnalyticsOutput,
    StagedInsightOutput,
    StagedQualityOutput,
    StagedMonitoringOutput,
    StagedRecommendationOutput
)
from db.models.staging.reporting import (
    StagedReportOutput,
    StagedMetricsOutput,
    StagedComplianceReport
)

# Add imports for other key models in your project
from db.models.auth.session import UserSession
from db.models.auth.team import Team, TeamMember

# Load the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use BaseModel's metadata to capture all model metadata
target_metadata = BaseModel.metadata

def get_url():
    return f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_async_engine(get_url())

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()