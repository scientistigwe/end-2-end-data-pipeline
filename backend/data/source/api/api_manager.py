from __future__ import annotations

import logging
import asyncio
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
from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.process_manager import ProcessManager, with_process_handling
from .api_validator import APIValidator
from .api_fetcher import APIFetcher
from .api_config import Config

logger = logging.getLogger(__name__)


@dataclass
class APIContext:
    """Context for API request processing"""
    request_id: str
    pipeline_id: str
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)
    stage: Optional[ProcessingStage] = None


class APIManager(BaseManager):
    """Enhanced API manager with CPM integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize APIManager with required components"""
        super().__init__(
            message_broker=message_broker,
            component_name="APIManager"
        )

        self.control_point_manager = control_point_manager
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.validator = APIValidator(config=self.config)

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="api",
            source_id=str(uuid4())
        )

        # Request tracking
        self.active_requests: Dict[str, APIContext] = {}

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            'api.process.request': self._handle_process_request,
            'api.validation.request': self._handle_validation_request,
            'api.fetch.data': self._handle_fetch_data,
            'api.process.response': self._handle_process_response
        }

        self.control_point_manager.register_handler(
            source_type='api_manager',
            handlers=handlers
        )

    async def _handle_process_request(self, control_point: ControlPoint) -> None:
        """Handle API processing request through CPM"""
        try:
            request_data = control_point.data
            context = APIContext(
                request_id=str(uuid4()),
                pipeline_id=control_point.pipeline_id,
                status=ProcessingStatus.PENDING,
                metadata=request_data.get('metadata', {})
            )
            self.active_requests[context.request_id] = context

            # Initial validation
            validation_results = await self.validator.validate_request_comprehensive(
                request_data,
                context.metadata
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

            # Create data fetching control point
            fetch_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.DATA_EXTRACTION,
                data={
                    'request_id': context.request_id,
                    'request_data': request_data,
                    'validation_results': validation_results
                },
                options=['fetch']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'fetch_point_id': fetch_point.id,
                    'validation_results': validation_results
                }
            )

        except Exception as e:
            logger.error(f"Process request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_fetch_data(self, control_point: ControlPoint) -> None:
        """Handle data fetching through CPM"""
        try:
            request_data = control_point.data['request_data']
            context = self.active_requests.get(control_point.data['request_id'])

            if not context:
                raise ValueError("Context not found")

            api_fetcher = APIFetcher(request_data)
            response = await api_fetcher.fetch_data(
                endpoint=request_data['endpoint'],
                method=request_data.get('method', 'GET'),
                params=request_data.get('params')
            )

            # Create response validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.DATA_VALIDATION,
                data={
                    'request_id': context.request_id,
                    'response_data': response,
                    'metadata': context.metadata
                },
                options=['validate']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'validation_point_id': validation_point.id,
                    'response': response
                }
            )

        except Exception as e:
            logger.error(f"Data fetch error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_validation_request(self, control_point: ControlPoint) -> None:
        """Handle validation request through CPM"""
        try:
            validation_data = control_point.data
            context = self.active_requests.get(validation_data['request_id'])

            if not context:
                raise ValueError("Context not found")

            validation_results = await self.validator.validate_response_comprehensive(
                validation_data['response_data'],
                context.metadata
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

            # Create processing control point
            process_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.PROCESSING,
                data={
                    'request_id': context.request_id,
                    'response_data': validation_data['response_data'],
                    'validation_results': validation_results,
                    'metadata': context.metadata
                },
                options=['process']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'process_point_id': process_point.id,
                    'validation_results': validation_results
                }
            )

        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_process_response(self, control_point: ControlPoint) -> None:
        """Handle response processing through CPM"""
        try:
            process_data = control_point.data
            context = self.active_requests.get(process_data['request_id'])

            if not context:
                raise ValueError("Context not found")

            # Final processing result
            await self.control_point_manager.submit_decision(
                control_point.id,
                'complete',
                {
                    'request_id': context.request_id,
                    'pipeline_id': context.pipeline_id,
                    'response_data': process_data['response_data'],
                    'metadata': context.metadata
                }
            )

        except Exception as e:
            logger.error(f"Process response error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    def _setup_message_handlers(self) -> None:
        """Set up message handlers"""
        handlers = {
            MessageType.API_REQUEST: self._handle_api_request,
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

    @with_process_handling
    async def process_api_request(
            self,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process API request with control points

        Args:
            request_data: API request configuration

        Returns:
            Dictionary containing processing results
        """
        try:
            # Create request context
            context = APIContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                status=ProcessingStatus.PENDING,
                metadata=request_data.get('metadata', {})
            )

            self.active_requests[context.request_id] = context

            # Process through stages
            try:
                result = await self._process_stages(context, request_data)
                return {
                    'status': 'success',
                    'request_id': context.request_id,
                    'pipeline_id': context.pipeline_id,
                    'data': result
                }
            except asyncio.CancelledError:
                await self._handle_cancellation(context)
                raise
            except Exception as e:
                await self._handle_error(context, str(e))
                raise

        except Exception as e:
            logger.error(f"API request processing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_stages(
            self,
            context: APIContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process request through various stages with control points"""
        stages = [
            (ProcessingStage.INITIAL_VALIDATION, self._validate_request),
            (ProcessingStage.CONNECTION_CHECK, self._check_connection),
            (ProcessingStage.DATA_EXTRACTION, self._fetch_data),
            (ProcessingStage.DATA_VALIDATION, self._validate_response),
            (ProcessingStage.PROCESSING, self._process_response)
        ]

        stage_results = {}

        for stage, processor in stages:
            context.stage = stage
            await self._update_status(context, f"Starting {stage.value}")

            # Process stage
            result = await processor(context, request_data)

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
                request_data = await self._apply_modifications(
                    request_data,
                    decision.get('modifications', {})
                )

            stage_results[stage.value] = result

        return stage_results

    async def _validate_request(
            self,
            context: APIContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate API request configuration"""
        try:
            validation_results = await self.validator.validate_request_comprehensive(
                request_data,
                context.metadata
            )

            return {
                'validation_results': validation_results,
                'request_preview': {
                    k: v for k, v in request_data.items()
                    if k not in ['credentials', 'auth']
                }
            }

        except Exception as e:
            logger.error(f"Request validation error: {str(e)}", exc_info=True)
            raise

    async def _check_connection(
            self,
            context: APIContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check API connection and credentials"""
        try:
            api_fetcher = APIFetcher(request_data)
            connection_check = await api_fetcher.check_connection()

            return {
                'connection_status': connection_check.get('status'),
                'diagnostics': connection_check.get('diagnostics', {}),
                'rate_limits': connection_check.get('rate_limits', {})
            }

        except Exception as e:
            logger.error(f"Connection check error: {str(e)}", exc_info=True)
            raise

    async def _fetch_data(
            self,
            context: APIContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch data from API"""
        try:
            api_fetcher = APIFetcher(request_data)
            response = await api_fetcher.fetch_data(
                endpoint=request_data['endpoint'],
                method=request_data.get('method', 'GET'),
                params=request_data.get('params')
            )

            return {
                'response_data': response.get('data'),
                'status_code': response.get('status_code'),
                'headers': response.get('headers', {})
            }

        except Exception as e:
            logger.error(f"Data fetch error: {str(e)}", exc_info=True)
            raise

    async def _validate_response(
            self,
            context: APIContext,
            response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate API response"""
        try:
            validation_results = await self.validator.validate_response_comprehensive(
                response_data,
                context.metadata
            )

            return {
                'validation_results': validation_results,
                'data_preview': response_data.get('response_data', {})
            }

        except Exception as e:
            logger.error(f"Response validation error: {str(e)}", exc_info=True)
            raise

    async def _create_control_point(
            self,
            context: APIContext,
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
                    'request_id': context.request_id,
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

            return await self.control_point_manager.wait_for_decision(
                control_point_id,
                timeout=self.config.PROCESSING_TIMEOUT
            )

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}", exc_info=True)
            raise

    async def _update_status(
            self,
            context: APIContext,
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
                    'request_id': context.request_id,
                    'status': context.status.value,
                    'stage': context.stage.value if context.stage else None,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(status_message)

            # Record metrics
            await self.process_monitor.record_status_update(
                status=context.status.value,
                stage=context.stage.value if context.stage else None,
                request_id=context.request_id
            )

        except Exception as e:
            logger.error(f"Status update error: {str(e)}", exc_info=True)