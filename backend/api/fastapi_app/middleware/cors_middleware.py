# api/fastapi_app/middleware/cors_middleware.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict


def setup_cors(
        app: FastAPI,
        allowed_origins: List[str],
        allowed_methods: List[str],
        allowed_headers: List[str],
        allow_credentials: bool = True
) -> None:
    """Configure CORS middleware for FastAPI application"""

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=allowed_methods,
        allow_headers=allowed_headers,
        expose_headers=["*"],
        max_age=3600,
    )


def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration from settings"""
    return {
        "allowed_origins": [
            "http://localhost:3000",
            "http://localhost:8000",
            # Add other origins as needed
        ],
        "allowed_methods": ["*"],
        "allowed_headers": ["*"],
        "allow_credentials": True
    }


# Usage in your main app:
"""
from .middleware.cors_middleware import setup_cors, get_cors_config

app = FastAPI()
cors_config = get_cors_config()
setup_cors(app, **cors_config)
"""