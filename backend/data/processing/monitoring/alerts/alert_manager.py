# backend/data/processing/monitoring/alerts/alert_manager.py
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Centralized Alert Management System

    Responsibilities:
    - Process and categorize system alerts
    - Manage alert lifecycle
    - Provide alert aggregation and reporting
    """

    def __init__(self, max_retention_hours: int = 24):
        """
        Initialize AlertManager with configurable alert retention

        Args:
            max_retention_hours: Maximum hours to retain processed alerts
        """
        self._processed_alerts: List[Dict[str, Any]] = []
        self._max_retention_hours = max_retention_hours

    def process_alert(
            self,
            pipeline_id: Optional[str],
            alert_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive alert processing workflow

        Args:
            pipeline_id: Optional associated pipeline identifier
            alert_details: Detailed alert information

        Returns:
            Processed alert with additional metadata
        """
        try:
            # Validate and enrich alert details
            processed_alert = self._validate_alert(alert_details)

            # Add tracking metadata
            processed_alert.update({
                'id': str(uuid.uuid4()),
                'pipeline_id': pipeline_id,
                'processed_at': datetime.now().isoformat(),
                'status': 'processed'
            })

            # Store processed alert
            self._processed_alerts.append(processed_alert)

            # Cleanup old alerts
            self._cleanup_alerts()

            # Log the alert
            self._log_alert(processed_alert)

            return processed_alert

        except Exception as e:
            logger.error(f"Alert processing failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'original_details': alert_details
            }

    def _validate_alert(self, alert_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and standardize alert details

        Args:
            alert_details: Raw alert information

        Returns:
            Validated and standardized alert
        """
        # Implement comprehensive alert validation
        # Add type checking, required field validation, etc.
        required_keys = ['type', 'severity', 'message']
        for key in required_keys:
            if key not in alert_details:
                raise ValueError(f"Missing required alert field: {key}")

        # Standardize severity levels
        severity_mapping = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }
        alert_details['severity_level'] = severity_mapping.get(
            alert_details.get('severity', 'low').lower(), 1
        )

        return alert_details

    def _log_alert(self, alert: Dict[str, Any]) -> None:
        """
        Log processed alert to system logs

        Args:
            alert: Processed alert details
        """
        log_method = {
            1: logger.info,
            2: logger.warning,
            3: logger.error,
            4: logger.critical
        }.get(alert.get('severity_level', 1), logger.info)

        log_method(f"Alert Processed: {alert}")

    def _cleanup_alerts(self) -> None:
        """Remove alerts older than retention period"""
        current_time = datetime.now()
        self._processed_alerts = [
            alert for alert in self._processed_alerts
            if (current_time - datetime.fromisoformat(alert.get('processed_at', current_time.isoformat())))
               < timedelta(hours=self._max_retention_hours)
        ]

    def get_recent_alerts(
            self,
            limit: int = 100,
            severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent alerts with optional filtering

        Args:
            limit: Maximum number of alerts to return
            severity: Optional severity level filter

        Returns:
            List of recent alerts
        """
        filtered_alerts = self._processed_alerts

        if severity:
            filtered_alerts = [
                alert for alert in filtered_alerts
                if alert.get('severity', '').lower() == severity.lower()
            ]

        return filtered_alerts[:limit]

    def clear_processed_alerts(self) -> None:
        """Clear all processed alerts"""
        self._processed_alerts.clear()