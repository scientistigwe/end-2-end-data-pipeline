# s3_validator.py
import boto3
from typing import Tuple, Dict, Any
import logging
from botocore.exceptions import ClientError
from .s3_config import Config

logger = logging.getLogger(__name__)


class S3Validator:
    """S3 validation utilities"""

    @staticmethod
    def validate_credentials(credentials: Dict[str, Any], region: str) -> Tuple[bool, str]:
        """Validate AWS credentials"""
        try:
            session = boto3.Session(
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key'],
                region_name=region
            )

            # Test with a simple operation
            s3 = session.client('s3')
            s3.list_buckets()

            return True, "AWS credentials validated successfully"
        except ClientError as e:
            return False, f"AWS credential validation failed: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"

    @staticmethod
    def validate_bucket_access(s3_client, bucket: str) -> Tuple[bool, str]:
        """Validate bucket access permissions"""
        try:
            s3_client.head_bucket(Bucket=bucket)
            return True, "Bucket access verified"
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == '404':
                return False, f"Bucket {bucket} not found"
            elif error_code == '403':
                return False, f"Access denied to bucket {bucket}"
            return False, f"Bucket access error: {str(e)}"

    @staticmethod
    def validate_object_format(key: str) -> Tuple[bool, str]:
        """Validate S3 object format"""
        ext = key.split('.')[-1].lower() if '.' in key else None
        if not ext:
            return False, "No file extension found"
        if ext not in Config.SUPPORTED_FORMATS:
            return False, f"Unsupported format: {ext}. Supported formats: {', '.join(Config.SUPPORTED_FORMATS)}"
        return True, "File format is supported"

    @staticmethod
    def validate_object_size(s3_client, bucket: str, key: str) -> Tuple[bool, str]:
        """Validate S3 object size"""
        try:
            response = s3_client.head_object(Bucket=bucket, Key=key)
            size = response['ContentLength']
            if size > Config.MAX_FILE_SIZE:
                return False, f"File size {size} bytes exceeds maximum allowed size of {Config.MAX_FILE_SIZE} bytes"
            return True, "File size is within limits"
        except ClientError as e:
            return False, f"Size validation error: {str(e)}"


