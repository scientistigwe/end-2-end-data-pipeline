# backend/core/app/factory.py

from typing import Dict, Any
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.core.config.config_manager import ConfigurationManager
from backend.data_pipeline.analysis.quality_report_messenger import QualityReportMessenger


def create_application_components() -> Dict[str, Any]:
    """Create and wire up application components with consistent messaging"""
    # Create shared components
    config_manager = ConfigurationManager()
    message_broker = MessageBroker(config_manager)

    # Create staging area
    staging_area = EnhancedStagingArea(message_broker)

    # Create conductor with both dependencies
    conductor = DataConductor(
        message_broker=message_broker,
        config_manager=config_manager
    )

    # Create orchestrator with all dependencies
    orchestrator = DataOrchestrator(
        message_broker=message_broker,
        data_conductor=conductor,
        staging_area=staging_area
    )

    # Create file manager
    file_manager = FileManager(message_broker)

    # Create quality report messenger
    quality_report = QualityReportMessenger(message_broker)

    return {
        'message_broker': message_broker,
        'orchestrator': orchestrator,
        'file_manager': file_manager,
        'staging_area': staging_area,
        'conductor': conductor,
        'quality_report': quality_report,
        'config_manager': config_manager
    }