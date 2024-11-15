# s3_security.py

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Any, Optional
import json
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import DataEncodingError


@dataclass
class EncryptionConfig:
    key_env_var: str = "ENCRYPTION_KEY"
    encoding: str = "utf-8"
    chunk_size: int = 64 * 1024
    salt: bytes = b"data_pipeline_salt"
    iterations: int = 100000


class DataType(Enum):
    STRING = "string"
    BYTES = "bytes"
    DATAFRAME = "dataframe"
    JSON = "json"
    S3_METADATA = "s3_metadata"


class DataSecurityManager:
    def __init__(self, config: Optional[EncryptionConfig] = None):
        """Initialize security manager."""
        self.config = config or EncryptionConfig()
        self._fernet = self._initialize_encryption()

    def _initialize_encryption(self) -> Fernet:
        """Initialize encryption with key derivation."""
        key = os.environ.get(self.config.key_env_var)
        if not key:
            raise ValueError(f"Missing encryption key in {self.config.key_env_var}")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.config.salt,
            iterations=self.config.iterations,
        )

        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        return Fernet(derived_key)

    def encrypt_data(self, data: Any) -> bytes:
        """Encrypt data with type preservation."""
        if data is None:
            raise ValueError("Cannot process None data")

        data_type, prepared_data = self._prepare_data(data)
        data_bytes = (prepared_data if isinstance(prepared_data, bytes)
                      else str(prepared_data).encode(self.config.encoding))

        metadata = f"{data_type.value}:".encode(self.config.encoding)
        return metadata + self._fernet.encrypt(data_bytes)

    def decrypt_data(self, encrypted_data: bytes) -> Any:
        """Decrypt data with type restoration."""
        if not encrypted_data:
            raise ValueError("Cannot decrypt empty data")

        try:
            separator = ":".encode(self.config.encoding)
            metadata_end = encrypted_data.index(separator) + 1
            data_type = DataType(encrypted_data[:metadata_end - 1].decode())

            content = encrypted_data[metadata_end:]
            decrypted = self._fernet.decrypt(content)
            return self._restore_data(decrypted, data_type)
        except Exception as e:
            raise DataEncodingError(f"Decryption failed: {e}")

    def _prepare_data(self, data: Any) -> tuple[DataType, Any]:
        """Prepare data for encryption."""
        if isinstance(data, str):
            return DataType.STRING, data
        elif isinstance(data, bytes):
            return DataType.BYTES, data
        elif isinstance(data, pd.DataFrame):
            return DataType.DATAFRAME, data.to_json()
        elif isinstance(data, dict):
            if all(key in data for key in ('ContentType', 'Metadata')):
                return DataType.S3_METADATA, json.dumps(data)
            return DataType.JSON, json.dumps(data)
        try:
            return DataType.JSON, json.dumps(data)
        except:
            raise TypeError(f"Unsupported type: {type(data)}")

    def _restore_data(self, decrypted: bytes, data_type: DataType) -> Any:
        """Restore decrypted data to original type."""
        decoded = decrypted.decode(self.config.encoding)

        if data_type == DataType.STRING:
            return decoded
        elif data_type == DataType.BYTES:
            return decrypted
        elif data_type == DataType.DATAFRAME:
            return pd.read_json(decoded)
        elif data_type in (DataType.JSON, DataType.S3_METADATA):
            return json.loads(decoded)
        raise ValueError(f"Unknown type: {data_type}")
