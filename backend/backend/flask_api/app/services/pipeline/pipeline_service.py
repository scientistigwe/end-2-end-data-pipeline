# app/services/pipeline/pipeline_service.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.pipeline_manager import PipelineManager
from backend.database.repository.pipeline_repository import PipelineRepository
from backend.core.messaging.types import ModuleIdentifier, ComponentType, ProcessingMessage


class PipelineService:
    """
    Pipeline service that coordinates between API layer, pipeline manager, and repository.
    Handles pipeline lifecycle, execution, monitoring, and management.
    """
    
    def __init__(self, message_broker: MessageBroker, repository: PipelineRepository):
        self.message_broker = message_broker
        self.repository = repository
        self.pipeline_manager = PipelineManager(message_broker, repository)
        self.logger = logging.getLogger(__name__)
        
        # Subscribe to pipeline events
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Setup handlers for pipeline events"""
        try:
            pipeline_service_id = ModuleIdentifier(
                component_name="PipelineService",
                component_type=ComponentType.MANAGER,
                method_name="handle_message"
            )

            self.message_broker.subscribe(
                component=pipeline_service_id,
                pattern="pipeline.status_update",
                callback=self._handle_status_update
            )
            self.message_broker.subscribe(
                component=pipeline_service_id,
                pattern="pipeline.error", 
                callback=self._handle_error
            )
        except Exception as e:
            self.logger.error(f"Failed to setup event handlers: {str(e)}")
            raise
                
    def list_pipelines(self, filters: Dict[str, Any], 
                      page: int = 1, 
                      page_size: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """
        List pipelines with filtering and pagination
        
        Args:
            filters: Filter criteria
            page: Page number
            page_size: Items per page
            
        Returns:
            Tuple of (pipelines list, total count)
        """
        try:
            pipelines, total = self.repository.list_pipelines(filters, page, page_size)
            
            # Enrich with runtime status for active pipelines
            for pipeline in pipelines:
                if pipeline['status'] in ['running', 'paused']:
                    try:
                        runtime_status = self.pipeline_manager.get_pipeline_status(
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

    def get_pipeline_details(self, pipeline_id: UUID, 
                           include_history: bool = False) -> Dict[str, Any]:
        """
        Get complete pipeline details
        
        Args:
            pipeline_id: Pipeline identifier
            include_history: Whether to include execution history
            
        Returns:
            Pipeline details dictionary
        """
        try:
            # Get basic pipeline info
            pipeline = self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Add runtime status if pipeline is active
            if pipeline['status'] in ['running', 'paused']:
                try:
                    runtime_status = self.pipeline_manager.get_pipeline_status(pipeline_id)
                    pipeline['runtime_status'] = runtime_status
                except Exception as status_error:
                    self.logger.warning(
                        f"Failed to get runtime status: {str(status_error)}"
                    )

            # Add metrics
            try:
                pipeline['metrics'] = self.get_pipeline_metrics(pipeline_id)
            except Exception as metrics_error:
                self.logger.warning(
                    f"Failed to get metrics: {str(metrics_error)}"
                )
                pipeline['metrics'] = {}

            # Add history if requested
            if include_history:
                try:
                    pipeline['history'] = self.repository.get_pipeline_history(
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

    def create_pipeline(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create new pipeline
        
        Args:
            config: Pipeline configuration
            
        Returns:
            Created pipeline details
        """
        try:
            # Validate configuration
            validation_result = self._validate_pipeline_config(config)
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid pipeline configuration: {validation_result['errors']}"
                )

            # Create in repository
            pipeline = self.repository.create_pipeline(config)

            # Initialize in manager
            self.pipeline_manager.initialize_pipeline(
                UUID(pipeline['id']),
                config
            )

            # Log creation event
            self.repository.log_pipeline_event(
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

    def update_pipeline(self, pipeline_id: UUID, 
                       config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update pipeline configuration
        
        Args:
            pipeline_id: Pipeline identifier
            config: Updated configuration
            
        Returns:
            Updated pipeline details
        """
        try:
            # Validate configuration
            validation_result = self._validate_pipeline_config(config)
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid pipeline configuration: {validation_result['errors']}"
                )

            # Get current status
            current_status = self.repository.get_pipeline(pipeline_id)
            if not current_status:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Update in repository
            pipeline = self.repository.update_pipeline(pipeline_id, config)

            # Handle running pipeline
            if current_status['status'] == 'running':
                self.pipeline_manager.reinitialize_pipeline(pipeline_id, config)

            # Log update event
            self.repository.log_pipeline_event(
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

    def start_pipeline(self, pipeline_id: UUID, 
                      run_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start pipeline execution
        
        Args:
            pipeline_id: Pipeline identifier
            run_config: Optional runtime configuration
            
        Returns:
            Pipeline status
        """
        try:
            # Verify pipeline exists
            pipeline = self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Check if already running
            if pipeline['status'] == 'running':
                raise ValueError(f"Pipeline already running: {pipeline_id}")

            # Create run record
            run = self.repository.create_run(
                pipeline_id,
                run_config or {}
            )

            # Start in manager
            self.pipeline_manager.start_pipeline(
                pipeline_id,
                run['id'],
                run_config
            )

            # Update status and log event
            self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'running'}
            )
            self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'STARTED',
                    'message': 'Pipeline started',
                    'details': {'run_id': run['id']}
                }
            )

            return self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to start pipeline: {str(e)}")
            raise

    def stop_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Stop pipeline execution"""
        try:
            # Verify pipeline exists and is running
            pipeline = self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            if pipeline['status'] != 'running':
                raise ValueError(f"Pipeline not running: {pipeline_id}")

            # Stop in manager
            self.pipeline_manager.stop_pipeline(pipeline_id)

            # Update status and log event
            self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'stopped'}
            )
            self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'STOPPED',
                    'message': 'Pipeline stopped'
                }
            )

            return self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to stop pipeline: {str(e)}")
            raise

    def pause_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Pause pipeline execution"""
        try:
            # Verify pipeline exists and is running
            pipeline = self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            if pipeline['status'] != 'running':
                raise ValueError(f"Pipeline not running: {pipeline_id}")

            # Pause in manager
            self.pipeline_manager.pause_pipeline(pipeline_id)

            # Update status and log event
            self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'paused'}
            )
            self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'PAUSED',
                    'message': 'Pipeline paused'
                }
            )

            return self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to pause pipeline: {str(e)}")
            raise

    def resume_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Resume paused pipeline"""
        try:
            # Verify pipeline exists and is paused
            pipeline = self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            if pipeline['status'] != 'paused':
                raise ValueError(f"Pipeline not paused: {pipeline_id}")

            # Resume in manager
            self.pipeline_manager.resume_pipeline(pipeline_id)

            # Update status and log event
            self.repository.save_pipeline_state(
                pipeline_id,
                {'status': 'running'}
            )
            self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'RESUMED',
                    'message': 'Pipeline resumed'
                }
            )

            return self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to resume pipeline: {str(e)}")
            raise

    def get_pipeline_history(self, pipeline_id: UUID,
                           start_time: Optional[datetime] = None,
                           end_time: Optional[datetime] = None,
                           page: int = 1,
                           page_size: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """Get pipeline execution history"""
        try:
            runs, total = self.repository.get_pipeline_history(
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

    def get_pipeline_logs(self, pipeline_id: UUID,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         event_types: Optional[List[str]] = None,
                         page: int = 1,
                         page_size: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """Get pipeline execution logs"""
        try:
            logs, total = self.repository.get_pipeline_logs(
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

    def get_pipeline_metrics(self, pipeline_id: UUID,
                           time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get pipeline performance metrics"""
        try:
            # Get historical metrics from repository
            metrics = self.repository.get_pipeline_metrics(pipeline_id, time_range)

            # Add runtime metrics if pipeline is active
            try:
                runtime_metrics = self.pipeline_manager.get_pipeline_metrics(pipeline_id)
                metrics.update(runtime_metrics)
            except Exception as runtime_error:
                self.logger.warning(
                    f"Failed to get runtime metrics: {str(runtime_error)}"
                )

            return metrics

        except Exception as e:
            self.logger.error(f"Failed to get pipeline metrics: {str(e)}")
            raise

    def get_pipeline_templates(self) -> List[Dict[str, Any]]:
        """Get available pipeline templates"""
        try:
            return self.repository.list_templates()
        except Exception as e:
            self.logger.error(f"Failed to get pipeline templates: {str(e)}")
            raise

    def create_pipeline_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Create new pipeline template"""
        try:
            # Validate template
            validation_result = self._validate_pipeline_config(template['config'])
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid template configuration: {validation_result['errors']}"
                )

            return self.repository.create_template(template)
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to create pipeline template: {str(e)}")
            raise

    def schedule_pipeline(self, pipeline_id: UUID,
                         schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule pipeline execution"""
        try:
            # Validate schedule
            validation_result = self._validate_schedule_config(schedule)
            if not validation_result['valid']:
                raise ValueError(
                    f"Invalid schedule configuration: {validation_result['errors']}"
                )

            # Update schedule in repository
            self.repository.update_pipeline_schedule(pipeline_id, schedule)

            # Update in pipeline manager
            self.pipeline_manager.update_pipeline_schedule(pipeline_id, schedule)

            # Log event
            self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'SCHEDULED',
                    'message': 'Pipeline schedule updated',
                    'details': {'schedule': schedule}
                }
            )

            return self.get_pipeline_details(pipeline_id)

        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to schedule pipeline: {str(e)}")
            raise

    def export_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Export pipeline configuration with full details"""
        try:
            # Get pipeline with all related data
            pipeline = self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Add version history
            versions = self.repository.get_pipeline_versions(pipeline_id)

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

    def import_pipeline(self, config: Dict[str, Any], owner_id: UUID) -> Dict[str, Any]:
        """Import pipeline from exported configuration"""
        try:
            # Validate import format
            if 'version' not in config or 'pipeline' not in config:
                raise ValueError("Invalid import format")

            # Prepare pipeline config
            pipeline_config = config['pipeline']
            pipeline_config['owner_id'] = owner_id

            # Create new pipeline
            pipeline = self.create_pipeline(pipeline_config)

            # Log import event
            self.repository.log_pipeline_event(
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

    def clone_pipeline(self, pipeline_id: UUID, new_name: str) -> Dict[str, Any]:
        """Clone existing pipeline with new name"""
        try:
            # Get source pipeline
            source = self.repository.get_pipeline(pipeline_id)
            if not source:
                raise ValueError(f"Source pipeline not found: {pipeline_id}")

            # Prepare clone config
            clone_config = dict(source)
            clone_config['name'] = new_name
            clone_config.pop('id', None)
            clone_config.pop('created_at', None)
            clone_config.pop('updated_at', None)

            # Create clone
            clone = self.create_pipeline(clone_config)

            # Log clone event
            self.repository.log_pipeline_event(
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

    def _handle_status_update(self, message: ProcessingMessage) -> None:
        """Handle pipeline status update events"""
        try:
            pipeline_id = UUID(message.metadata['pipeline_id'])
            status = message.metadata['status']
            details = message.metadata.get('details', {})

            # Update repository state
            self.repository.save_pipeline_state(
                pipeline_id,
                {
                    'status': status,
                    'current_step': details.get('current_step'),
                    'progress': details.get('progress', 0)
                }
            )

            # Log event
            self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'STATUS_UPDATE',
                    'message': f"Pipeline status updated to {status}",
                    'details': details
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling status update: {str(e)}")

    def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle pipeline error events"""
        try:
            pipeline_id = UUID(message.metadata['pipeline_id'])
            error = message.metadata['error']

            # Update repository state
            self.repository.save_pipeline_state(
                pipeline_id,
                {
                    'status': 'failed',
                    'error': error
                }
            )

            # Log error event
            self.repository.log_pipeline_event(
                pipeline_id,
                {
                    'type': 'ERROR',
                    'message': f"Pipeline error: {error}",
                    'details': message.metadata.get('details', {})
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling pipeline error: {str(e)}")

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

    def _validate_schedule_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schedule configuration"""
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
        """Validate cron expression format"""
        try:
            parts = expression.split()
            return len(parts) == 5  # Simple validation, could be enhanced
        except:
            return False

    def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            self.pipeline_manager.cleanup()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            raise