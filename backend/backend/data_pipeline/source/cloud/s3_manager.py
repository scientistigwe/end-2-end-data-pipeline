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
from backend.core.utils.process_manager import ProcessManager, with_process_handling
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
    """Enhanced S3 manager with control point integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            config: Optional[Config] = None
    ):
        """Initialize S3Manager with required components"""
        super().__init__(
            message_broker=message_broker,
            component_name="S3Manager"
        )

        self.control_point_manager = control_point_manager
        self.config = config or Config()
        self.validator = S3Validator(config=self.config)

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="s3",
            source_id=str(uuid4())
        )

        # Initialize process handler
        self.process_handler = ProcessHandler(config=self.config.RETRY)

        # State tracking
        self.active_connections: Dict[str, S3Fetcher] = {}
        self.active_operations: Dict[str, S3Context] = {}

        # Initialize handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up message handlers"""
        handlers = {
            MessageType.S3_REQUEST: self._handle_s3_request,
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

    async def _handle_connect_request(
            self,
            context: S3Context,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle S3 connection request with control points"""
        try:
            stages = [
                (ProcessingStage.INITIAL_VALIDATION, self._validate_connection),
                (ProcessingStage.CONNECTION_CHECK, self._establish_connection),
                (ProcessingStage.ACCESS_CHECK, self._verify_access)
            ]

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
                    options=['proceed', 'reject']
                )

                if decision['decision'] == 'reject':
                    await self._handle_rejection(context, decision.get('details', {}))
                    raise ValueError(f"Connection rejected at stage {stage.value}")

            # Store connection
            connection_id = str(uuid4())
            fetcher = S3Fetcher(self.config)
            self.active_connections[connection_id] = fetcher

            return {
                'status': 'success',
                'request_id': context.request_id,
                'connection_id': connection_id,
                'pipeline_id': context.pipeline_id
            }

        except Exception as e:
            await self._handle_error(context, str(e))
            raise

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

    async def _handle_object_request(
            self,
            context: S3Context,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle S3 object operation with control points"""
        try:
            # Verify connection
            connection_id = request_data.get('connection_id')
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]

            stages = [
                (ProcessingStage.INITIAL_VALIDATION, self._validate_object_request),
                (ProcessingStage.ACCESS_CHECK, self._verify_object_access),
                (ProcessingStage.DATA_EXTRACTION, self._fetch_object),
                (ProcessingStage.DATA_VALIDATION, self._validate_object_data),
                (ProcessingStage.PROCESSING, self._process_object_data)
            ]

            stage_results = {}

            for stage, processor in stages:
                context.stage = stage
                await self._update_status(context, f"Starting {stage.value}")

                # Process stage
                result = await processor(
                    context,
                    request_data,
                    fetcher=fetcher
                )

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

            return {
                'status': 'success',
                'request_id': context.request_id,
                'pipeline_id': context.pipeline_id,
                'data': stage_results
            }

        except Exception as e:
            await self._handle_error(context, str(e))
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

    async def _process_object_data(
            self,
            context: S3Context,
            request_data: Dict[str, Any],
            fetcher: S3Fetcher
    ) -> Dict[str, Any]:
        """Process object data based on format"""
        try:
            data = request_data.get('data', {})
            format_type = self._determine_format(request_data.get('key', ''))

            # Record processing start
            await self.process_monitor.record_metric(
                'data_processing_start',
                1,
                format=format_type
            )

            start_time = datetime.now()

            # Process based on format
            if format_type == 'csv':
                processed_data = await self._process_csv_data(data)
            elif format_type == 'json':
                processed_data = await self._process_json_data(data)
            elif format_type == 'parquet':
                processed_data = await self._process_parquet_data(data)
            else:
                processed_data = await self._process_generic_data(data)

            duration = (datetime.now() - start_time).total_seconds()

            # Record processing metrics
            await self.process_monitor.record_operation_metric(
                'data_processing',
                success=True,
                duration=duration,
                format=format_type,
                rows_processed=processed_data.get('row_count', 0)
            )

            return {
                'processed_data': processed_data,
                'format': format_type,
                'processing_stats': {
                    'duration': duration,
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            await self.process_monitor.record_error(
                'data_processing_error',
                error=str(e),
                format=format_type
            )
            raise

    async def _handle_list_request(
            self,
            context: S3Context,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle S3 object listing with control points"""
        try:
            connection_id = request_data.get('connection_id')
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]

            stages = [
                (ProcessingStage.INITIAL_VALIDATION, self._validate_list_request),
                (ProcessingStage.ACCESS_CHECK, self._verify_list_access),
                (ProcessingStage.DATA_EXTRACTION, self._list_objects),
                (ProcessingStage.PROCESSING, self._process_object_list)
            ]

            stage_results = {}

            for stage, processor in stages:
                context.stage = stage
                await self._update_status(context, f"Starting {stage.value}")

                result = await processor(
                    context,
                    request_data,
                    fetcher=fetcher
                )

                decision = await self._create_control_point(
                    context=context,
                    stage=stage,
                    data=result,
                    options=['proceed', 'reject']
                )

                if decision['decision'] == 'reject':
                    await self._handle_rejection(context, decision.get('details', {}))
                    raise ValueError(f"Listing rejected at stage {stage.value}")

                stage_results[stage.value] = result

            return {
                'status': 'success',
                'request_id': context.request_id,
                'pipeline_id': context.pipeline_id,
                'data': stage_results
            }

        except Exception as e:
            await self._handle_error(context, str(e))
            raise

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

    def _analyze_format_distribution(
            self,
            objects: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze distribution of object formats"""
        formats = {}
        for obj in objects:
            fmt = self._determine_format(obj.get('key', ''))
            formats[fmt] = formats.get(fmt, 0) + 1
        return formats

    def _analyze_size_distribution(
            self,
            objects: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze distribution of object sizes"""
        size_ranges = {
            'small': 0,  # < 1MB
            'medium': 0,  # 1MB - 100MB
            'large': 0,  # 100MB - 1GB
            'very_large': 0  # > 1GB
        }

        for obj in objects:
            size = obj.get('size', 0)
            if size < 1024 * 1024:
                size_ranges['small'] += 1
            elif size < 100 * 1024 * 1024:
                size_ranges['medium'] += 1
            elif size < 1024 * 1024 * 1024:
                size_ranges['large'] += 1
            else:
                size_ranges['very_large'] += 1

        return size_ranges

    def _generate_list_recommendations(
            self,
            analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on object list analysis"""
        recommendations = []

        # Size-based recommendations
        if analysis['size_distribution'].get('very_large', 0) > 0:
            recommendations.append({
                'type': 'optimization',
                'message': 'Consider using multipart download for large objects',
                'objects_affected': analysis['size_distribution']['very_large']
            })

        # Format-based recommendations
        for fmt, count in analysis['format_distribution'].items():
            if fmt == 'unknown':
                recommendations.append({
                    'type': 'format',
                    'message': f'Found {count} objects with unknown format',
                    'suggestion': 'Verify file extensions and content types'
                })

        return recommendations