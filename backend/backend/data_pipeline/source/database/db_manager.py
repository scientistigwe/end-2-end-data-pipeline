# db_manager.py
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.engine import Engine

from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier
from .db_validator import DBValidator
from .db_fetcher import DBFetcher

logger = logging.getLogger(__name__)


class DBManager:
    """Enhanced database management system with messaging integration"""

    def __init__(self, message_broker):
        """Initialize DBManager with component registration"""
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = DBValidator()

        # Initialize with consistent UUID
        component_uuid = self.registry.get_component_uuid("DBManager")
        self.module_id = ModuleIdentifier("DBManager", "process_query", component_uuid)

        # Track active queries and connections
        self.pending_queries: Dict[str, Dict[str, Any]] = {}
        self.active_connections: Dict[str, DBFetcher] = {}

        # Register and subscribe
        self._initialize_messaging()
        logger.info(f"DBManager initialized with ID: {self.module_id.get_tag()}")

    def _initialize_messaging(self) -> None:
        """Set up message broker registration and subscriptions"""
        try:
            # Register with message broker
            self.message_broker.register_module(self.module_id)

            # Get orchestrator ID with consistent UUID
            orchestrator_id = ModuleIdentifier(
                "DataOrchestrator",
                "manage_pipeline",
                self.registry.get_component_uuid("DataOrchestrator")
            )

            # Subscribe to orchestrator responses
            self.message_broker.subscribe_to_module(
                orchestrator_id.get_tag(),
                self._handle_orchestrator_response
            )
            logger.info("DBManager messaging initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing messaging: {str(e)}")
            raise

    def initialize_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize database connection"""
        try:
            connection_id = str(uuid.uuid4())

            # Create and validate connection
            db_fetcher = DBFetcher(config)
            is_valid, message = self.validator.validate_connection(db_fetcher.engine)

            if not is_valid:
                raise ValueError(message)

            # Store connection
            self.active_connections[connection_id] = db_fetcher

            return {
                'status': 'success',
                'connection_id': connection_id,
                'message': 'Database connection established'
            }

        except Exception as e:
            logger.error(f"Connection initialization error: {str(e)}")
            raise

    def process_query(self, connection_id: str, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Main entry point for database query processing"""
        try:
            if connection_id not in self.active_connections:
                raise ValueError("Invalid connection ID")

            query_id = str(uuid.uuid4())
            db_fetcher = self.active_connections[connection_id]

            # Store query info
            self.pending_queries[query_id] = {
                'connection_id': connection_id,
                'query': query,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }

            logger.info(f"Starting query processing: {query_id}")

            # Step 1: Validate query
            self._validate_query(db_fetcher.engine, query)

            # Step 2: Process query
            processed_data = self._process_query_data(db_fetcher, query, params)

            # Step 3: Update pending query status
            self.pending_queries[query_id]['status'] = 'processed'
            self.pending_queries[query_id]['processed_data'] = processed_data

            # Step 4: Send processed data to orchestrator
            self._send_to_orchestrator(query_id, processed_data)

            return processed_data

        except Exception as e:
            logger.error(f"Query processing error: {str(e)}")
            raise

    def _validate_query(self, engine: Engine, query: str) -> None:
        """Validate query before execution"""
        is_valid, message = self.validator.validate_query(engine, query)
        if not is_valid:
            raise ValueError(message)

    def _process_query_data(self, db_fetcher: DBFetcher, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Process database query with error handling"""
        try:
            # Execute query
            result = db_fetcher.fetch_data(query, params)

            return {
                "status": "success",
                "data": result['data'].to_dict(orient="records"),
                "metadata": {
                    "row_count": result['row_count'],
                    "columns": result['columns'],
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            raise ValueError(str(e))

    def _send_to_orchestrator(self, query_id: str, processed_data: Dict[str, Any]) -> None:
        """Send processed data to orchestrator"""
        try:
            orchestrator_id = ModuleIdentifier(
                "DataOrchestrator",
                "manage_pipeline",
                self.registry.get_component_uuid("DataOrchestrator")
            )

            message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=orchestrator_id,
                message_type=MessageType.ACTION,
                content={
                    'query_id': query_id,
                    'action': 'process_db_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': 'database'
                }
            )

            logger.info(f"Sending data to orchestrator: {orchestrator_id.get_tag()}")
            self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            raise

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
        """Handle responses from orchestrator"""
        try:
            query_id = message.content.get('query_id')
            if not query_id or query_id not in self.pending_queries:
                logger.warning(f"Received response for unknown query ID: {query_id}")
                return

            query_data = self.pending_queries[query_id]

            if message.message_type == MessageType.ACTION:
                logger.info(f"Query {query_id} processed successfully")
                self._cleanup_pending_query(query_id)
            elif message.message_type == MessageType.ERROR:
                logger.error(f"Error processing query {query_id}")
                self._handle_orchestrator_error(query_id, message.content.get('error'))

        except Exception as e:
            logger.error(f"Error handling orchestrator response: {str(e)}")

    def _cleanup_pending_query(self, query_id: str) -> None:
        """Clean up processed query data"""
        if query_id in self.pending_queries:
            del self.pending_queries[query_id]
            logger.info(f"Cleaned up pending query: {query_id}")

    def close_connection(self, connection_id: str) -> None:
        """Close database connection and cleanup"""
        try:
            if connection_id in self.active_connections:
                self.active_connections[connection_id].close()
                del self.active_connections[connection_id]
                logger.info(f"Closed connection: {connection_id}")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
            raise


