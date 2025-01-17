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
from backend.core.utils.process_manager import ProcessManager, with_process_handling, ProcessContext
from .s3_validator import S3Validator
from .s3_fetcher import S3Fetcher
from .s3_config import Config

logger = logging.getLogger(__name__)


@dataclass
class S3Context:
    """Context for S3 operations"""
    request_id: str
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)


class S3Manager(BaseManager):
    """Enhanced S3 manager with CPM integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            metrics_collector: Optional[MetricsCollector] = None,
            config: Optional[Config] = None
    ):
        """Initialize S3Manager with required components"""
        super().__init__(
            message_broker=message_broker,
            component_name="S3Manager"
        )

        self.control_point_manager = control_point_manager
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.validator = S3Validator(config=self.config)

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="s3",
            source_id=str(uuid4())
        )

        # State tracking
        self.active_connections: Dict[str, S3Fetcher] = {}
        self.active_operations: Dict[str, S3Context] = {}

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            's3.connect.request': self._handle_connect_request,
            's3.process.object': self._handle_object_request,
            's3.validate.request': self._handle_validate_request,
            's3.list.objects': self._handle_list_request,
            's3.data.extraction': self._handle_data_extraction,
            's3.process.data': self._handle_process_data
        }

        self.control_point_manager.register_handler(
            source_type='s3_manager',
            handlers=handlers
        )

    async def _handle_connect_request(self, control_point: ControlPoint) -> None:
        """Handle S3 connection request through CPM"""
        try:
            request_data = control_point.data
            context = S3Context(
                request_id=str(uuid4()),
                pipeline_id=control_point.pipeline_id,
                stage=ProcessingStage.CONNECTION_CHECK,
                status=ProcessingStatus.PENDING,
                metadata=request_data.get('metadata', {})
            )

            # Validate connection params
            validation_result = await self.validator.validate_connection_comprehensive(
                request_data,
                context.metadata
            )

            if not validation_result['passed']:
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': validation_result['summary']}
                )
                return

            # Create fetcher and test connection
            fetcher = S3Fetcher(request_data)
            connection_check = await fetcher.check_connection()

            if connection_check.get('status') != 'success':
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': connection_check.get('error', 'Connection failed')}
                )
                return

            # Store connection
            connection_id = str(uuid4())
            self.active_connections[connection_id] = fetcher

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'connection_id': connection_id,
                    'diagnostics': connection_check.get('diagnostics', {})
                }
            )

        except Exception as e:
            logger.error(f"Connection request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_object_request(self, control_point: ControlPoint) -> None:
        """Handle S3 object operation through CPM"""
        try:
            request_data = control_point.data
            connection_id = request_data.get('connection_id')

            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            context = S3Context(
                request_id=str(uuid4()),
                pipeline_id=control_point.pipeline_id,
                stage=ProcessingStage.DATA_EXTRACTION,
                status=ProcessingStatus.PENDING,
                metadata=request_data
            )
            self.active_operations[context.request_id] = context

            # Validate object access
            access_check = await self.validator.verify_object_access(
                fetcher.s3_client,
                request_data.get('bucket'),
                request_data.get('key')
            )

            if not access_check['access_granted']:
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': access_check.get('error', 'Access denied')}
                )
                return

            # Create data extraction control point
            extract_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.DATA_EXTRACTION,
                data={
                    'request_id': context.request_id,
                    'connection_id': connection_id,
                    'bucket': request_data.get('bucket'),
                    'key': request_data.get('key'),
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
            logger.error(f"Object request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_data_extraction(self, control_point: ControlPoint) -> None:
        """Handle S3 data extraction through CPM"""
        try:
            extract_data = control_point.data
            connection_id = extract_data['connection_id']
            context = self.active_operations.get(extract_data['request_id'])

            if not context or connection_id not in self.active_connections:
                raise ValueError("Context or connection not found")

            fetcher = self.active_connections[connection_id]

            # Fetch object
            result = await fetcher.fetch_object_async(
                extract_data['bucket'],
                extract_data['key']
            )

            # Create validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.DATA_VALIDATION,
                data={
                    'request_id': context.request_id,
                    'object_data': result,
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

    async def _handle_validate_request(self, control_point: ControlPoint) -> None:
        """Handle validation request through CPM"""
        try:
            validation_data = control_point.data
            context = self.active_operations.get(validation_data['request_id'])

            if not context:
                raise ValueError("Context not found")

            # Validate object data
            validation_results = await self.validator.validate_object_data(
                validation_data['object_data'],
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
                    'object_data': validation_data['object_data'],
                    'validation_results': validation_results,
                    'metadata': context.metadata
                },
                options=['process']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {'process_point_id': process_point.id}
            )

        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_list_request(self, control_point: ControlPoint) -> None:
        """Handle object listing request through CPM"""
        try:
            request_data = control_point.data
            connection_id = request_data.get('connection_id')

            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]

            # List objects
            result = await fetcher.list_objects_async(
                request_data.get('bucket'),
                prefix=request_data.get('prefix', ''),
                max_items=request_data.get('max_items')
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'complete',
                {
                    'objects': result.get('objects', []),
                    'continuation_token': result.get('continuation_token'),
                    'is_truncated': result.get('is_truncated', False)
                }
            )

        except Exception as e:
            logger.error(f"List request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_process_data(self, control_point: ControlPoint) -> None:
        """Handle data processing through CPM"""
        try:
            process_data = control_point.data
            context = self.active_operations.get(process_data['request_id'])

            if not context:
                raise ValueError("Context not found")

            # Process the data based on type and requirements
            processed_result = await self._process_object_data(
                process_data['object_data'],
                context.metadata
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'complete',
                {
                    'request_id': context.request_id,
                    'pipeline_id': context.pipeline_id,
                    'processed_data': processed_result,
                    'metadata': context.metadata
                }
            )

        except Exception as e:
            logger.error(f"Process data error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def cleanup(self) -> None:
        """Clean up manager resources through CPM"""
        try:
            # Close all active connections
            for connection_id in list(self.active_connections.keys()):
                try:
                    fetcher = self.active_connections[connection_id]
                    await fetcher.close()
                except Exception as cleanup_error:
                    logger.error(f"Error closing connection {connection_id}: {cleanup_error}")

            # Clear tracking
            self.active_connections.clear()
            self.active_operations.clear()

            logger.info("S3Manager resources cleaned up")

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)

    async def _process_object_data(self, object_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process S3 object data based on type and metadata"""
        try:
            # Add processing logic based on object type and requirements
            data_type = metadata.get('data_type', 'raw')

            if data_type == 'raw':
                return {'data': object_data}
            else:
                # Add specific processing based on data type
                return {'data': object_data, 'processed': True}

        except Exception as e:
            logger.error(f"Data processing error: {str(e)}", exc_info=True)
            raise

    def _setup_message_handlers(self) -> None:
        """Set up message handlers"""
        handlers = {
            MessageType.SOURCE_READ: self._handle_s3_request,  # Use SOURCE_READ instead of S3_REQUEST
            MessageType.CONTROL_POINT_DECISION: self._handle_control_decision,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.ERROR: self._handle_error,
            # Add source-specific handlers
            MessageType.SOURCE_CONNECT: self._handle_connect_request,
            MessageType.SOURCE_VALIDATE: self._validate_connection,
            MessageType.SOURCE_EXTRACT: self._handle_object_request
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_id,
                pattern=f"{message_type.value}.#",
                callback=handler
            )
            
    @with_process_handling
    async def process_s3_request(
            self,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process S3 request with control points"""
        try:
            # Create operation context
            context = S3Context(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata=request_data.get('metadata', {})
            )

            self.active_operations[context.request_id] = context

            # Process based on action
            action = request_data.get('action')
            if action == 'connect':
                return await self._handle_connect_request(context, request_data)
            elif action == 'process_object':
                return await self._handle_object_request(context, request_data)
            elif action == 'list_objects':
                return await self._handle_list_request(context, request_data)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"S3 request processing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _handle_s3_request(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle incoming S3 requests"""
        try:
            request_data = message.content
            result = await self.process_s3_request(request_data)
            
            # Create response message
            response = message.create_response(
                message_type=MessageType.SOURCE_SUCCESS if result['status'] == 'success' 
                            else MessageType.SOURCE_ERROR,
                content=result
            )
            
            await self.message_broker.publish(response)
            
        except Exception as e:
            logger.error(f"Error handling S3 request: {str(e)}", exc_info=True)
            error_response = message.create_response(
                message_type=MessageType.SOURCE_ERROR,
                content={'error': str(e)}
            )
            await self.message_broker.publish(error_response)

    async def _handle_control_decision(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle control point decisions"""
        try:
            decision_data = message.content
            control_point_id = decision_data.get('control_point_id')
            decision = decision_data.get('decision')
            
            await self.control_point_manager.process_decision(
                control_point_id,
                decision
            )
            
        except Exception as e:
            logger.error(f"Error handling control decision: {str(e)}", exc_info=True)

    async def _handle_status_update(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle status updates"""
        try:
            status_data = message.content
            request_id = status_data.get('request_id')
            
            # Update operation status if active
            if context := self.active_operations.get(request_id):
                context.status = ProcessingStatus(status_data.get('status'))
                await self._update_status(context, status_data.get('message', ''))
                
        except Exception as e:
            logger.error(f"Error handling status update: {str(e)}", exc_info=True)

    async def _handle_error(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle error messages"""
        try:
            error_data = message.content
            request_id = error_data.get('request_id')
            error_message = error_data.get('error')
            
            # Update operation status if active
            if context := self.active_operations.get(request_id):
                await self._handle_error(context, error_message)
                
        except Exception as e:
            logger.error(f"Error handling error message: {str(e)}", exc_info=True)
            
    async def _validate_connection(
            self,
            context: S3Context,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate connection configuration"""
        validation_results = await self.validator.validate_connection_comprehensive(
            request_data,
            context.metadata
        )

        return {
            'validation_results': validation_results,
            'connection_preview': {
                k: v for k, v in request_data.items()
                if k not in ['credentials', 'secret_key']
            }
        }

    async def _establish_connection(
            self,
            context: S3Context,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Establish S3 connection"""
        fetcher = S3Fetcher(request_data)
        connection_check = await fetcher.check_connection()

        return {
            'connection_status': connection_check.get('status'),
            'diagnostics': connection_check.get('diagnostics', {}),
            'capabilities': connection_check.get('capabilities', {})
        }

    async def _verify_access(
            self,
            context: S3Context,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify S3 access permissions"""
        access_check = await self.validator.verify_access_permissions(
            request_data.get('bucket'),
            request_data.get('credentials')
        )

        return {
            'access_check': access_check,
            'permissions': access_check.get('permissions', []),
            'restrictions': access_check.get('restrictions', [])
        }

    async def _create_control_point(
            self,
            context: S3Context,
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
                timeout=self.config.REQUEST_TIMEOUT
            )

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}", exc_info=True)
            raise

    async def _validate_object_request(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Validate object request parameters"""
        validation_results = await self.validator.validate_object_request(
            request_data,
            context.metadata
        )

        return {
            'validation_results': validation_results,
            'object_preview': {
                'bucket': request_data.get('bucket'),
                'key': request_data.get('key'),
                'operation': request_data.get('operation')
            }
        }

    async def _verify_object_access(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Verify access to specific S3 object"""
        bucket = request_data.get('bucket')
        key = request_data.get('key')

        access_check = await self.validator.verify_object_access(
            fetcher.s3_client,
            bucket,
            key
        )

        return {
            'access_check': access_check,
            'object_metadata': access_check.get('metadata', {}),
            'permissions': access_check.get('permissions', [])
        }

    async def _fetch_object(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Fetch object from S3"""
        try:
            bucket = request_data.get('bucket')
            key = request_data.get('key')

            # Record start of fetch
            await self.process_monitor.record_operation_metric(
                'object_fetch_start',
                1,
                bucket=bucket,
                key=key
            )

            start_time = datetime.now()
            result = await fetcher.fetch_object_async(bucket, key)
            duration = (datetime.now() - start_time).total_seconds()

            # Record fetch metrics
            await self.process_monitor.record_operation_metric(
                'object_fetch',
                success=True,
                duration=duration,
                bytes_transferred=result.get('metadata', {}).get('size', 0)
            )

            return {
                'data': result.get('data'),
                'metadata': result.get('metadata'),
                'fetch_stats': {
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            await self.process_monitor.record_error(
                'object_fetch_error',
                error=str(e),
                bucket=bucket,
                key=key
            )
            raise

    async def _validate_object_data(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Validate fetched object data"""
        data = request_data.get('data', {})

        validation_results = await self.validator.validate_object_data(
            data,
            context.metadata
        )

        return {
            'validation_results': validation_results,
            'data_preview': data.get('preview', []),
            'issues': validation_results.get('issues', []),
            'recommendations': validation_results.get('recommendations', [])
        }

    async def _validate_list_request(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Validate object listing request"""
        validation_results = await self.validator.validate_list_request(
            request_data,
            context.metadata
        )

        return {
            'validation_results': validation_results,
            'list_parameters': {
                'bucket': request_data.get('bucket'),
                'prefix': request_data.get('prefix', ''),
                'max_items': request_data.get('max_items')
            }
        }

    async def _verify_list_access(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Verify access for object listing"""
        bucket = request_data.get('bucket')
        access_check = await self.validator.verify_list_access(
            fetcher.s3_client,
            bucket
        )

        return {
            'access_check': access_check,
            'bucket_metadata': access_check.get('metadata', {}),
            'permissions': access_check.get('permissions', [])
        }

    async def _list_objects(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """List objects from S3"""
        try:
            bucket = request_data.get('bucket')
            prefix = request_data.get('prefix', '')

            start_time = datetime.now()
            result = await fetcher.list_objects_async(
                bucket,
                prefix=prefix,
                max_items=request_data.get('max_items')
            )
            duration = (datetime.now() - start_time).total_seconds()

            # Record metrics
            await self.process_monitor.record_operation_metric(
                'object_listing',
                success=True,
                duration=duration,
                object_count=len(result.get('objects', []))
            )

            return {
                'objects': result.get('objects', []),
                'continuation_token': result.get('continuation_token'),
                'is_truncated': result.get('is_truncated', False),
                'listing_stats': {
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            await self.process_monitor.record_error(
                'object_listing_error',
                error=str(e),
                bucket=bucket,
                prefix=prefix
            )
            raise

    async def _process_object_list(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Process object listing results"""
        objects = request_data.get('objects', [])

        # Analyze object types and sizes
        analysis = {
            'total_objects': len(objects),
            'total_size': sum(obj.get('size', 0) for obj in objects),
            'format_distribution': self._analyze_format_distribution(objects),
            'size_distribution': self._analyze_size_distribution(objects)
        }

        return {
            'analysis': analysis,
            'objects': objects,
            'recommendations': self._generate_list_recommendations(analysis)
        }

    def _determine_format(self, key: str) -> str:
        """Determine file format from key"""
        ext = key.split('.')[-1].lower() if '.' in key else 'unknown'
        return ext if ext in self.config.SUPPORTED_FORMATS else 'unknown'

    