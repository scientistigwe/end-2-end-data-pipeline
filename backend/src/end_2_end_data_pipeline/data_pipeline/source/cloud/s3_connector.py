# s3_connector.py

import boto3
import logging
from typing import Optional
from botocore.config import Config
from botocore.exceptions import ClientError, BotoCoreError
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import CloudConnectionError

logger = logging.getLogger(__name__)


class S3Connector:
    VALID_REGIONS = [
        'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
        'eu-west-1', 'eu-west-2', 'eu-central-1',
        'ap-northeast-1', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
        'sa-east-1'
    ]
    def __init__(
            self,
            aws_access_key: str,
            aws_secret_key: str,
            region_name: str,
            session=None,
            config=None
    ):
        """Initialize S3 connector with AWS credentials and optional session/config."""
        if not self._validate_region(region_name):
            raise ValueError(f"Invalid AWS region: {region_name}")
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.region_name = region_name
        self.session = session
        self.config = config
        self.s3_client = None
        self.s3_resource = None
        try:
            self._initialize_connection()
        except (ClientError, Exception) as e:
            logger.error(f"Failed to initialize S3 connection: {e}")
            raise CloudConnectionError(f"Failed to establish S3 connection: {e}")
    def _validate_region(self, region_name: str) -> bool:
        """Validate AWS region name."""
        return region_name in self.VALID_REGIONS

    def _initialize_connection(self) -> None:
        """Initialize the S3 client and resource."""
        if self.session is None:
            self.session = boto3.Session(
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.region_name
            )

        self.s3_client = (
            self.session.client('s3', config=self.config)
            if self.config
            else self.session.client('s3')
        )
        self.s3_resource = self.session.resource('s3')

        # Test connection
        self.s3_client.list_buckets()

    def upload_file(self, bucket_name: str, key: str, data: bytes) -> None:
            """Upload data to S3 bucket."""
            if not isinstance(data, bytes):
                raise AttributeError("Data must be bytes")
            try:
                self.s3_client.put_object(Bucket=bucket_name, Key=key, Body=data)
                logger.info(f"Successfully uploaded to s3://{bucket_name}/{key}")
            except Exception as e:
                logger.error(f"Upload failed: {e}")
                raise CloudConnectionError(f"Failed to upload to S3: {e}")

    def download_file(self, bucket_name: str, key: str) -> bytes:
        """Download data from S3 bucket."""
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise CloudConnectionError(f"Failed to download from S3: {e}")

    def close(self) -> None:
        """Close S3 connections."""
        try:
            if self.s3_client:
                self.s3_client.close()
            if self.s3_resource:
                self.s3_resource.meta.client.close()
        finally:
            self.s3_client = None
            self.s3_resource = None