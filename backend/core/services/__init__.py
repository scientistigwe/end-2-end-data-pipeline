# backend/core/services/__init__.py

"""
Core services module initialization.
This module provides a centralized way to access all service implementations,
handling imports and exposures in a clean and maintainable way.
"""

import logging
from typing import Dict, Any, Type
from abc import ABC

# Import all service base classes and interfaces
#from .base_service import BaseService

# Import service implementations
from .quality.quality_service import QualityService
from .insight.insight_service import InsightService
from .decision.decision_service import DecisionService
from .recommendation.recommendations_service import RecommendationService
from .reports.report_service import ReportService
from .pipeline.pipeline_service import PipelineService
from .monitoring.monitoring_service import MonitoringService
from .auth.auth_service import AuthService
from .settings.settings_service import SettingsService
from .advanced_analytics.advanced_analytics_services import AnalyticsService

logger = logging.getLogger(__name__)

# Import base service class for type hints
class BaseService(ABC):
    """Base class for all services"""

    async def cleanup(self) -> None:
        """Clean up service resources"""
        pass

# Service registry mapping service names to their implementations
SERVICE_REGISTRY: Dict[str, Type[BaseService]] = {
    'quality': QualityService,
    'insight': InsightService,
    'decision': DecisionService,
    'recommendation': RecommendationService,
    'report': ReportService,
    'pipeline': PipelineService,
    'monitoring': MonitoringService,
    'auth': AuthService,
    'settings': SettingsService,
    'analytics': AnalyticsService
}


def get_service_class(service_name: str) -> Type[BaseService]:
    """
    Retrieve a service class by name.

    Args:
        service_name: Name of the service to retrieve

    Returns:
        Service class implementation

    Raises:
        KeyError: If service_name is not found in registry
    """
    if service_name not in SERVICE_REGISTRY:
        raise KeyError(f"Service '{service_name}' not found in registry")
    return SERVICE_REGISTRY[service_name]


def initialize_services(config: Dict[str, Any]) -> Dict[str, BaseService]:
    """
    Initialize all registered services with provided configuration.

    Args:
        config: Dictionary containing service configurations

    Returns:
        Dictionary mapping service names to initialized instances
    """
    initialized_services = {}

    try:
        for service_name, service_class in SERVICE_REGISTRY.items():
            service_config = config.get(f"{service_name}_service_config", {})
            initialized_services[service_name] = service_class(**service_config)
            logger.info(f"Initialized {service_name} service")

    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        # Clean up any services that were initialized
        cleanup_services(initialized_services)
        raise

    return initialized_services


def cleanup_services(services: Dict[str, BaseService]) -> None:
    """
    Clean up initialized services.

    Args:
        services: Dictionary of service instances to clean up
    """
    for service_name, service in reversed(list(services.items())):
        try:
            if hasattr(service, 'cleanup'):
                service.cleanup()
            logger.info(f"Cleaned up {service_name} service")
        except Exception as e:
            logger.error(f"Error cleaning up {service_name} service: {str(e)}")


# Export all service classes for direct imports
__all__ = [
    'BaseService',
    'QualityService',
    'InsightService',
    'DecisionService',
    'RecommendationService',
    'ReportService',
    'PipelineService',
    'MonitoringService',
    'AuthService',
    'SettingsService',
    'AnalyticsService',
    'get_service_class',
    'initialize_services',
    'cleanup_services'
]