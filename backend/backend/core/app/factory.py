# backend/core/app/factory.py

from typing import Dict, Any
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataOrchestrator
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.core.config.config_manager import ConfigurationManager


def create_application_components() -> Dict[str, Any]:
    """Create and wire up application components with consistent messaging"""
    # Create shared components
    config_manager = ConfigurationManager()
    message_broker = MessageBroker(config_manager)

    # Create and initialize components
    orchestrator = DataOrchestrator(message_broker)
    file_manager = FileManager(message_broker)

    return {
        'message_broker': message_broker,
        'orchestrator': orchestrator,
        'file_manager': file_manager
    }