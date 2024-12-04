# stream_service.py
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from .stream_manager import StreamManager
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator

logger = logging.getLogger(__name__)

class StreamService:
    """Service layer for managing stream operations"""

    def __init__(self, message_broker=None, orchestrator=None):
        """Initialize StreamService with dependency injection"""
        self.message_broker = message_broker or MessageBroker()
        self.stream_manager = StreamManager(self.message_broker)
        self.orchestrator = orchestrator
        logger.info("StreamService initialized with MessageBroker")

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

    def _create_pipeline_entry(self, stream_id: str, config: Dict) -> str:
        """Create a pipeline entry for tracking"""
        if not hasattr(self, 'pipeline_service'):
            from backend.data_pipeline.pipeline_service import PipelineService
            self.pipeline_service = PipelineService(
                message_broker=self.message_broker,
                orchestrator=self._get_orchestrator()
            )

        pipeline_config = {
            'stream_id': stream_id,
            'source_type': 'stream',
            'stream_type': config['stream_type'],
            'start_time': datetime.now().isoformat()
        }

        pipeline_id = self.pipeline_service.start_pipeline(pipeline_config)
        logger.info(f"Created pipeline {pipeline_id} for stream {stream_id}")
        return pipeline_id

    def initialize_stream(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize stream connection"""
        try:
            result = self.stream_manager.initialize_stream(config)
            
            if result.get('status') == 'success':
                stream_id = result['stream_id']
                pipeline_id = self._create_pipeline_entry(stream_id, config)
                result['pipeline_id'] = pipeline_id

            return result
        except Exception as e:
            logger.error(f"Stream initialization error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to initialize stream: {str(e)}"
            }

    def start_stream(self, stream_id: str) -> Dict[str, Any]:
        """Start stream processing"""
        try:
            result = self.stream_manager.start_stream_processing(stream_id)
            return result
        except Exception as e:
            logger.error(f"Stream start error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to start stream: {str(e)}"
            }

    def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """Get stream status"""
        try:
            return self.stream_manager.get_stream_status(stream_id)
        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to get stream status: {str(e)}"
            }

    def stop_stream(self, stream_id: str) -> Dict[str, Any]:
        """Stop stream processing"""
        try:
            self.stream_manager.stop_stream(stream_id)
            return {
                'status': 'success',
                'message': 'Stream stopped successfully'
            }
        except Exception as e:
            logger.error(f"Stream stop error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to stop stream: {str(e)}"
            }