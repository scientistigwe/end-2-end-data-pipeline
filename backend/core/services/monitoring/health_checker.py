import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import psutil
import aiohttp
from enum import Enum

from ..base.base_service import BaseService
from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    MonitoringContext,
    HealthStatus,
    ComponentStatus,
    HealthCheckResult
)

logger = logging.getLogger(__name__)

class HealthCheckType(Enum):
    """Types of health checks"""
    SYSTEM = "system"
    COMPONENT = "component"
    SERVICE = "service"
    DATABASE = "database"
    NETWORK = "network"
    CUSTOM = "custom"

class HealthChecker(BaseService):
    """
    Service for performing system-wide health checks.
    Handles component status monitoring, service availability, and system health reporting.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        
        # Service identifier
        self.module_identifier = ModuleIdentifier(
            component_name="health_checker",
            component_type=ComponentType.MONITORING_SERVICE,
            department="monitoring",
            role="health"
        )

        # Health check configuration
        self.check_interval = 60  # seconds
        self.timeout = 10  # seconds
        self.retry_count = 3
        self.retry_delay = 5  # seconds
        
        # Health check state
        self.component_status: Dict[str, ComponentStatus] = {}
        self.health_history: List[HealthCheckResult] = []
        self.active_checks: Dict[str, asyncio.Task] = {}
        
        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup handlers for health check messages"""
        handlers = {
            MessageType.MONITORING_HEALTH_START: self._handle_health_check_start,
            MessageType.MONITORING_HEALTH_STOP: self._handle_health_check_stop,
            MessageType.MONITORING_HEALTH_CHECK: self._handle_health_check_request,
            MessageType.MONITORING_COMPONENT_STATUS: self._handle_component_status
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_health_check_start(self, message: ProcessingMessage) -> None:
        """Handle request to start health checking"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Start health checking if not already running
            if pipeline_id not in self.active_checks:
                check_task = asyncio.create_task(
                    self._perform_health_checks(pipeline_id)
                )
                self.active_checks[pipeline_id] = check_task

            # Publish health check start notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'started'
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to start health checking: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_health_check_stop(self, message: ProcessingMessage) -> None:
        """Handle request to stop health checking"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Stop health checking if running
            if pipeline_id in self.active_checks:
                self.active_checks[pipeline_id].cancel()
                del self.active_checks[pipeline_id]

            # Publish health check stop notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_STOP,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'stopped'
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to stop health checking: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_health_check_request(self, message: ProcessingMessage) -> None:
        """Handle immediate health check request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")

            # Perform immediate health check
            result = await self._check_system_health(pipeline_id)
            
            # Publish health check result
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_RESULT,
                    content={
                        'pipeline_id': pipeline_id,
                        'result': result
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to perform health check: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_component_status(self, message: ProcessingMessage) -> None:
        """Handle component status updates"""
        try:
            component_id = message.content.get('component_id')
            status = message.content.get('status')
            if not component_id or not status:
                raise ValueError("Component ID and status are required")

            # Update component status
            self.component_status[component_id] = ComponentStatus(
                component_id=component_id,
                status=status,
                timestamp=datetime.now(),
                details=message.content.get('details', {})
            )

            # Publish status update notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_COMPONENT_STATUS,
                    content={
                        'component_id': component_id,
                        'status': status,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

        except Exception as e:
            logger.error(f"Failed to update component status: {str(e)}")
            await self._handle_error(message, str(e))

    async def _perform_health_checks(self, pipeline_id: str) -> None:
        """Perform periodic health checks"""
        try:
            while True:
                # Perform system health check
                result = await self._check_system_health(pipeline_id)
                
                # Store result in history
                self.health_history.append(result)
                
                # Clean up old results
                self._cleanup_old_results()
                
                # Publish health check result
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_HEALTH_RESULT,
                        content={
                            'pipeline_id': pipeline_id,
                            'result': result
                        },
                        metadata=MessageMetadata(
                            correlation_id=str(uuid.uuid4()),
                            source_component=self.module_identifier.component_name
                        )
                    )
                )

                # Wait for next check interval
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info(f"Health checking cancelled for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Error in health checking: {str(e)}")
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_FAILED,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    async def _check_system_health(self, pipeline_id: str) -> HealthCheckResult:
        """Check overall system health"""
        try:
            # Check system resources
            system_status = await self._check_system_resources()
            
            # Check component statuses
            component_status = await self._check_component_status()
            
            # Check service availability
            service_status = await self._check_service_availability()
            
            # Check database connectivity
            database_status = await self._check_database_connectivity()
            
            # Check network connectivity
            network_status = await self._check_network_connectivity()
            
            # Determine overall health status
            overall_status = self._determine_overall_status([
                system_status,
                component_status,
                service_status,
                database_status,
                network_status
            ])
            
            # Create health check result
            result = HealthCheckResult(
                pipeline_id=pipeline_id,
                timestamp=datetime.now(),
                status=overall_status,
                details={
                    'system': system_status,
                    'components': component_status,
                    'services': service_status,
                    'database': database_status,
                    'network': network_status
                }
            )
            
            return result

        except Exception as e:
            logger.error(f"Failed to check system health: {str(e)}")
            return HealthCheckResult(
                pipeline_id=pipeline_id,
                timestamp=datetime.now(),
                status=HealthStatus.ERROR,
                details={'error': str(e)}
            )

    async def _check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            return {
                'cpu': {
                    'usage': psutil.cpu_percent(interval=1),
                    'count': psutil.cpu_count(),
                    'status': 'healthy'
                },
                'memory': {
                    'usage': psutil.virtual_memory().percent,
                    'available': psutil.virtual_memory().available,
                    'status': 'healthy'
                },
                'disk': {
                    'usage': psutil.disk_usage('/').percent,
                    'free': psutil.disk_usage('/').free,
                    'status': 'healthy'
                }
            }
        except Exception as e:
            logger.error(f"Failed to check system resources: {str(e)}")
            return {'error': str(e), 'status': 'error'}

    async def _check_component_status(self) -> Dict[str, Any]:
        """Check status of all components"""
        try:
            return {
                component_id: {
                    'status': status.status,
                    'timestamp': status.timestamp.isoformat(),
                    'details': status.details
                }
                for component_id, status in self.component_status.items()
            }
        except Exception as e:
            logger.error(f"Failed to check component status: {str(e)}")
            return {'error': str(e), 'status': 'error'}

    async def _check_service_availability(self) -> Dict[str, Any]:
        """Check availability of critical services"""
        try:
            services = {
                'message_broker': self.message_broker.is_connected(),
                'database': await self._check_database_connectivity(),
                'api': await self._check_api_availability()
            }
            
            return {
                'services': services,
                'status': 'healthy' if all(services.values()) else 'degraded'
            }
        except Exception as e:
            logger.error(f"Failed to check service availability: {str(e)}")
            return {'error': str(e), 'status': 'error'}

    async def _check_database_connectivity(self) -> bool:
        """Check database connectivity"""
        try:
            # Implement database connectivity check
            # This is a placeholder - implement actual database check
            return True
        except Exception as e:
            logger.error(f"Failed to check database connectivity: {str(e)}")
            return False

    async def _check_network_connectivity(self) -> Dict[str, Any]:
        """Check network connectivity"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check connectivity to critical endpoints
                endpoints = {
                    'api': 'http://localhost:8000/health',
                    'database': 'http://localhost:5432/health'
                }
                
                results = {}
                for name, url in endpoints.items():
                    try:
                        async with session.get(url, timeout=self.timeout) as response:
                            results[name] = response.status == 200
                    except Exception as e:
                        results[name] = False
                
                return {
                    'endpoints': results,
                    'status': 'healthy' if all(results.values()) else 'degraded'
                }
        except Exception as e:
            logger.error(f"Failed to check network connectivity: {str(e)}")
            return {'error': str(e), 'status': 'error'}

    async def _check_api_availability(self) -> bool:
        """Check API availability"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/health', timeout=self.timeout) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Failed to check API availability: {str(e)}")
            return False

    def _determine_overall_status(self, statuses: List[Dict[str, Any]]) -> HealthStatus:
        """Determine overall system health status"""
        if any(s.get('status') == 'error' for s in statuses):
            return HealthStatus.ERROR
        elif any(s.get('status') == 'degraded' for s in statuses):
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _cleanup_old_results(self) -> None:
        """Remove old health check results"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.health_history = [
            result for result in self.health_history
            if result.timestamp > cutoff_time
        ] 