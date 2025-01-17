from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from uuid import uuid4
from cachetools import TTLCache
from aiohttp import web
import aiofiles

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingStage,
    ProcessingMessage,
    ModuleIdentifier,
    ComponentType
)
from sqlalchemy.orm import scoped_session
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.utils.rate_limiter import AsyncRateLimiter
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.websocket_manager import WebSocketManager
from .file_validator import FileSourceValidator
from .file_config import Config

logger = logging.getLogger(__name__)


@dataclass
class FileUploadContext:
    """Context for file upload tracking"""
    file_id: str
    pipeline_id: str
    filename: str
    upload_time: datetime
    metadata: Dict[str, Any]
    status: str = 'pending'
    error: Optional[str] = None
    processing_stages: List[str] = None
    current_stage: Optional[str] = None


class FileService:
    """Enhanced file service with comprehensive processing capabilities"""

    def __init__(
            self,
            message_broker: Optional[MessageBroker] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize FileService with required components"""
        # Core components
        self.message_broker = message_broker or MessageBroker()
        self.control_point_manager = control_point_manager or ControlPointManager(
            message_broker=self.message_broker,
            component_name='file_service',
            component_type=ComponentType.FILE_SOURCE
        )
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()

        self.validator = FileSourceValidator(config=self.config, metrics_collector=self.metrics_collector)

        # Initialize monitoring and state tracking
        self.websocket_manager = WebSocketManager()
        self.rate_limiter = AsyncRateLimiter(max_calls=100, period=1.0)
        self.response_cache = TTLCache(maxsize=1000, ttl=3600)
        self.active_uploads: Dict[str, FileUploadContext] = {}
        self.response_queues: Dict[str, asyncio.Queue] = {}

        # Ensure upload directory exists
        os.makedirs(self.config.UPLOAD_DIRECTORY, exist_ok=True)

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            'file.upload.status': self._handle_upload_status,
            'file.processing.status': self._handle_processing_status,
            'file.processing.error': self._handle_processing_error,
            'file.processing.complete': self._handle_processing_complete
        }

        # Register handlers with CPM
        self.control_point_manager.register_handler(
            source_type='file',
            handlers=handlers
        )

    async def handle_file_upload(
            self,
            file_data: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """Handle file upload through CPM"""
        try:
            async with self.rate_limiter:
                # Generate tracking IDs
                file_id = str(uuid4())
                pipeline_id = str(uuid4())

                # Create upload context
                context = FileUploadContext(
                    file_id=file_id,
                    pipeline_id=pipeline_id,
                    filename=file_data['file'].filename,
                    upload_time=datetime.now(),
                    metadata={
                        'user_id': user_id,
                        'original_filename': file_data['file'].filename,
                        'content_type': file_data['file'].content_type,
                        **file_data.get('metadata', {})
                    }
                )

                self.active_uploads[file_id] = context

                # Create control point for initial validation
                control_point = await self.control_point_manager.create_control_point(
                    pipeline_id=pipeline_id,
                    stage=ProcessingStage.INITIAL_VALIDATION,
                    data={
                        'file_metadata': context.metadata,
                        'validation_stage': 'initial'
                    },
                    options=['proceed', 'reject']
                )

                # Wait for validation decision
                decision = await self.control_point_manager.wait_for_decision(
                    control_point.id,
                    timeout=self.config.VALIDATION_TIMEOUT
                )

                if decision.decision == 'proceed':
                    # Save file and initiate processing through CPM
                    saved_path = await self._save_file(file_data['file'], context)
                    context.metadata['saved_path'] = saved_path

                    # Create processing control point
                    process_point = await self.control_point_manager.create_control_point(
                        pipeline_id=pipeline_id,
                        stage=ProcessingStage.PROCESSING,
                        data={
                            'file_id': file_id,
                            'file_path': saved_path,
                            'metadata': context.metadata
                        },
                        options=['process']
                    )

                    return {
                        'status': 'accepted',
                        'file_id': file_id,
                        'pipeline_id': pipeline_id,
                        'tracking_url': f'/api/files/{file_id}/status'
                    }

                else:
                    context.status = 'rejected'
                    context.error = decision.details.get('reason', 'Upload rejected')
                    return {
                        'status': 'rejected',
                        'reason': context.error
                    }

        except Exception as e:
            logger.error(f"File upload error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    def _setup_message_handlers(self) -> None:
        """Set up message broker subscriptions"""
        handlers = {
            'file.upload.status': self._handle_upload_status,
            'file.processing.status': self._handle_processing_status,
            'file.processing.error': self._handle_processing_error,
            'file.processing.complete': self._handle_processing_complete
        }

        for pattern, handler in handlers.items():
            self.message_broker.subscribe(
                component=ModuleIdentifier(
                    component_name='file_service',
                    component_type=ComponentType.SERVICE,
                    method_name=handler.__name__
                ),
                pattern=pattern,
                callback=handler
            )

    async def _validate_upload(
            self,
            file_data: Dict[str, Any],
            context: FileUploadContext
    ) -> Dict[str, Any]:
        """Comprehensive file validation"""
        try:
            validation_results = {
                'passed': True,
                'checks': []
            }

            # Basic validation checks
            checks = [
                ('format', await self.validator.validate_file_format(context.metadata)),
                ('size', await self.validator.validate_file_size(context.metadata)),
                ('security', await self.validator.validate_security(
                    await file_data['file'].read()
                ))
            ]

            # Reset file pointer
            await file_data['file'].seek(0)

            # Process validation results
            for check_type, (passed, message) in checks:
                validation_results['checks'].append({
                    'type': check_type,
                    'passed': passed,
                    'message': message
                })
                if not passed:
                    validation_results['passed'] = False

            return validation_results

        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            return {
                'passed': False,
                'checks': [{
                    'type': 'error',
                    'passed': False,
                    'message': str(e)
                }]
            }

    async def _save_file(
            self,
            file: Any,
            context: FileUploadContext
    ) -> str:
        """Save uploaded file with proper error handling"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.config.UPLOAD_DIRECTORY, exist_ok=True)

            # Generate safe filename
            safe_filename = f"{context.file_id}_{context.filename}"
            file_path = os.path.join(self.config.UPLOAD_DIRECTORY, safe_filename)

            # Save file using aiofiles
            async with aiofiles.open(file_path, 'wb') as f:
                while chunk := await file.read(8192):
                    await f.write(chunk)

            return file_path

        except Exception as e:
            logger.error(f"File save error: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to save file: {str(e)}")

    async def _initiate_processing(self, context: FileUploadContext) -> None:
        """Initiate file processing pipeline"""
        try:
            # Prepare processing message
            processing_message = ProcessingMessage(
                source_identifier=ModuleIdentifier(
                    component_name='file_service',
                    component_type=ComponentType.SERVICE,
                    method_name='initiate_processing'
                ),
                target_identifier=ModuleIdentifier(
                    component_name='file_manager',
                    component_type=ComponentType.MANAGER,
                    method_name='process_file'
                ),
                message_type=MessageType.FILE_PROCESSING_REQUEST,
                content={
                    'file_id': context.file_id,
                    'pipeline_id': context.pipeline_id,
                    'metadata': context.metadata,
                    'file_path': context.metadata['saved_path']
                }
            )

            # Publish processing request
            await self.message_broker.publish(processing_message)

            # Update context
            context.status = 'processing'
            context.current_stage = 'initiated'

        except Exception as e:
            logger.error(f"Processing initiation error: {str(e)}", exc_info=True)
            context.status = 'error'
            context.error = str(e)
            raise

    async def get_upload_status(
            self,
            file_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get current status of file upload and processing"""
        try:
            # Check cache first
            cached_status = self.response_cache.get(file_id)
            if cached_status:
                return cached_status

            # Get context
            context = self.active_uploads.get(file_id)
            if not context:
                return {'status': 'not_found'}

            # Verify user authorization
            if context.metadata['user_id'] != user_id:
                return {'status': 'unauthorized'}

            status = {
                'file_id': context.file_id,
                'pipeline_id': context.pipeline_id,
                'filename': context.filename,
                'status': context.status,
                'current_stage': context.current_stage,
                'upload_time': context.upload_time.isoformat(),
                'processing_stages': context.processing_stages,
                'error': context.error
            }

            # Cache status
            self.response_cache[file_id] = status

            return status

        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}", exc_info=True)
            return {'status': 'error', 'error': str(e)}

    async def _handle_upload_status(self, message: ProcessingMessage) -> None:
        """Handle upload status updates"""
        try:
            file_id = message.content.get('file_id')
            context = self.active_uploads.get(file_id)

            if context:
                context.status = message.content.get('status')
                context.current_stage = message.content.get('stage')

                # Notify through WebSocket if available
                if ws := self.websocket_connections.get(file_id):
                    await ws.send_json({
                        'type': 'status_update',
                        'data': message.content
                    })

        except Exception as e:
            logger.error(f"Status update handling error: {str(e)}", exc_info=True)

    async def _handle_processing_complete(self, message: ProcessingMessage) -> None:
        """Handle processing completion"""
        try:
            file_id = message.content.get('file_id')
            context = self.active_uploads.get(file_id)

            if context:
                context.status = 'completed'
                context.current_stage = 'complete'

                # Clean up
                await self._cleanup_upload(context)

        except Exception as e:
            logger.error(f"Completion handling error: {str(e)}", exc_info=True)

    def list_sources(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List file sources for a specific user
        
        Args:
            user_id: User's unique identifier
        
        Returns:
            List of file sources
        """
        try:
            # Filter active uploads by user_id
            sources = [
                {
                    'id': context.file_id,
                    'pipeline_id': context.pipeline_id,
                    'filename': context.filename,
                    'upload_time': context.upload_time.isoformat(),
                    'status': context.status,
                    'current_stage': context.current_stage,
                    'error': context.error
                }
                for context in self.active_uploads.values()
                if context.metadata.get('user_id') == user_id
            ]
            
            return sources
        except Exception as e:
            logger.error(f"Error listing file sources: {str(e)}", exc_info=True)
            return []
    
    async def _handle_processing_status(self, message: ProcessingMessage) -> None:
        """
        Handle processing status updates for a file
        
        Args:
            message: Processing status message
        """
        try:
            file_id = message.content.get('file_id')
            context = self.active_uploads.get(file_id)

            if context:
                # Update context with new processing status
                context.status = message.content.get('status', context.status)
                context.current_stage = message.content.get('stage', context.current_stage)
                
                # Update processing stages if provided
                if 'processing_stages' in message.content:
                    context.processing_stages = message.content.get('processing_stages')

                # Notify through WebSocket if available
                if ws := self.websocket_manager.get_connection(file_id):
                    await ws.send_json({
                        'type': 'processing_status',
                        'data': {
                            'file_id': file_id,
                            'status': context.status,
                            'current_stage': context.current_stage,
                            'processing_stages': context.processing_stages
                        }
                    })

                # Optional: Log or record the status update
                if self.metrics_collector:
                    await self.metrics_collector.record_processing_status(
                        file_id=file_id,
                        status=context.status,
                        stage=context.current_stage
                    )

        except Exception as e:
            logger.error(f"Processing status handling error: {str(e)}", exc_info=True)
            
    async def _handle_processing_error(self, message: ProcessingMessage) -> None:
        """Handle processing errors"""
        try:
            file_id = message.content.get('file_id')
            context = self.active_uploads.get(file_id)

            if context:
                context.status = 'error'
                context.error = message.content.get('error')

                # Cleanup on error
                await self._cleanup_upload(context)

        except Exception as e:
            logger.error(f"Error handling error: {str(e)}", exc_info=True)

    async def _cleanup_upload(self, context: FileUploadContext) -> None:
        """Clean up upload resources"""
        try:
            # Remove temporary file
            if 'saved_path' in context.metadata:
                try:
                    os.remove(context.metadata['saved_path'])
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file: {str(e)}")

            # Close WebSocket connection
            if ws := self.websocket_connections.get(context.file_id):
                await ws.close()
                del self.websocket_connections[context.file_id]

            # Remove from active uploads
            if context.file_id in self.active_uploads:
                del self.active_uploads[context.file_id]

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)

    def _handle_validation_failure(
            self,
            context: FileUploadContext,
            validation_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle validation failure"""
        context.status = 'validation_failed'
        context.error = '; '.join(
            check['message']
            for check in validation_results['checks']
            if not check['passed']
        )

        return {
            'status': 'validation_failed',
            'errors': [
                check['message']
                for check in validation_results['checks']
                if not check['passed']
            ]
        }

    async def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            # Clean up all active uploads
            for context in list(self.active_uploads.values()):
                await self._cleanup_upload(context)

            # Clear caches and queues
            self.response_cache.clear()
            self.response_queues.clear()

        except Exception as e:
            logger.error(f"Service cleanup error: {str(e)}", exc_info=True)