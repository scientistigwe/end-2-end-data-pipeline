import logging
from cryptography.fernet import Fernet
import os
from typing import Union
from data_pipeline.exceptions import DataEncodingError

logger = logging.getLogger(__name__)

class DataSecurityManager:
    """Handles data encryption and decryption for secure data transmission"""

    def __init__(self, db_validator):
        """Initialize the security manager with encryption key"""
        self.db_validator = db_validator
        is_valid, error_msg = self.db_validator.validate_encryption_key()
        if not is_valid:
            raise ValueError(f"Failed to initialize security manager: {error_msg}")

        self._fernet = Fernet(os.environ['ENCRYPTION_KEY'].encode())

    def encrypt_data(self, data: Union[str, bytes]) -> bytes:
        """
        Encrypt data for secure transmission

        Args:
            data: Data to encrypt (string or bytes)

        Returns:
            Encrypted data as bytes

        Raises:
            ValueError: If data is None or empty
            DataEncodingError: If encryption fails
        """
        if data is None:
            raise ValueError("Cannot encrypt None data")

        try:
            if isinstance(data, str):
                data = data.encode()
            return self._fernet.encrypt(data)
        except Exception as e:
            raise DataEncodingError(f"Encryption failed: {str(e)}")

    def decrypt_data(self, encrypted_data: bytes) -> str:
        """
        Decrypt encrypted data

        Args:
            encrypted_data: Encrypted data bytes

        Returns:
            Decrypted data as string

        Raises:
            ValueError: If encrypted_data is None
            DataEncodingError: If decryption fails
        """
        if encrypted_data is None:
            raise ValueError("Cannot decrypt None data")

        try:
            decrypted = self._fernet.decrypt(encrypted_data)
            return decrypted.decode()
        except Exception as e:
            raise DataEncodingError(f"Decryption failed: {str(e)}")