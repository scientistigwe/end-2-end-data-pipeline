# api/fastapi_app/middleware/cors.py

from typing import List, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI, cors_config: Dict[str, Any]) -> None:
    """Configure CORS for the FastAPI application

    Args:
        app: FastAPI application instance
        cors_config: CORS configuration dictionary
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_config.get('allowed_origins', ["*"]),
        allow_credentials=cors_config.get('allow_credentials', True),
        allow_methods=cors_config.get('allowed_methods', ["*"]),
        allow_headers=cors_config.get('allowed_headers', ["*"]),
        expose_headers=cors_config.get('expose_headers', []),
        max_age=cors_config.get('max_age', 3600),
    )


def get_cors_config() -> Dict[str, Any]:
    """Get default CORS configuration

    Returns:
        Dict with default CORS settings
    """
    return {
        "allowed_origins": [
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:5174",  # Add your frontend URL
            "http://127.0.0.1:5174"   # Also include the IP version
        ],
        "allowed_methods": ["*"],
        "allowed_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3600,
        "expose_headers": []
    }