from __future__ import annotations

import os
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ComponentType,
    MessageType,
    ProcessingMessage,
    ModuleIdentifier,
    ProcessingStage,
    ProcessingStatus
)
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.orchestration.base_manager import BaseManager
from .file_fetcher import FileFetcher
from .file_validator import FileValidator, ValidationLevel
from .file_config import Config

logger = logging.getLogger(__name__)


@dataclass
class ProcessingContext:
    """Context for file processing"""
    file_id: str
    pipeline_id: str
    filename: str
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)
    stage: Optional[ProcessingStage] = None


class FileManager(BaseManager):
    """Enhanced file manager with CPM integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            config: Optional[Config] = None
    ):
        """Initialize FileManager"""
        super().__init__(
            message_broker=message_broker,
            component_name="FileManager"
        )

        self.control_point_manager = control_point_manager
        self.config = config or Config()
        self.validator = FileValidator(config=self.config)

        # Processing tracking
        self.active_processes: Dict[str, ProcessingContext] = {}

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            'file.process.request': self._handle_processing_request,
            'file.validate.request': self._handle_validation_request,
            'file.extract.data': self._handle_data_extraction,
            'file.check.quality': self._handle_quality_check
        }

        self.control_point_manager.register_handler(
            source_type='file_manager',
            handlers=handlers
        )

    async def _handle_processing_request(self, control_point: ControlPoint) -> None:
        """Handle file processing request through CPM"""
        try:
            file_data = control_point.data
            context = ProcessingContext(
                file_id=file_data['file_id'],
                pipeline_id=control_point.pipeline_id,
                filename=file_data['metadata']['filename'],
                status=ProcessingStatus.PENDING,
                metadata=file_data['metadata']
            )
            self.active_processes[context.file_id] = context

            # Create extraction control point
            extract_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.DATA_EXTRACTION,
                data={
                    'file_id': context.file_id,
                    'file_path': file_data['file_path'],
                    'metadata': context.metadata
                },
                options=['extract']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {'extract_point_id': extract_point.id}
            )

        except Exception as e:
            logger.error(f"Processing request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_data_extraction(self, control_point: ControlPoint) -> None:
        """Handle data extraction through CPM"""
        try:
            extract_data = control_point.data
            context = self.active_processes.get(extract_data['file_id'])

            if not context:
                raise ValueError("Context not found")

            # Extract data
            fetcher = FileFetcher(extract_data['file_path'])
            df, message = await fetcher.convert_to_dataframe()

            if df is None:
                raise ValueError(f"Data extraction failed: {message}")

            # Create validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.DATA_VALIDATION,
                data={
                    'file_id': context.file_id,
                    'data': df.to_dict(orient='records'),
                    'preview': df.head().to_dict(orient='records'),
                    'columns': list(df.columns),
                    'row_count': len(df),
                    'metadata': context.metadata
                },
                options=['validate']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {'validation_point_id': validation_point.id}
            )

        except Exception as e:
            logger.error(f"Data extraction error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_validation_request(self, control_point: ControlPoint) -> None:
        """Handle validation request through CPM"""
        try:
            validation_data = control_point.data
            context = self.active_processes.get(validation_data['file_id'])

            if not context:
                raise ValueError("Context not found")

            validation_results = await self.validator.validate_file_comprehensive(
                validation_data['file_path'],
                context.metadata,
                ValidationLevel.STRICT
            )

            if not validation_results['passed']:
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {
                        'reason': validation_results['summary'],
                        'details': validation_results['details']
                    }
                )
                return

            # Create quality check control point
            quality_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.QUALITY_CHECK,
                data={
                    'file_id': context.file_id,
                    'validation_results': validation_results,
                    'data': validation_data['data'],
                    'metadata': context.metadata
                },
                options=['check']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {'quality_point_id': quality_point.id}
            )

        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_quality_check(self, control_point: ControlPoint) -> None:
        """Handle quality check through CPM"""
        try:
            check_data = control_point.data
            context = self.active_processes.get(check_data['file_id'])

            if not context:
                raise ValueError("Context not found")

            # Perform quality checks
            quality_metrics = {
                'completeness': await self._check_completeness(check_data['data']),
                'consistency': await self._check_consistency(check_data['data']),
                'validity': await self._check_validity(check_data['data'])
            }

            await self.control_point_manager.submit_decision(
                control_point.id,
                'complete',
                {
                    'file_id': context.file_id,
                    'quality_metrics': quality_metrics,
                    'metadata': context.metadata
                }
            )

        except Exception as e:
            logger.error(f"Quality check error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def cleanup(self) -> None:
        """Clean up manager resources through CPM"""
        try:
            # Clean up active processes
            for file_id in list(self.active_processes.keys()):
                try:
                    context = self.active_processes[file_id]
                    await self._cleanup_process(context)
                except Exception as cleanup_error:
                    logger.error(f"Process cleanup error: {cleanup_error}")

            # Clear tracking
            self.active_processes.clear()

            logger.info("FileManager resources cleaned up")

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)

    async def _cleanup_process(self, context: ProcessingContext) -> None:
        """Clean up process resources"""
        try:
            # Clean up any temporary files if needed
            if 'file_path' in context.metadata:
                try:
                    os.remove(context.metadata['file_path'])
                except Exception as e:
                    logger.error(f"Error removing temporary file: {str(e)}")

            # Remove from active processes
            if context.file_id in self.active_processes:
                del self.active_processes[context.file_id]

        except Exception as e:
            logger.error(f"Process cleanup error: {str(e)}", exc_info=True)

    def _setup_message_handlers(self) -> None:
        """Set up message handlers"""
        handlers = {
            MessageType.FILE_PROCESSING_REQUEST: self._handle_processing_request,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_decision,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_id,
                pattern=f"{message_type.value}.#",
                callback=handler
            )

    async def process_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process file through various stages with control points

        Args:
            file_data: Dictionary containing file information and metadata

        Returns:
            Dictionary containing processing results
        """
        try:
            # Create processing context
            context = ProcessingContext(
                file_id=file_data['file_id'],
                pipeline_id=file_data['pipeline_id'],
                filename=file_data['metadata']['filename'],
                status=ProcessingStatus.PENDING,
                metadata=file_data['metadata']
            )

            self.active_processes[context.file_id] = context

            # Process through stages
            try:
                await self._process_stages(context, file_data)
            except asyncio.CancelledError:
                await self._handle_cancellation(context)
                raise
            except Exception as e:
                await self._handle_error(context, str(e))
                raise

            return {
                'status': 'completed',
                'file_id': context.file_id,
                'pipeline_id': context.pipeline_id
            }

        except Exception as e:
            logger.error(f"File processing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_stages(
            self,
            context: ProcessingContext,
            file_data: Dict[str, Any]
    ) -> None:
        """Process file through various stages"""
        stages = [
            (ProcessingStage.DATA_EXTRACTION, self._extract_data),
            (ProcessingStage.DATA_VALIDATION, self._validate_data),
            (ProcessingStage.QUALITY_CHECK, self._check_quality),
            (ProcessingStage.PROCESSING, self._process_data)
        ]

        for stage, processor in stages:
            context.stage = stage
            await self._update_status(context, f"Starting {stage.value}")

            # Process stage
            result = await processor(context, file_data)

            # Create control point
            decision = await self._create_control_point(
                context=context,
                stage=stage,
                data=result,
                options=['proceed', 'modify', 'reject']
            )

            if decision['decision'] == 'reject':
                await self._handle_rejection(context, decision.get('details', {}))
                raise ValueError(f"Processing rejected at stage {stage.value}")

            elif decision['decision'] == 'modify':
                file_data = await self._apply_modifications(
                    file_data,
                    decision.get('modifications', {})
                )

    async def _extract_data(
            self,
            context: ProcessingContext,
            file_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract data from file"""
        try:
            fetcher = FileFetcher(file_data['file_path'])
            df, message = await fetcher.convert_to_dataframe()

            if df is None:
                raise ValueError(f"Data extraction failed: {message}")

            return {
                'data': df.to_dict(orient='records'),
                'preview': df.head().to_dict(orient='records'),
                'columns': list(df.columns),
                'row_count': len(df)
            }

        except Exception as e:
            logger.error(f"Data extraction error: {str(e)}", exc_info=True)
            raise

    async def _validate_data(
            self,
            context: ProcessingContext,
            file_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate extracted data"""
        try:
            validation_results = await self.validator.validate_file_comprehensive(
                file_data['file_path'],
                context.metadata,
                ValidationLevel.STRICT
            )

            return {
                'validation_results': validation_results,
                'data_preview': file_data.get('preview', [])
            }

        except Exception as e:
            logger.error(f"Data validation error: {str(e)}", exc_info=True)
            raise

    async def _check_quality(
            self,
            context: ProcessingContext,
            file_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform quality checks on data"""
        try:
            quality_metrics = {
                'completeness': await self._check_completeness(file_data),
                'consistency': await self._check_consistency(file_data),
                'validity': await self._check_validity(file_data)
            }

            return {
                'quality_metrics': quality_metrics,
                'data_preview': file_data.get('preview', [])
            }

        except Exception as e:
            logger.error(f"Quality check error: {str(e)}", exc_info=True)
            raise

    async def _process_data(
            self,
            context: ProcessingContext,
            file_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process data after validation"""
        try:
            processed_data = await self._apply_processing(file_data)

            return {
                'processed_data': processed_data,
                'summary': {
                    'input_rows': file_data.get('row_count', 0),
                    'output_rows': len(processed_data),
                    'processing_time': datetime.now().timestamp() - context.created_at.timestamp()
                }
            }

        except Exception as e:
            logger.error(f"Data processing error: {str(e)}", exc_info=True)
            raise

    async def _create_control_point(
            self,
            context: ProcessingContext,
            stage: ProcessingStage,
            data: Dict[str, Any],
            options: List[str]
    ) -> Dict[str, Any]:
        """Create control point and wait for decision"""
        try:
            control_point_id = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=stage,
                data={
                    'file_id': context.file_id,
                    'stage_data': data,
                    'metadata': context.metadata
                },
                options=options
            )

            context.control_points.append(control_point_id)
            context.status = ProcessingStatus.AWAITING_DECISION

            await self._update_status(
                context,
                f"Awaiting decision at {stage.value}"
            )

            # Wait for decision
            return await self.control_point_manager.wait_for_decision(
                control_point_id,
                timeout=self.config.PROCESSING_TIMEOUT
            )

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}", exc_info=True)
            raise

    async def _update_status(
            self,
            context: ProcessingContext,
            message: str
    ) -> None:
        """Update processing status"""
        try:
            status_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("pipeline_manager"),
                message_type=MessageType.STATUS_UPDATE,
                content={
                    'pipeline_id': context.pipeline_id,
                    'file_id': context.file_id,
                    'status': context.status.value,
                    'stage': context.stage.value if context.stage else None,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(status_message)

        except Exception as e:
            logger.error(f"Status update error: {str(e)}", exc_info=True)

    async def _apply_modifications(
            self,
            file_data: Dict[str, Any],
            modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply modifications to data"""
        try:
            # Implement modification logic based on requirements
            return file_data
        except Exception as e:
            logger.error(f"Modification error: {str(e)}", exc_info=True)
            raise

    async def _handle_cancellation(self, context: ProcessingContext) -> None:
        """Handle processing cancellation"""
        try:
            context.status = ProcessingStatus.CANCELLED
            await self._update_status(context, "Processing cancelled")
            await self._cleanup_process(context.file_id)
        except Exception as e:
            logger.error(f"Cancellation handling error: {str(e)}", exc_info=True)

    async def _handle_error(
            self,
            context: ProcessingContext,
            error: str
    ) -> None:
        """Handle processing error"""
        try:
            context.status = ProcessingStatus.ERROR
            context.error = error
            await self._update_status(context, f"Error: {error}")
        except Exception as e:
            logger.error(f"Error handling error: {str(e)}", exc_info=True)

    async def _cleanup_process(self, file_id: str) -> None:
        """Clean up process resources"""
        try:
            if file_id in self.active_processes:
                context = self.active_processes[file_id]

                # Clean up control points
                for control_point_id in context.control_points:
                    try:
                        await self.control_point_manager.cleanup_control_point(
                            control_point_id
                        )
                    except Exception as e:
                        logger.error(
                            f"Control point cleanup error: {str(e)}",
                            exc_info=True
                        )

                # Remove from active processes
                del self.active_processes[file_id]

        except Exception as e:
            logger.error(f"Process cleanup error: {str(e)}", exc_info=True)

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        try:
            # Clean up all active processes
            for file_id in list(self.active_processes.keys()):
                await self._cleanup_process(file_id)

            # Clean up message handlers
            await super().cleanup()

        except Exception as e:
            logger.error(f"Manager cleanup error: {str(e)}", exc_info=True)