
# s3_service.py
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from .s3_manager import S3Manager
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator

logger = logging.getLogger(__name__)


class S3Service:
    """Service layer for managing S3 operations"""

    def __init__(self, message_broker=None, orchestrator=None):
        """Initialize S3Service with dependency injection"""
        self.message_broker = message_broker or MessageBroker()
        self.s3_manager = S3Manager(self.message_broker)
        self.orchestrator = orchestrator
        logger.info("S3Service initialized with MessageBroker")

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

    def _create_pipeline_entry(self, s3_path: str, process_result: Dict) -> str:
        """Create a pipeline entry for tracking"""
        if not hasattr(self, 'pipeline_service'):
            from backend.data_pipeline.pipeline_service import PipelineService
            self.pipeline_service = PipelineService(
                message_broker=self.message_broker,
                orchestrator=self._get_orchestrator()
            )

        config = {
            's3_path': s3_path,
            'source_type': 's3',
            'metadata': process_result.get('metadata', {}),
            'start_time': datetime.now().isoformat()
        }

        pipeline_id = self.pipeline_service.start_pipeline(config)
        logger.info(f"Created pipeline {pipeline_id} for S3 path {s3_path}")
        return pipeline_id

    def establish_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Establish S3 connection"""
        try:
            result = self.s3_manager.initialize_connection(config)
            return result
        except Exception as e:
            logger.error(f"S3 connection error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to establish S3 connection: {str(e)}"
            }

    def process_object(self, connection_id: str, bucket: str, key: str) -> Dict[str, Any]:
        """Process S3 object"""
        try:
            s3_path = f"s3://{bucket}/{key}"
            result = self.s3_manager.process_s3_object(connection_id, bucket, key)

            if result.get('status') == 'success':
                pipeline_id = self._create_pipeline_entry(s3_path, result)
                result['pipeline_id'] = pipeline_id

            logger.info(f"S3 processing result: {result.get('status')}")
            return result

        except Exception as e:
            logger.error(f"S3 processing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"S3 processing failed: {str(e)}",
                'connection_id': connection_id,
                's3_path': f"s3://{bucket}/{key}"
            }

    def close_connection(self, connection_id: str) -> Dict[str, Any]:
        """Close S3 connection"""
        try:
            self.s3_manager.close_connection(connection_id)
            return {
                'status': 'success',
                'message': 'S3 connection closed successfully'
            }
        except Exception as e:
            logger.error(f"S3 connection closure error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to close S3 connection: {str(e)}"
            }