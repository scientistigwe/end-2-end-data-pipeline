# api/fastapi_app/middleware/cors.py

from typing import Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.app_config import app_config  # Import the single source of truth


def setup_cors(app: FastAPI, cors_config: Dict[str, Any] = None) -> None:
    """Configure CORS for the FastAPI application

    Args:
        app: FastAPI application instance
        cors_config: Optional override for CORS configuration
    """
    # If no config is provided, use the app_config
    if cors_config is None:
        cors_config = app_config.cors_settings

    # Ensure these are included for cookie handling
    cors_config.setdefault('expose_headers', ['Set-Cookie'])

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get('allow_origins', ["*"]),
        allow_credentials=cors_config.get('allow_credentials', True),
        allow_methods=cors_config.get('allow_methods', ["*"]),
        allow_headers=cors_config.get('allow_headers', ["*"]),
        expose_headers=cors_config.get('expose_headers', ['Set-Cookie']),
        max_age=cors_config.get('max_age', 3600),
    )


def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration from app_config

    Returns:
        Dict with CORS settings from the central configuration
    """
    # Just return the settings from app_config to ensure consistency
    return app_config.cors_settings