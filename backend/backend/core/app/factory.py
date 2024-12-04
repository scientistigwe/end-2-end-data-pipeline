# backend/core/app/factory.py
"""
Application Component Factory Module

This module serves as the central factory for creating and wiring up all core application components.
It manages the initialization and dependency injection of various data source handlers, orchestration
components, and analysis systems within the data pipeline architecture.

Key Components:
- Message Broker: Central communication system
- Data Sources: File, API, Database, S3, and Stream handlers
- Orchestration: Conductor and Orchestrator for pipeline management
- Analysis: Quality and Insight analysis systems
- Staging: Enhanced staging area for data processing
- Configuration: System-wide configuration management

The factory ensures consistent messaging patterns and proper dependency injection across all components,
facilitating a robust and maintainable data pipeline system.
"""

from typing import Dict, Any
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator
from backend.core.config.config_manager import ConfigurationManager
from backend.data_pipeline.analysis.quality_report_messenger import QualityReportMessenger

# Import Data Source Managers
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.api.api_manager import APIManager
from backend.data_pipeline.source.database.db_manager import DBManager
from backend.data_pipeline.source.cloud.s3_manager import S3Manager
from backend.data_pipeline.source.stream.stream_manager import StreamManager


def create_application_components() -> Dict[str, Any]:
    """
    Create and wire up application components with consistent messaging.

    This function serves as the main factory method for initializing all core components
    of the data pipeline system. It ensures proper dependency injection and establishes
    the communication channels between different components.

    Returns:
        Dict[str, Any]: Dictionary containing all initialized components, including:
            - message_broker: Central message broker for component communication
            - orchestrator: Main pipeline orchestrator
            - staging_area: Enhanced staging area for data processing
            - conductor: Data conductor for pipeline flow management
            - config_manager: System configuration manager
            - Data Source Managers:
                - file_manager: For file-based data sources
                - api_manager: For API-based data sources
                - db_manager: For database connections
                - s3_manager: For S3/cloud storage
                - stream_manager: For real-time data streams
            - Analysis Components:
                - quality_report: Quality analysis messenger

    Example:
        components = create_application_components()
        message_broker = components['message_broker']
        file_manager = components['file_manager']
    """
    # Initialize Core Components
    config_manager = ConfigurationManager()
    message_broker = MessageBroker(config_manager)

    # Initialize Processing Components
    staging_area = EnhancedStagingArea(message_broker)
    conductor = DataConductor(
        message_broker=message_broker,
        config_manager=config_manager
    )

    # Initialize Orchestrator
    orchestrator = DataOrchestrator(
        message_broker=message_broker,
        data_conductor=conductor,
        staging_area=staging_area
    )

    # Initialize Data Source Managers
    file_manager = FileManager(message_broker)
    api_manager = APIManager(message_broker)
    db_manager = DBManager(message_broker)
    s3_manager = S3Manager(message_broker)
    stream_manager = StreamManager(message_broker)

    # Initialize Analysis Components
    quality_report = QualityReportMessenger(message_broker)

    # Return all components
    return {
        # Core Components
        'message_broker': message_broker,
        'orchestrator': orchestrator,
        'staging_area': staging_area,
        'conductor': conductor,
        'config_manager': config_manager,

        # Data Source Managers
        'file_manager': file_manager,
        'api_manager': api_manager,
        'db_manager': db_manager,
        's3_manager': s3_manager,
        'stream_manager': stream_manager,

        # Analysis Components
        'quality_report': quality_report
    }


def get_source_manager(source_type: str, components: Dict[str, Any]) -> Any:
    """
    Get the appropriate source manager based on source type.

    Args:
        source_type (str): Type of data source ('file', 'api', 'database', 's3', 'stream')
        components (Dict[str, Any]): Dictionary of application components

    Returns:
        Any: Appropriate source manager instance

    Raises:
        ValueError: If source type is not supported
    """
    source_managers = {
        'file': components.get('file_manager'),
        'api': components.get('api_manager'),
        'database': components.get('db_manager'),
        's3': components.get('s3_manager'),
        'stream': components.get('stream_manager')
    }

    manager = source_managers.get(source_type)
    if not manager:
        raise ValueError(f"Unsupported source type: {source_type}")

    return manager