# api/flask_app/__init__.py

import logging
from flask import Flask
from .app import ApplicationFactory

logger = logging.getLogger(__name__)


def create_app(config_name: str = 'development') -> Flask:
    """
    Application factory function that serves as the main entry point.

    Args:
        config_name (str): Name of configuration to use (development, production, etc.)

    Returns:
        Flask: Configured Flask application instance
    """
    factory = ApplicationFactory()
    return factory.create_app(config_name)


__all__ = ['create_app']