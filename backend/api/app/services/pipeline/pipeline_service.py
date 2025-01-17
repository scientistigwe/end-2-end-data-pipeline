# app/services/pipeline/pipeline_service.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from core.messaging.broker import MessageBroker
from core.messaging.event_types import MessageType
from core.managers.pipeline_manager import PipelineManager
from db.repository.pipeline_repository import PipelineRepository
from core.messaging.event_types import ModuleIdentifier, ComponentType, ProcessingMessage

import asyncio


class PipelineService:
    """
    Asynchronous Pipeline Service for coordinating pipeline lifecycle and management.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: PipelineRepository,
            logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the Pipeline Service with async capabilities.
        """
        self.message_broker = message_broker
        self.repository = repository
        self.pipeline_manager = PipelineManager(message_broker, repository)
        self.logger = logger or logging.getLogger(__name__)

        # Create module identifier with the correct component type
        self.module_id = ModuleIdentifier(
            component_name="PipelineService",
            component_type=ComponentType.SERVICE,  # Use SERVICE
            method_name="handle_message"
        )

        # Asynchronous initialization
        self._initialize_async()

    def _initialize_async(self) -> None:
        """
        Initialize asynchronous components in a thread-safe manner.
        """
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run async initialization in the event loop
        try:
            loop.run_until_complete(self._async_initialize())
        except Exception as e:
            self.logger.error(f"Async initialization failed: {str(e)}")
            raise

    async def _async_initialize(self) -> None:
        """
        Asynchronous initialization of the Pipeline Service.
        """
        try:
            # Create module identifier for subscriptions
            pipeline_service_id = ModuleIdentifier(
                component_name="PipelineService",
                component_type=ComponentType.SERVICE,  # Changed from MANAGER to SERVICE
                method_name="handle_message"
            )

            # Rest of the method remains the same
        except Exception as e:
            self.logger.error(f"Async initialization failed: {str(e)}")
            raise

    def _setup_event_handlers(self) -> None:
        """Setup handlers for pipeline events"""
        try:
            pipeline_service_id = ModuleIdentifier(
                component_name="PipelineService",
                component_type=ComponentType.SERVICE,  # Changed from MANAGER to SERVICE
                method_name="handle_message"
            )

            # Rest of the method remains the same
        except Exception as e:
            self.logger.error(f"Failed to setup event handlers: {str(e)}")
            raise

    async def list_pipelines(
            self,
            filters: Dict[str, Any],
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Asynchronously list pipelines with filtering and pagination.

        Args:
            filters (Dict[str, Any]): Filter criteria
            page (int, optional): Page number. Defaults to 1.
            page_size (int, optional): Items per page. Defaults to 50.

        Returns:
            Tuple[List[Dict[str, Any]], int]: List of pipelines and total count
        """
        try:
            # Use repository's method (assuming it supports async)
            pipelines, total = await self.repository.list_pipelines(filters, page, page_size)

            # Enrich with runtime status
            for pipeline in pipelines:
                if pipeline['status'] in ['running', 'paused']:
                    try:
                        runtime_status = await self.pipeline_manager.get_pipeline_status(
                            pipeline['id']
                        )
                        pipeline['runtime_status'] = runtime_status
                    except Exception as status_error:
                        self.logger.warning(
                            f"Failed to get runtime status for pipeline {pipeline['id']}: {str(status_error)}"
                        )

            return pipelines, total

        except Exception as e:
            self.logger.error(f"Failed to list pipelines: {str(e)}")
            raise

    async def create_pipeline(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously create a new pipeline.

        Args:
            config (Dict[str, Any]): Pipeline configuration

        Returns:
            Dict[str, Any]: Created pipeline details
        """
        try:
            # Validate configuration
            validation_result = self._validate_pipeline_config(config)
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid pipeline configuration: {validation_result['errors']}"
                )

            # Create in repository
            pipeline = await self.repository.create_pipeline(config)

            # Initialize in manager (assuming this method exists in PipelineManager)
            await self.pipeline_manager.initialize_pipeline(
                UUID(pipeline['id']),
                config
            )

            # Log creation event
            await self.repository.log_pipeline_event(
                UUID(pipeline['id']),
                {
                    'type': 'CREATED',
                    'message': 'Pipeline created',
                    'details': {'config': config}
                }
            )

            return pipeline

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {str(e)}")
            raise

    async def start_pipeline(
            self,
            pipeline_id: UUID,
            run_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously start pipeline execution.

        Args:
            pipeline_id (UUID): Pipeline identifier
            run_config (Optional[Dict[str, Any]], optional): Runtime configuration

        Returns:
            Dict[str, Any]: Pipeline details
        """
        try:
            # Verify pipeline exists
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Check if already running
            if pipeline['status'] == 'running':
                raise ValueError(f"Pipeline already running: {pipeline_id}")

            # Create run record
            run = await self.repository.create_run(
                pipeline_id,
                run_config or {}
            )

            # Start in manager
            await self.pipeline_manager.start_pipeline(
                pipeline_id,
                run['id'],
                run_config
            )

            # Update status and log event
            await self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'running'}
            )
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'STARTED',
                    'message': 'Pipeline started',
                    'details': {'run_id': run['id']}
                }
            )

            return await self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to start pipeline: {str(e)}")
            raise

    # Add async methods for other core operations (stop, pause, resume, etc.)
    # Implement similar async patterns as shown in start_pipeline method

    async def _handle_status_update(self, message: ProcessingMessage) -> None:
        """
        Async handler for pipeline status update events.

        Args:
            message (ProcessingMessage): Status update message
        """
        try:
            pipeline_id = UUID(message.metadata['pipeline_id'])
            status = message.metadata['status']
            details = message.metadata.get('details', {})

            # Update repository state
            await self.repository.save_pipeline_state(
                pipeline_id,
                {
                    'status': status,
                    'current_step': details.get('current_step'),
                    'progress': details.get('progress', 0)
                }
            )

            # Log event
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'STATUS_UPDATE',
                    'message': f"Pipeline status updated to {status}",
                    'details': details
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling status update: {str(e)}")

    async def cleanup(self) -> None:
        """
        Asynchronously cleanup service resources.
        """
        try:
            await self.pipeline_manager.cleanup()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise

    async def get_pipeline_details(
            self,
            pipeline_id: UUID,
            include_history: bool = False
    ) -> Dict[str, Any]:
        """
        Asynchronously get complete pipeline details.

        Args:
            pipeline_id (UUID): Pipeline identifier
            include_history (bool, optional): Whether to include execution history

        Returns:
            Dict[str, Any]: Pipeline details
        """
        try:
            # Get basic pipeline info
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Add runtime status if pipeline is active
            if pipeline['status'] in ['running', 'paused']:
                try:
                    runtime_status = await self.pipeline_manager.get_pipeline_status(pipeline_id)
                    pipeline['runtime_status'] = runtime_status
                except Exception as status_error:
                    self.logger.warning(
                        f"Failed to get runtime status: {str(status_error)}"
                    )

            # Add metrics
            try:
                pipeline['metrics'] = await self.get_pipeline_metrics(pipeline_id)
            except Exception as metrics_error:
                self.logger.warning(
                    f"Failed to get metrics: {str(metrics_error)}"
                )
                pipeline['metrics'] = {}

            # Add history if requested
            if include_history:
                try:
                    pipeline['history'] = await self.repository.get_pipeline_history(
                        pipeline_id,
                        start_time=datetime.utcnow() - timedelta(days=30)
                    )
                except Exception as history_error:
                    self.logger.warning(
                        f"Failed to get history: {str(history_error)}"
                    )
                    pipeline['history'] = []

            return pipeline

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get pipeline details: {str(e)}")
            raise

    async def update_pipeline(
            self,
            pipeline_id: UUID,
            config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Asynchronously update pipeline configuration.

        Args:
            pipeline_id (UUID): Pipeline identifier
            config (Dict[str, Any]): Updated configuration

        Returns:
            Dict[str, Any]: Updated pipeline details
        """
        try:
            # Validate configuration
            validation_result = self._validate_pipeline_config(config)
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid pipeline configuration: {validation_result['errors']}"
                )

            # Get current status
            current_status = await self.repository.get_pipeline(pipeline_id)
            if not current_status:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Update in repository
            pipeline = await self.repository.update_pipeline(pipeline_id, config)

            # Handle running pipeline
            if current_status['status'] == 'running':
                await self.pipeline_manager.reinitialize_pipeline(pipeline_id, config)

            # Log update event
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'UPDATED',
                    'message': 'Pipeline configuration updated',
                    'details': {'config': config}
                }
            )

            return pipeline

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to update pipeline: {str(e)}")
            raise

    async def stop_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """
        Asynchronously stop pipeline execution.

        Args:
            pipeline_id (UUID): Pipeline identifier

        Returns:
            Dict[str, Any]: Updated pipeline details
        """
        try:
            # Verify pipeline exists and is running
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            if pipeline['status'] != 'running':
                raise ValueError(f"Pipeline not running: {pipeline_id}")

            # Stop in manager
            await self.pipeline_manager.stop_pipeline(pipeline_id)

            # Update status and log event
            await self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'stopped'}
            )
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'STOPPED',
                    'message': 'Pipeline stopped'
                }
            )

            return await self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to stop pipeline: {str(e)}")
            raise

    async def pause_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """
        Asynchronously pause pipeline execution.

        Args:
            pipeline_id (UUID): Pipeline identifier

        Returns:
            Dict[str, Any]: Updated pipeline details
        """
        try:
            # Verify pipeline exists and is running
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            if pipeline['status'] != 'running':
                raise ValueError(f"Pipeline not running: {pipeline_id}")

            # Pause in manager
            await self.pipeline_manager.pause_pipeline(pipeline_id)

            # Update status and log event
            await self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'paused'}
            )
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'PAUSED',
                    'message': 'Pipeline paused'
                }
            )

            return await self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to pause pipeline: {str(e)}")
            raise

    async def resume_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """
        Asynchronously resume paused pipeline.

        Args:
            pipeline_id (UUID): Pipeline identifier

        Returns:
            Dict[str, Any]: Updated pipeline details
        """
        try:
            # Verify pipeline exists and is paused
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            if pipeline['status'] != 'paused':
                raise ValueError(f"Pipeline not paused: {pipeline_id}")

            # Resume in manager
            await self.pipeline_manager.resume_pipeline(pipeline_id)

            # Update status and log event
            await self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'running'}
            )
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'RESUMED',
                    'message': 'Pipeline resumed'
                }
            )

            return await self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to resume pipeline: {str(e)}")
            raise

    async def get_pipeline_history(
            self,
            pipeline_id: UUID,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Asynchronously get pipeline execution history.

        Args:
            pipeline_id (UUID): Pipeline identifier
            start_time (Optional[datetime], optional): Start time filter
            end_time (Optional[datetime], optional): End time filter
            page (int, optional): Page number
            page_size (int, optional): Items per page

        Returns:
            Tuple[List[Dict[str, Any]], int]: List of runs and total count
        """
        try:
            runs, total = await self.repository.get_pipeline_history(
                pipeline_id,
                start_time,
                end_time,
                page,
                page_size
            )
            return runs, total
        except Exception as e:
            self.logger.error(f"Failed to get pipeline history: {str(e)}")
            raise

    async def get_pipeline_logs(
            self,
            pipeline_id: UUID,
            start_time: Optional[datetime] = None,
            end_time: Optional[datetime] = None,
            event_types: Optional[List[str]] = None,
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Asynchronously get pipeline execution logs.

        Args:
            pipeline_id (UUID): Pipeline identifier
            start_time (Optional[datetime], optional): Start time filter
            end_time (Optional[datetime], optional): End time filter
            event_types (Optional[List[str]], optional): Event type filters
            page (int, optional): Page number
            page_size (int, optional): Items per page

        Returns:
            Tuple[List[Dict[str, Any]], int]: List of logs and total count
        """
        try:
            logs, total = await self.repository.get_pipeline_logs(
                pipeline_id,
                start_time,
                end_time,
                event_types,
                page,
                page_size
            )
            return logs, total
        except Exception as e:
            self.logger.error(f"Failed to get pipeline logs: {str(e)}")
            raise

    async def get_pipeline_metrics(
            self,
            pipeline_id: UUID,
            time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously get pipeline performance metrics.

        Args:
            pipeline_id (UUID): Pipeline identifier
            time_range (Optional[timedelta], optional): Time range for metrics

        Returns:
            Dict[str, Any]: Pipeline metrics
        """
        try:
            # Get historical metrics from repository
            metrics = await self.repository.get_pipeline_metrics(pipeline_id, time_range)

            # Add runtime metrics if pipeline is active
            try:
                runtime_metrics = await self.pipeline_manager.get_pipeline_metrics(pipeline_id)
                metrics.update(runtime_metrics)
            except Exception as runtime_error:
                self.logger.warning(
                    f"Failed to get runtime metrics: {str(runtime_error)}"
                )

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get pipeline metrics: {str(e)}")
            raise

    async def get_pipeline_templates(self) -> List[Dict[str, Any]]:
        """
        Asynchronously get available pipeline templates.

        Returns:
            List[Dict[str, Any]]: List of pipeline templates
        """
        try:
            return await self.repository.list_templates()
        except Exception as e:
            self.logger.error(f"Failed to get pipeline templates: {str(e)}")
            raise

    async def create_pipeline_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously create a new pipeline template.

        Args:
            template (Dict[str, Any]): Pipeline template configuration

        Returns:
            Dict[str, Any]: Created pipeline template
        """
        try:
            # Validate template
            validation_result = self._validate_pipeline_config(template['config'])
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid template configuration: {validation_result['errors']}"
                )

            return await self.repository.create_template(template)
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create pipeline template: {str(e)}")
            raise

    async def schedule_pipeline(
            self,
            pipeline_id: UUID,
            schedule: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Asynchronously schedule pipeline execution.

        Args:
            pipeline_id (UUID): Pipeline identifier
            schedule (Dict[str, Any]): Schedule configuration

        Returns:
            Dict[str, Any]: Updated pipeline details
        """
        try:
            # Validate schedule
            validation_result = self._validate_schedule_config(schedule)
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid schedule configuration: {validation_result['errors']}"
                )

            # Update schedule in repository
            await self.repository.update_pipeline_schedule(pipeline_id, schedule)

            # Update in pipeline manager
            await self.pipeline_manager.update_pipeline_schedule(pipeline_id, schedule)

            # Log event
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'SCHEDULED',
                    'message': 'Pipeline schedule updated',
                    'details': {'schedule': schedule}
                }
            )

            return await self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to schedule pipeline: {str(e)}")
            raise

    async def export_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """
        Asynchronously export pipeline configuration with full details.

        Args:
            pipeline_id (UUID): Pipeline identifier

        Returns:
            Dict[str, Any]: Exported pipeline configuration
        """
        try:
            # Get pipeline with all related data
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Add version history
            versions = await self.repository.get_pipeline_versions(pipeline_id)

            # Create export format
            return {
                'version': '1.0',
                'exported_at': datetime.utcnow().isoformat(),
                'pipeline': pipeline,
                'versions': versions,
                'metadata': {
                    'exported_by': 'pipeline_service',
                    'export_version': '1.0'
                }
            }

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to export pipeline: {str(e)}")
            raise

    async def import_pipeline(
            self,
            config: Dict[str, Any],
            owner_id: UUID
    ) -> Dict[str, Any]:
        """
        Asynchronously import pipeline from exported configuration.

        Args:
            config (Dict[str, Any]): Exported pipeline configuration
            owner_id (UUID): Owner identifier

        Returns:
            Dict[str, Any]: Imported pipeline details
        """
        try:
            # Validate import format
            if 'version' not in config or 'pipeline' not in config:
                raise ValueError("Invalid import format")

            # Prepare pipeline config
            pipeline_config = config['pipeline']
            pipeline_config['owner_id'] = owner_id

            # Create new pipeline
            pipeline = await self.create_pipeline(pipeline_config)

            # Log import event
            await self.repository.log_pipeline_event(
                UUID(pipeline['id']),
                {
                    'type': 'IMPORTED',
                    'message': 'Pipeline imported',
                    'details': {
                        'source_version': config['version'],
                        'imported_at': datetime.utcnow().isoformat()
                    }
                }
            )

            return pipeline

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to import pipeline: {str(e)}")
            raise

    async def clone_pipeline(
            self,
            pipeline_id: UUID,
            new_name: str
    ) -> Dict[str, Any]:
        """
        Asynchronously clone an existing pipeline with a new name.

        Args:
            pipeline_id (UUID): Source pipeline identifier
            new_name (str): Name for the cloned pipeline

        Returns:
            Dict[str, Any]: Cloned pipeline details
        """
        try:
            # Get source pipeline
            source = await self.repository.get_pipeline(pipeline_id)
            if not source:
                raise ValueError(f"Source pipeline not found: {pipeline_id}")

            # Prepare clone config
            clone_config = dict(source)
            clone_config['name'] = new_name
            clone_config.pop('id', None)
            clone_config.pop('created_at', None)
            clone_config.pop('updated_at', None)

            # Create clone
            clone = await self.create_pipeline(clone_config)

            # Log clone event
            await self.repository.log_pipeline_event(
                UUID(clone['id']),
                {
                    'type': 'CLONED',
                    'message': 'Pipeline cloned',
                    'details': {
                        'source_pipeline_id': str(pipeline_id),
                        'source_name': source['name']
                    }
                }
            )

            return clone

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to clone pipeline: {str(e)}")
            raise


    async def _handle_error(self, message: ProcessingMessage) -> None:
        """
        Async handler for pipeline error events.

        Args:
            message (ProcessingMessage): Error message
        """
        try:
            pipeline_id = UUID(message.metadata['pipeline_id'])
            error = message.metadata['error']

            # Update repository state
            await self.repository.save_pipeline_state(
                pipeline_id,
                {
                    'status': 'failed',
                    'error': error
                }
            )

            # Log error event
            await self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'ERROR',
                    'message': f"Pipeline error: {error}",
                    'details': message.metadata.get('details', {})
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling pipeline error: {str(e)}")


    def _validate_schedule_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schedule configuration.

        Args:
            config (Dict[str, Any]): Schedule configuration

        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }

            if 'enabled' not in config:
                validation_result['valid'] = False
                validation_result['errors'].append("Missing required field: enabled")

            if config.get('enabled'):
                if 'cron' not in config:
                    validation_result['valid'] = False
                    validation_result['errors'].append("Missing required field: cron")
                elif not self._validate_cron_expression(config['cron']):
                    validation_result['valid'] = False
                    validation_result['errors'].append("Invalid cron expression")

            return validation_result

        except Exception as e:
            self.logger.error(f"Error validating schedule config: {str(e)}")
            raise


    def _validate_cron_expression(self, expression: str) -> bool:
        """
        Validate cron expression format.

        Args:
            expression (str): Cron expression to validate

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            parts = expression.split()
            # Simple validation: 5 parts (minute, hour, day of month, month, day of week)
            return len(parts) == 5 and all(part != '*' for part in parts)
        except Exception:
            return False


    async def _handle_message_error(
            self,
            message: ProcessingMessage,
            error: Exception
    ) -> None:
        """
        Handle errors that occur during message processing.

        Args:
            message (ProcessingMessage): Original message
            error (Exception): Error that occurred
        """
        try:
            # Log error details
            self.logger.error(f"Message processing error: {str(error)}")

            # Create and send error notification
            error_message = ProcessingMessage(
                source_identifier=self.module_id,  # You'll need to define module_id
                target_identifier=message.source_identifier,
                message_type=MessageType.ERROR,
                content={
                    'original_message_id': message.message_id,
                    'error_details': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            self.logger.error(f"Error in error handling: {str(e)}")

    def _validate_pipeline_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pipeline configuration"""
        try:
            validation_result = {
                'valid': True,
                'errors': [],
                'warnings': []
            }

            # Required fields
            required = ['name', 'steps']
            for field in required:
                if field not in config:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"Missing required field: {field}")

            # Validate steps
            if 'steps' in config:
                for i, step in enumerate(config['steps']):
                    if 'type' not in step:
                        validation_result['valid'] = False
                        validation_result['errors'].append(
                            f"Step {i} missing required field: type"
                        )
                    if 'name' not in step:
                        validation_result['valid'] = False
                        validation_result['errors'].append(
                            f"Step {i} missing required field: name"
                        )

            return validation_result

        except Exception as e:
            self.logger.error(f"Error validating pipeline config: {str(e)}")
            raise
