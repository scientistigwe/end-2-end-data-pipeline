#
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class JSONExporter:
    """
    JSON Metrics Export and Persistent Storage

    Responsibilities:
    - Export metrics to JSON format
    - Manage JSON log files
    - Provide configurable export options
    """

    def __init__(
        self,
        export_directory: Optional[str] = None,
        max_files: int = 10,
        max_file_size_mb: int = 50
    ):
        """
        Initialize JSON exporter with storage configuration

        Args:
            export_directory: Directory for JSON export files
            max_files: Maximum number of retained export files
            max_file_size_mb: Maximum size of individual export files
        """
        self.export_directory = export_directory or os.path.join(os.getcwd(), 'metrics_logs')
        self.max_files = max_files
        self.max_file_size_mb = max_file_size_mb

        # Ensure export directory exists
        os.makedirs(self.export_directory, exist_ok=True)

    def export(self, metrics: Dict[str, Any]) -> str:
        """
        Export metrics to a JSON file

        Args:
            metrics: Comprehensive metrics dictionary

        Returns:
            Path to exported JSON file
        """
        try:
            # Prepare export metadata
            export_filename = self._generate_filename()
            export_path = os.path.join(self.export_directory, export_filename)

            # Write metrics to file
            with open(export_path, 'w') as f:
                json.dump(metrics, f, indent=2)

            # Manage file rotation
            self._manage_file_rotation()

            logger.info(f"Metrics exported to {export_path}")
            return export_path

        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            raise

    def _generate_filename(self) -> str:
        """
        Generate unique filename for metrics export

        Returns:
            Formatted filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"metrics_export_{timestamp}.json"

    def _manage_file_rotation(self) -> None:
        """
        Manage export files to prevent excessive storage usage
        """
        try:
            # List and sort export files
            files = sorted(
                [f for f in os.listdir(self.export_directory) if f.startswith('metrics_export_')],
                reverse=True
            )

            # Remove excess files
            for file in files[self.max_files:]:
                os.remove(os.path.join(self.export_directory, file))

            # Check file sizes
            for file in files[:self.max_files]:
                file_path = os.path.join(self.export_directory, file)
                if os.path.getsize(file_path) > self.max_file_size_mb * 1024 * 1024:
                    os.remove(file_path)

        except Exception as e:
            logger.warning(f"File rotation error: {e}")