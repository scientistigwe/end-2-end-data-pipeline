# backend/core/services/__init__.py

"""
Core services module initialization.
This module provides a centralized way to access all service implementations,
handling imports and exposures in a clean and maintainable way.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Optional
from abc import ABC


# Import base service class for type hints
class BaseService(ABC):
    """Base class for all services"""

    async def cleanup(self) -> None:
        """Clean up service resources"""
        pass


# Create a type variable for service classes
ServiceType = TypeVar('ServiceType', bound=BaseService)

# Import data source services from their correct locations
from ..source.file.file_service import FileService
from ..source.database.db_service import DatabaseService
from ..source.api.api_service import APIService
from ..source.cloud.cloud_service import S3Service
from ..source.stream.stream_service import StreamService

logger = logging.getLogger(__name__)

# Service registry with proper type hints
SERVICE_REGISTRY: Dict[str, Type[BaseService]] = {
    'file': FileService,
    'database': DatabaseService,
    'api': APIService,
    's3': S3Service,
    'stream': StreamService,
}


def get_service_class(service_name: str) -> Type[BaseService]:
    """
    Retrieve a service class by name.

    Args:
        service_name: Name of the service to retrieve

    Returns:
        Service class implementation that inherits from BaseService

    Raises:
        KeyError: If service_name is not found in registry
        ValueError: If service class doesn't implement required interface
    """
    if service_name not in SERVICE_REGISTRY:
        raise KeyError(
            f"Service '{service_name}' not found in registry. Available services: {', '.join(SERVICE_REGISTRY.keys())}")

    service_class = SERVICE_REGISTRY[service_name]
    if not issubclass(service_class, BaseService):
        raise ValueError(f"Service class {service_class.__name__} must implement BaseService interface")

    return service_class


def initialize_services(
        config: Dict[str, Any],
        required_services: Optional[list[str]] = None
) -> Dict[str, BaseService]:
    """
    Initialize all registered services with provided configuration.

    Args:
        config: Dictionary containing service configurations
        required_services: Optional list of service names that must be initialized

    Returns:
        Dictionary mapping service names to initialized service instances

    Raises:
        KeyError: If a required service is not found in registry
        ValueError: If service initialization fails
        Exception: For other initialization errors
    """
    initialized_services: Dict[str, BaseService] = {}
    services_to_initialize = required_services or SERVICE_REGISTRY.keys()

    try:
        for service_name in services_to_initialize:
            if service_name not in SERVICE_REGISTRY:
                raise KeyError(f"Required service '{service_name}' not found in registry")

            service_class = SERVICE_REGISTRY[service_name]
            service_config = config.get(f"{service_name}_service_config", {})

            try:
                service_instance = service_class(**service_config)
                initialized_services[service_name] = service_instance
                logger.info(f"Successfully initialized {service_name} service")
            except Exception as e:
                raise ValueError(f"Failed to initialize {service_name} service: {str(e)}")

        return initialized_services

    except Exception as e:
        logger.error(f"Service initialization error: {str(e)}")
        cleanup_services(initialized_services)
        raise


async def cleanup_services(services: Dict[str, BaseService]) -> None:
    """
    Clean up initialized services in reverse order of initialization.

    Args:
        services: Dictionary mapping service names to service instances

    Note:
        This function attempts to clean up all services even if some cleanups fail.
        Any cleanup errors are logged but don't prevent other services from being cleaned up.
    """
    cleanup_errors = []

    for service_name, service in reversed(list(services.items())):
        try:
            await service.cleanup()
            logger.info(f"Successfully cleaned up {service_name} service")
        except Exception as e:
            error_msg = f"Error cleaning up {service_name} service: {str(e)}"
            logger.error(error_msg)
            cleanup_errors.append(error_msg)

    if cleanup_errors:
        logger.error(f"Encountered {len(cleanup_errors)} errors during service cleanup")


# Export all service classes and utility functions
__all__ = [
    'BaseService',
    'FileService',
    'DatabaseService',
    'APIService',
    'S3Service',
    'StreamService',
    'get_service_class',
    'initialize_services',
    'cleanup_services'
]