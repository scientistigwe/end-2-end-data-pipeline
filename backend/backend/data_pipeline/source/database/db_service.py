# db_service.py
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from .db_manager import DBManager
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator

logger = logging.getLogger(__name__)


class DBService:
    """Service layer for managing database operations"""

    def __init__(self, message_broker=None, orchestrator=None):
        """Initialize DBService with dependency injection"""
        self.message_broker = message_broker or MessageBroker()
        self.db_manager = DBManager(self.message_broker)
        self.orchestrator = orchestrator
        logger.info("DBService initialized with MessageBroker")

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

    def _create_pipeline_entry(self, connection_id: str, query_result: Dict) -> str:
        """Create a pipeline entry for tracking"""
        if not hasattr(self, 'pipeline_service'):
            from backend.data_pipeline.pipeline_service import PipelineService
            self.pipeline_service = PipelineService(
                message_broker=self.message_broker,
                orchestrator=self._get_orchestrator()
            )

        config = {
            'connection_id': connection_id,
            'source_type': 'database',
            'metadata': query_result.get('metadata', {}),
            'start_time': datetime.now().isoformat()
        }

        pipeline_id = self.pipeline_service.start_pipeline(config)
        logger.info(f"Created pipeline {pipeline_id} for database connection {connection_id}")
        return pipeline_id

    def establish_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Establish database connection"""
        try:
            result = self.db_manager.initialize_connection(config)
            return result
        except Exception as e:
            logger.error(f"Connection error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to establish connection: {str(e)}"
            }

    def execute_query(self, connection_id: str, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute database query"""
        try:
            result = self.db_manager.process_query(connection_id, query, params)

            if result.get('status') == 'success':
                pipeline_id = self._create_pipeline_entry(connection_id, result)
                result['pipeline_id'] = pipeline_id

            logger.info(f"Query execution result: {result.get('status')}")
            return result

        except Exception as e:
            logger.error(f"Query execution error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Query execution failed: {str(e)}",
                'connection_id': connection_id
            }

    def close_connection(self, connection_id: str) -> Dict[str, Any]:
        """Close database connection"""
        try:
            self.db_manager.close_connection(connection_id)
            return {
                'status': 'success',
                'message': 'Connection closed successfully'
            }
        except Exception as e:
            logger.error(f"Connection closure error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to close connection: {str(e)}"
            }