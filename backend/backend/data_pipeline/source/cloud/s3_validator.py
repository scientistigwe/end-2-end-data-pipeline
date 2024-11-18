import logging
from typing import Tuple, Optional
from backend.data_pipeline.exceptions import CloudConnectionError

logger = logging.getLogger(__name__)


class S3Validator:
    def __init__(self, s3_connector):
        """
        Initialize the S3 validator with an S3Connector instance.

        Args:
            s3_connector: An initialized S3Connector instance
        """
        self.s3_connector = s3_connector
        self._validated = False  # Flag to prevent multiple calls

    def validate_connection(self) -> Tuple[bool, Optional[str]]:
        """
        Validate S3 connection by checking if buckets can be listed.

        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - Boolean indicating if validation was successful
                - Error message string if validation failed, None otherwise
        """
        if self._validated:
            logger.info("S3 connection already validated.")
            return True, None  # Early exit if already validated

        try:
            response = self.s3_connector.s3_client.list_buckets()
            buckets = response.get('Buckets', [])

            if not buckets:
                logger.warning("No buckets found during validation.")

            logger.info("S3 connection validated successfully.")
            self._validated = True  # Mark as validated
            return True, None

        except CloudConnectionError as e:
            logger.error(f"S3 connection validation failed: {str(e)}")
            return False, str(e)
        except Exception as e:
            logger.error(f"S3 validation error: {str(e)}")
            return False, str(e)