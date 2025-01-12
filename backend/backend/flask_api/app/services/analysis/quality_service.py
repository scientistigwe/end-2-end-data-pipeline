# backend/flask_api/app/services/analysis/quality_service.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from backend.database.repository.quality_repository import QualityRepository
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.quality_manager import QualityManager
from backend.data_pipeline.quality_analysis.data_quality_processor import (
    DataQualityProcessor,
    QualityAnalysisResult
)

logger = logging.getLogger(__name__)

class QualityService:
    """
    Service layer for quality analysis functionality.
    Coordinates between API layer, quality manager, and repository.
    """
    
    def __init__(self, repository: QualityRepository, 
                 message_broker: Optional[MessageBroker] = None):
        self.repository = repository
        self.message_broker = message_broker or MessageBroker()
        self.quality_manager = QualityManager(self.message_broker, self.repository)
        self.processor = DataQualityProcessor(self.message_broker)
        self.logger = logging.getLogger(__name__)

    def start_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Start quality analysis"""
        try:
            # Create check record
            check = self.repository.create_quality_check(data)
            
            # Start analysis in manager
            self.quality_manager.initiate_quality_check({
                'check_id': str(check.id),
                'pipeline_id': data.get('pipeline_id'),
                'dataset_id': data.get('dataset_id'),
                'config': data.get('config', {}),
                'metadata': data.get('metadata', {})
            })
            
            return {
                'check_id': str(check.id),
                'status': 'pending'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start analysis: {str(e)}")
            raise

    def get_analysis_status(self, check_id: UUID) -> Dict[str, Any]:
        """Get analysis status"""
        try:
            # Get database status
            check = self.repository.get_check(check_id)
            if not check:
                raise ValueError(f"Check {check_id} not found")
                
            # Get runtime status
            runtime_status = self.quality_manager.get_quality_status(
                str(check.pipeline_id)
            )
            
            # Get metrics
            metrics = self.repository.get_quality_metrics(check_id)
            
            return {
                'status': check.status,
                'progress': runtime_status.get('progress', 0) if runtime_status else 0,
                'phase': runtime_status.get('phase') if runtime_status else None,
                'metrics': [self._format_metric(m) for m in metrics],
                'created_at': check.created_at.isoformat(),
                'updated_at': check.updated_at.isoformat(),
                'error': check.error
            }
            
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get analysis status: {str(e)}")
            raise

    def list_analyses(self, filters: Dict[str, Any],
                     page: int = 1,
                     page_size: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """List quality analyses"""
        try:
            checks, total = self.repository.list_checks(filters, page, page_size)
            return [self._format_check(check) for check in checks], total
            
        except Exception as e:
            self.logger.error(f"Failed to list analyses: {str(e)}")
            raise

    def get_analysis_report(self, check_id: UUID) -> Dict[str, Any]:
        """Get analysis report"""
        try:
            check = self.repository.get_check(check_id)
            if not check:
                raise ValueError(f"Check {check_id} not found")
                
            # Get metrics
            metrics = self.repository.get_quality_metrics(check_id)
            
            return {
                'check_id': str(check_id),
                'pipeline_id': str(check.pipeline_id),
                'type': check.type,
                'name': check.name,
                'config': check.config,
                'results': check.results,
                'metrics': [self._format_metric(m) for m in metrics],
                'metadata': check.metadata,
                'created_at': check.created_at.isoformat(),
                'completed_at': check.updated_at.isoformat()
            }
            
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f"Failed to get analysis report: {str(e)}")
            raise

    def create_quality_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create quality profile"""
        try:
            profile = self.repository.create_quality_profile(data)
            return self._format_profile(profile)
            
        except Exception as e:
            self.logger.error(f"Failed to create quality profile: {str(e)}")
            raise

    def get_quality_profiles(self) -> List[Dict[str, Any]]:
        """Get active quality profiles"""
        try:
            profiles = self.repository.get_active_profiles()
            return [self._format_profile(p) for p in profiles]
            
        except Exception as e:
            self.logger.error(f"Failed to get quality profiles: {str(e)}")
            raise

    def _format_check(self, check: Any) -> Dict[str, Any]:
        """Format quality check for API response"""
        return {
            'id': str(check.id),
            'pipeline_id': str(check.pipeline_id),
            'dataset_id': str(check.dataset_id) if check.dataset_id else None,
            'type': check.type,
            'name': check.name,
            'status': check.status,
            'error': check.error,
            'created_at': check.created_at.isoformat(),
            'updated_at': check.updated_at.isoformat()
        }

    def _format_metric(self, metric: Any) -> Dict[str, Any]:
        """Format quality metric for API response"""
        return {
            'name': metric.name,
            'value': metric.value,
            'type': metric.type,
            'metadata': metric.metadata,
            'created_at': metric.created_at.isoformat()
        }

    def _format_profile(self, profile: Any) -> Dict[str, Any]:
        """Format quality profile for API response"""
        return {
            'id': str(profile.id),
            'name': profile.name,
            'description': profile.description,
            'rules': profile.rules,
            'metadata': profile.metadata,
            'is_active': profile.is_active,
            'created_at': profile.created_at.isoformat(),
            'updated_at': profile.updated_at.isoformat()
        }    
