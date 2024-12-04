# s3_fetcher.py
import boto3
import pandas as pd
from typing import Dict, Any, Generator, Optional
import logging
from io import BytesIO
from .s3_config import Config

logger = logging.getLogger(__name__)


class S3Fetcher:
    """Handle S3 data fetching operations"""

    def __init__(self, config: Dict[str, Any]):
        """Initialize S3 fetcher with config"""
        self.config = config
        self.s3_client = self._initialize_client()

    def _initialize_client(self):
        """Initialize S3 client with credentials"""
        creds = Config.decrypt_credentials(self.config['credentials'])
        return boto3.client(
            's3',
            aws_access_key_id=creds['aws_access_key_id'],
            aws_secret_access_key=creds['aws_secret_access_key'],
            region_name=self.config.get('region', Config.DEFAULT_REGION),
            config=boto3.Config(max_pool_connections=Config.MAX_POOL_CONNECTIONS)
        )

    def fetch_object(self, bucket: str, key: str) -> Dict[str, Any]:
        """Fetch object from S3"""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content_type = response['ContentType']

            # Convert to DataFrame based on format
            ext = key.split('.')[-1].lower()
            data = self._convert_to_dataframe(response['Body'], ext)

            return {
                'data': data,
                'metadata': {
                    'content_type': content_type,
                    'last_modified': response['LastModified'].isoformat(),
                    'size': response['ContentLength'],
                    'etag': response['ETag']
                }
            }
        except Exception as e:
            logger.error(f"S3 fetch error: {str(e)}")
            raise

    def _convert_to_dataframe(self, data: BytesIO, format: str) -> pd.DataFrame:
        """Convert S3 object to DataFrame"""
        try:
            if format == 'csv':
                return pd.read_csv(data)
            elif format == 'json':
                return pd.read_json(data)
            elif format == 'parquet':
                return pd.read_parquet(data)
            elif format == 'xlsx':
                return pd.read_excel(data)
            else:
                raise ValueError(f"Unsupported format: {format}")
        except Exception as e:
            logger.error(f"Data conversion error: {str(e)}")
            raise

    def fetch_object_stream(self, bucket: str, key: str) -> Generator[bytes, None, None]:
        """Stream large S3 objects"""
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            for chunk in response['Body'].iter_chunks(chunk_size=Config.CHUNK_SIZE):
                yield chunk
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            raise

    def list_objects(self, bucket: str, prefix: str = '') -> Dict[str, Any]:
        """List objects in S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )

            objects = [{
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat()
            } for obj in response.get('Contents', [])]

            return {
                'objects': objects,
                'count': len(objects),
                'prefix': prefix
            }
        except Exception as e:
            logger.error(f"List objects error: {str(e)}")
            raise

    def close(self):
        """Close S3 client resources"""
        try:
            self.s3_client.close()
        except Exception as e:
            logger.error(f"Close error: {str(e)}")
            raise