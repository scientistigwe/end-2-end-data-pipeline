
# backend\backend\data_pipeline\source\api\api_service.py
from datetime import datetime
from typing import Dict, Any
import logging
from .api_manager import APIManager
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator

logger = logging.getLogger(__name__)


class APIService:
    """Service layer for managing API operations"""

    def __init__(self, message_broker=None, orchestrator=None):
        """Initialize APIService with dependency injection"""
        self.message_broker = message_broker or MessageBroker()
        self.api_manager = APIManager(self.message_broker)
        self.orchestrator = orchestrator
        logger.info("APIService initialized with MessageBroker")

    def _get_orchestrator(self):
        """Get or create orchestrator instance"""
        if not self.orchestrator:
            data_conductor = DataConductor(self.message_broker)
            staging_area = EnhancedStagingArea(self.message_broker)

            self.orchestrator = DataOrchestrator(
                message_broker=self.message_broker,
                data_conductor=data_conductor,
                staging_area=staging_area
            )
            logger.info("Created new orchestrator instance")

        return self.orchestrator

    def _create_pipeline_entry(self, endpoint: str, request_result: Dict) -> str:
        """Create a pipeline entry for tracking"""
        if not hasattr(self, 'pipeline_service'):
            from backend.data_pipeline.pipeline_service import PipelineService
            self.pipeline_service = PipelineService(
                message_broker=self.message_broker,
                orchestrator=self._get_orchestrator()
            )

        config = {
            'endpoint': endpoint,
            'source_type': 'api',
            'metadata': request_result.get('metadata', {}),
            'start_time': datetime.now().isoformat()
        }

        pipeline_id = self.pipeline_service.start_pipeline(config)
        logger.info(f"Created pipeline {pipeline_id} for API endpoint {endpoint}")
        return pipeline_id

    def process_api_request(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Handle API request processing"""
        endpoint = config.get('endpoint', 'unknown')
        logger.info(f"Processing API request for endpoint: {endpoint}")

        try:
            result = self.api_manager.process_api_request(config)

            if result.get('status') == 'success':
                pipeline_id = self._create_pipeline_entry(endpoint, result)
                result['pipeline_id'] = pipeline_id

            logger.info(f"API request result for {endpoint}: {result.get('status')}")
            return result

        except Exception as e:
            logger.error(f"Unexpected error during API request for {endpoint}", exc_info=True)
            return {
                'status': 'error',
                'message': f"API request failed: {str(e)}",
                'endpoint': endpoint
            }