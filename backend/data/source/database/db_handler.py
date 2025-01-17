# backend/source_handlers/database/db_handler.py

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union

from backend.core.messaging.broker import MessageBroker
from backend.core.staging.staging_manager import StagingManager
from backend.core.messaging.types import (
    MessageType, ProcessingMessage, ModuleIdentifier, ComponentType,
    ProcessingStage, ProcessingStatus
)
from .db_validator import DatabaseSourceValidator, DatabaseValidationConfig
from .db_connector import DatabaseConnector
from .db_config import DatabaseSourceConfig

logger = logging.getLogger(__name__)


class DatabaseHandler:
    """Core handler for database data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            validator_config: Optional[DatabaseValidationConfig] = None,
            timeout: int = 30,
            max_retries: int = 3
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker
        self.timeout = timeout
        self.max_retries = max_retries
        self.validator = DatabaseSourceValidator(config=validator_config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="database_handler",
            component_type=ComponentType.HANDLER,
            department="source",
            role="handler"
        )

        # Chunk size for processing
        self.chunk_size = 8192  # 8KB chunks

    async def handle_database_request(
            self,
            source_type: str,
            host: str,
            database: str,
            query: Optional[str] = None,
            operation: str = 'read',
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process incoming database request

        Args:
            source_type: Type of database (e.g., postgresql, mysql)
            host: Database host
            database: Database name
            query: SQL query or operation-specific instruction
            operation: Type of operation (read, write, etc.)
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary containing staging information
        """
        try:
            # Validate source configuration
            source_data = {
                'source_type': source_type,
                'host': host,
                'database': database,
                'username': auth.get('username') if auth else None,
                'operation': operation
            }
            validation_result = await self.validator.validate_source(source_data)

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process based on operation
            if operation == 'read':
                return await self._process_read_request(
                    source_type, host, database, query, params, auth, metadata
                )
            elif operation == 'write':
                return await self._process_write_request(
                    source_type, host, database, query, params, auth, metadata
                )
            else:
                raise ValueError(f"Unsupported operation: {operation}")

        except Exception as e:
            logger.error(f"Database request handling error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_read_request(
            self,
            source_type: str,
            host: str,
            database: str,
            query: Optional[str] = None,
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process database read request

        Args:
            source_type: Type of database
            host: Database host
            database: Database name
            query: SQL query
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary with query results
        """
        try:
            # Create database configuration
            db_config = DatabaseSourceConfig(
                source_type=source_type,
                host=host,
                database=database,
                username=auth.get('username') if auth else None
            )

            # Create database connector
            connector = DatabaseConnector(db_config)

            # Connect and execute query
            request_result = await self._execute_query(
                connector, query, params
            )

            # Stage the received data
            staged_id = await self._stage_database_data(
                source_type, database, request_result, metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'db_info': request_result
            }

        except Exception as e:
            logger.error(f"Database read request processing error: {str(e)}")
            raise

    async def _process_write_request(
            self,
            source_type: str,
            host: str,
            database: str,
            query: Optional[str] = None,
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process database write request

        Args:
            source_type: Type of database
            host: Database host
            database: Database name
            query: SQL query
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary with write operation results
        """
        try:
            # Create database configuration
            db_config = DatabaseSourceConfig(
                source_type=source_type,
                host=host,
                database=database,
                username=auth.get('username') if auth else None
            )

            # Create database connector
            connector = DatabaseConnector(db_config)

            # Connect and execute write query
            request_result = await self._execute_write_query(
                connector, query, params
            )

            # Stage the write operation metadata
            staged_id = await self._stage_database_data(
                source_type, database, request_result, metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'db_info': request_result
            }

        except Exception as e:
            logger.error(f"Database write request processing error: {str(e)}")
            raise

    async def _execute_query(
            self,
            connector: DatabaseConnector,
            query: Optional[str] = None,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute database read query

        Args:
            connector: Database connector
            query: SQL query
            params: Query parameters

        Returns:
            Dictionary with query results
        """
        try:
            # Connect to database
            await connector.connect()

            # Execute query
            results = await connector.execute_query(
                query or '',
                params or {}
            )

            # Process results
            return {
                'data': results,
                'metadata': {
                    'row_count': len(results),
                    'columns': list(results[0].keys()) if results else []
                }
            }

        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise
        finally:
            # Ensure connection is closed
            await connector.close()

    async def _execute_write_query(
            self,
            connector: DatabaseConnector,
            query: Optional[str] = None,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute database write query

        Args:
            connector: Database connector
            query: SQL query
            params: Query parameters

        Returns:
            Dictionary with write operation results
        """
        try:
            # Connect to database
            await connector.connect()

            # Execute write query
            result = await connector.execute_write_query(
                query or '',
                params or {}
            )

            # Process results
            return {
                'data': result,
                'metadata': {
                    'rows_affected': result.get('rows_affected', 0),
                    'last_insert_id': result.get('last_insert_id')
                }
            }

        except Exception as e:
            logger.error(f"Write query execution error: {str(e)}")
            raise
        finally:
            # Ensure connection is closed
            await connector.close()

    async def _stage_database_data(
            self,
            source_type: str,
            database: str,
            request_result: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store database query results in staging area

        Args:
            source_type: Type of database
            database: Database name
            request_result: Processed query results
            metadata: Additional metadata

        Returns:
            Staged data identifier
        """
        try:
            # Prepare staging metadata
            staging_metadata = {
                'source_type': source_type,
                'database': database,
                'row_count': request_result.get('metadata', {}).get('row_count', 0),
                'columns': request_result.get('metadata', {}).get('columns', []),
                **(metadata or {})
            }

            # Store in staging
            staged_id = await self.staging_manager.store_data(
                data=request_result.get('data'),
                metadata=staging_metadata,
                source_type='database'
            )

            # Notify about staging
            await self._notify_staging(staged_id, staging_metadata)

            return staged_id

        except Exception as e:
            logger.error(f"Database data staging error: {str(e)}")
            raise

    async def _notify_staging(
            self,
            staged_id: str,
            metadata: Dict[str, Any]
    ) -> None:
        """
        Notify about staged database data

        Args:
            staged_id: Identifier of staged data
            metadata: Staging metadata
        """
        try:
            message = ProcessingMessage(
                source_identifier=self.module_identifier,
                message_type=MessageType.DATA_STORAGE,
                content={
                    'staged_id': staged_id,
                    'source_type': 'database',
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Staging notification error: {str(e)}")