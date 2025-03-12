# api/__init__.py
import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .app import ApplicationFactory

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan_context(app: FastAPI, factory: ApplicationFactory) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for the FastAPI application.
    Handles startup and shutdown events.
    """
    try:
        # Initialize async resources
        await factory._init_async_resources()
        logger.info("Application startup complete")
        yield
    finally:
        # Cleanup on shutdown
        await factory._cleanup_async_resources()
        logger.info("Application shutdown complete")

async def create_app(config_name: str = 'development') -> FastAPI:
    """
    Asynchronous application factory function.

    Args:
        config_name: Configuration environment to use

    Returns:
        FastAPI: Configured application instance
    """
    try:
        # Create application factory
        factory = ApplicationFactory()

        # Create FastAPI app with lifespan management
        app = FastAPI(
            title="Analytix Flow API",
            description="End-to-end Analytix Flow API service",
            version="1.0.0",
            lifespan=lambda app: lifespan_context(app, factory)
        )

        # Configure the application
        await factory.configure(app, config_name)

        # Store factory reference
        app.state.factory = factory

        logger.info(f"Application created successfully in {config_name} environment")
        return app

    except Exception as e:
        logger.error("Failed to create application: %s", str(e), exc_info=True)
        raise


# Add new helper function for managing dependencies
def get_factory(app: FastAPI) -> ApplicationFactory:
    """
    Helper function to get the ApplicationFactory instance.
    Can be used as a FastAPI dependency.
    """
    return app.state.factory

# Type hints for better IDE support
Factory = ApplicationFactory

__all__ = ['create_app', 'get_factory', 'Factory']