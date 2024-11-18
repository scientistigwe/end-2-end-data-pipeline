# s3_data_manager.py

import pandas as pd
from io import BytesIO
from datetime import datetime
import ntplib
from typing import Optional
from botocore.config import Config
from backend.data_pipeline.exceptions import (
    CloudConnectionError, CloudQueryError, DataValidationError
)
import logging
from backend.data_pipeline.source.cloud.s3_connector import S3Connector

# Set up logging for the script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TimeSync:
    """Handles time synchronization with NTP servers."""

    def __init__(self):
        self.ntp_client = ntplib.NTPClient()

    def get_ntp_time(self) -> datetime:
        """Get current time from NTP server."""
        try:
            response = self.ntp_client.request('pool.ntp.org', timeout=5)
            return datetime.fromtimestamp(response.tx_time)
        except Exception as e:
            logger.warning(f"NTP time sync failed: {e}")
            return datetime.utcnow()


class S3DataManager:
    def __init__(self, aws_access_key: str, aws_secret_key: str, region_name: str):
        """Initialize S3 data manager with time synchronization."""
        self.time_sync = TimeSync()

        # Configure with time synchronization
        config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3},
            connect_timeout=5,
            read_timeout=5
        )

        self.s3_connector = S3Connector(
            aws_access_key,
            aws_secret_key,
            region_name,
            config=config
        )

    def validate_and_load(self, bucket_name: str, key: str, data_format: str = 'csv') -> pd.DataFrame:
        """Load and validate data from S3."""
        try:
            # Sync time before S3 operations
            _ = self.time_sync.get_ntp_time()

            raw_data = self.s3_connector.download_file(bucket_name, key)
            data = self._parse_data(raw_data, data_format)
            self._validate_data(data)
            return data
        except ValueError as e:
            raise ValueError(str(e))
        except DataValidationError as e:
            raise DataValidationError(str(e))
        except Exception as e:
            logger.error(f"Data load failed: {e}")
            raise CloudQueryError(str(e))

    def upload_dataframe(self, bucket_name: str, key: str, data: pd.DataFrame,
                         data_format: str = 'csv') -> None:
        """Upload DataFrame to S3."""
        if data_format not in ['csv', 'json']:
            raise ValueError(f"Unsupported format: {data_format}")

        try:
            # Sync time before S3 operations
            _ = self.time_sync.get_ntp_time()

            buffer = BytesIO()
            if data_format == 'csv':
                data.to_csv(buffer, index=False)
            else:  # data_format == 'json'
                data.to_json(buffer)

            buffer.seek(0)
            self.s3_connector.upload_file(bucket_name, key, buffer.getvalue())
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise CloudQueryError(str(e))

    def _parse_data(self, raw_data: bytes, data_format: str) -> pd.DataFrame:
        """Parse raw data into DataFrame."""
        if data_format not in ['csv', 'json']:
            raise ValueError(f"Unsupported format: {data_format}")

        buffer = BytesIO(raw_data)
        try:
            if data_format == 'csv':
                df = pd.read_csv(buffer)
            else:  # data_format == 'json'
                df = pd.read_json(buffer)

            if df.empty:
                raise DataValidationError("Empty DataFrame received")
            return df
        except pd.errors.EmptyDataError:
            raise DataValidationError("Empty DataFrame received")

    def _validate_data(self, data: pd.DataFrame) -> None:
        """Validate loaded data."""
        if data.empty:
            raise DataValidationError("Empty DataFrame received")

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 's3_connector'):
            self.s3_connector.close()
