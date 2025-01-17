# app/services/monitoring/monitoring_service.py
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import psutil
from sqlalchemy.orm import Session
from .....db.models.monitoring import (
    MonitoringMetric, 
    ResourceUsage,
    Alert,
    AlertRule,
    HealthCheck
)
from .....db.models.pipeline import Pipeline


class MonitoringService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def get_metrics(self, pipeline_id: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get filtered metrics for a pipeline."""
        try:
            query = self.db_session.query(MonitoringMetric).filter(
                MonitoringMetric.pipeline_id == pipeline_id
            )
            
            if filters.get('start_time'):
                query = query.filter(MonitoringMetric.timestamp >= filters['start_time'])
            if filters.get('end_time'):
                query = query.filter(MonitoringMetric.timestamp <= filters['end_time'])
                
            metrics = query.order_by(MonitoringMetric.timestamp.desc()).all()
            
            return [{
                'name': metric.name,
                'value': metric.value,
                'timestamp': metric.timestamp.isoformat(),
                'labels': metric.labels,
                'type': metric.type,
                'unit': metric.unit
            } for metric in metrics]
        except Exception as e:
            self.logger.error(f"Error fetching metrics: {str(e)}")
            raise

    def get_health_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get current health status of a pipeline."""
        try:
            checks = self.db_session.query(HealthCheck).filter(
                HealthCheck.pipeline_id == pipeline_id
            ).order_by(HealthCheck.last_check.desc()).all()
            
            return {
                'overall_status': self._calculate_overall_health(checks),
                'components': [{
                    'component': check.component,
                    'status': check.status,
                    'last_check': check.last_check.isoformat(),
                    'details': check.details
                } for check in checks]
            }
        except Exception as e:
            self.logger.error(f"Error fetching health status: {str(e)}")
            raise

    def get_performance_metrics(self, pipeline_id: str) -> Dict[str, Any]:
        """Get performance metrics for a pipeline."""
        try:
            usage = self.db_session.query(ResourceUsage).filter(
                ResourceUsage.pipeline_id == pipeline_id
            ).order_by(ResourceUsage.timestamp.desc()).first()
            
            if not usage:
                return {}
                
            return {
                'cpu_usage': usage.cpu_usage,
                'memory_usage': usage.memory_usage,
                'disk_usage': usage.disk_usage,
                'network_in': usage.network_in,
                'network_out': usage.network_out,
                'timestamp': usage.timestamp.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error fetching performance metrics: {str(e)}")
            raise

    def get_alert_config(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Get alert configuration for a pipeline."""
        try:
            rules = self.db_session.query(AlertRule).filter(
                AlertRule.pipeline_id == pipeline_id
            ).all()
            
            return [{
                'name': rule.name,
                'metric': rule.metric,
                'condition': rule.condition,
                'threshold': rule.threshold,
                'severity': rule.severity,
                'enabled': rule.enabled,
                'notification_channels': rule.notification_channels
            } for rule in rules]
        except Exception as e:
            self.logger.error(f"Error fetching alert config: {str(e)}")
            raise

    def update_alert_config(self, pipeline_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update alert configuration."""
        try:
            # Delete existing rules
            self.db_session.query(AlertRule).filter(
                AlertRule.pipeline_id == pipeline_id
            ).delete()
            
            # Create new rules
            rules = []
            for rule_config in config['rules']:
                rule = AlertRule(
                    pipeline_id=pipeline_id,
                    name=rule_config['name'],
                    metric=rule_config['metric'],
                    condition=rule_config['condition'],
                    threshold=rule_config['threshold'],
                    severity=rule_config['severity'],
                    enabled=rule_config.get('enabled', True),
                    notification_channels=rule_config.get('notification_channels', [])
                )
                rules.append(rule)
            
            self.db_session.add_all(rules)
            self.db_session.commit()
            
            return self.get_alert_config(pipeline_id)
        except Exception as e:
            self.logger.error(f"Error updating alert config: {str(e)}")
            self.db_session.rollback()
            raise

    def get_alert_history(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Get alert history for a pipeline."""
        try:
            alerts = self.db_session.query(Alert).filter(
                Alert.pipeline_id == pipeline_id
            ).order_by(Alert.created_at.desc()).all()
            
            return [{
                'type': alert.type,
                'severity': alert.severity,
                'message': alert.message,
                'status': alert.status,
                'created_at': alert.created_at.isoformat(),
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'metadata': alert.metadata
            } for alert in alerts]
        except Exception as e:
            self.logger.error(f"Error fetching alert history: {str(e)}")
            raise

    def get_resource_usage(self, pipeline_id: str) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Store metrics
            usage = ResourceUsage(
                pipeline_id=pipeline_id,
                cpu_usage=cpu_percent,
                memory_usage=memory.percent,
                disk_usage=disk.percent,
                network_in=0,  # Would need network monitoring implementation
                network_out=0,
                timestamp=datetime.utcnow()
            )
            
            self.db_session.add(usage)
            self.db_session.commit()
            
            return {
                'cpu': {
                    'usage_percent': cpu_percent,
                },
                'memory': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'usage_percent': memory.percent
                },
                'disk': {
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
                    'usage_percent': disk.percent
                },
                'timestamp': usage.timestamp.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting resource usage: {str(e)}")
            self.db_session.rollback()
            raise

    def get_aggregated_metrics(self, pipeline_id: str) -> Dict[str, Any]:
        """Get aggregated metrics for the last 24 hours."""
        try:
            start_time = datetime.utcnow() - timedelta(hours=24)
            metrics = self.db_session.query(MonitoringMetric).filter(
                MonitoringMetric.pipeline_id == pipeline_id,
                MonitoringMetric.timestamp >= start_time
            ).all()
            
            # Aggregate metrics by type
            aggregated = {}
            for metric in metrics:
                if metric.type not in aggregated:
                    aggregated[metric.type] = []
                aggregated[metric.type].append(metric.value)
            
            # Calculate statistics
            result = {}
            for metric_type, values in aggregated.items():
                result[metric_type] = {
                    'min': min(values),
                    'max': max(values),
                    'avg': sum(values) / len(values),
                    'count': len(values)
                }
                
            return result
        except Exception as e:
            self.logger.error(f"Error calculating aggregated metrics: {str(e)}")
            raise

    def _calculate_overall_health(self, checks: List[HealthCheck]) -> str:
        """Calculate overall health status from component checks."""
        if not checks:
            return 'unknown'
            
        status_priority = {
            'healthy': 0,
            'degraded': 1,
            'failing': 2
        }
        
        highest_priority = max(
            status_priority.get(check.status, 3)
            for check in checks
        )
        
        for status, priority in status_priority.items():
            if priority == highest_priority:
                return status
                
        return 'unknown'