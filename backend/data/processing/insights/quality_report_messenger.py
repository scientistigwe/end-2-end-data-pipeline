# backend/data_pipeline/insight/quality_report_messenger.py

import logging
import pandas as pd
from typing import Dict, Any

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ProcessingStatus,
    ModuleIdentifier
)
from backend.core.registry.component_registry import ComponentRegistry
from backend.data_pipeline.analysis.quality_report_generator import QualityReportGenerator

logger = logging.getLogger(__name__)


class QualityReportMessenger:
    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.registry = ComponentRegistry()

        # Initialize module ID
        self.module_id = ModuleIdentifier(
            "DataQualityReport",
            "generate_report",
            self.registry.get_component_uuid("DataQualityReport")
        )

        # Register and subscribe
        self._initialize_messaging()

    def _initialize_messaging(self):
        try:
            self.message_broker.register_module(self.module_id)
            self.message_broker.subscribe_to_module(
                self.module_id.get_tag(),
                self._handle_report_request
            )
            logger.info("DataQualityReport messaging initialized")
        except Exception as e:
            logger.error(f"Error initializing messaging: {str(e)}")
            raise

    def _handle_report_request(self, message: ProcessingMessage):
        try:
            data = message.content.get('data')
            if not data:
                raise ValueError("No data provided in message")

            # Convert data to DataFrame
            df = pd.DataFrame(data if isinstance(data, list) else data)

            # Generate report
            report_generator = QualityReportGenerator(df)
            report_results = report_generator.generate_reports()

            # Send results back
            self._send_response(message, report_results)

        except Exception as e:
            logger.error(f"Error generating quality report: {str(e)}")
            self._publish_error_message(message, str(e))

    def _send_response(self, original_message: ProcessingMessage, results: dict):
        response_message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=original_message.source_identifier,
            message_type=MessageType.STATUS_UPDATE,
            content={
                'pipeline_id': original_message.content.get('pipeline_id'),
                'staging_id': original_message.content.get('staging_id'),
                'report_results': results,
                'status': ProcessingStatus.COMPLETED
            }
        )
        self.message_broker.publish(response_message)

    def _publish_error_message(self, original_message: ProcessingMessage, error_details: str):
        error_message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=original_message.source_identifier,
            message_type=MessageType.ERROR,
            content={
                'pipeline_id': original_message.content.get('pipeline_id'),
                'error': error_details
            }
        )
        self.message_broker.publish(error_message)