# backend/core/utils/encryption.py

import os
import base64
import json
from typing import Any, Union, Dict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import padding


class AESEncryption:
    """Handles AES encryption for sensitive data"""

    def __init__(self):
        # Get or generate key
        self.key = self._get_or_generate_key()
        self.fernet = Fernet(self.key)

        # Initialize padding
        self.padder = padding.PKCS7(128).padder()
        self.unpadder = padding.PKCS7(128).unpadder()

    def _get_or_generate_key(self) -> bytes:
        """Get existing key or generate new one"""
        key = os.getenv('ENCRYPTION_KEY')
        if key:
            return base64.b64decode(key)

        # Generate new key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=os.urandom(16),
            iterations=100000,
        )
        key = base64.b64encode(kdf.derive(os.urandom(32)))
        return key

    def encrypt(self, data: Union[bytes, str, Dict]) -> bytes:
        """
        Encrypt data

        Args:
            data: Data to encrypt (bytes, string, or dictionary)

        Returns:
            Encrypted bytes
        """
        try:
            # Convert data to bytes if needed
            if isinstance(data, str):
                data = data.encode()
            elif isinstance(data, dict):
                data = json.dumps(data).encode()

            # Pad data
            padded_data = self.padder.update(data) + self.padder.finalize()

            # Encrypt
            return self.fernet.encrypt(padded_data)

        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")

    def decrypt(self, encrypted_data: bytes) -> Union[bytes, Dict]:
        """
        Decrypt data

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted data
        """
        try:
            # Decrypt
            decrypted_data = self.fernet.decrypt(encrypted_data)

            # Unpad
            unpadded_data = self.unpadder.update(decrypted_data) + self.unpadder.finalize()

            # Try to parse as JSON
            try:
                return json.loads(unpadded_data)
            except:
                return unpadded_data

        except Exception as e:
            raise EncryptionError(f"Decryption failed: {str(e)}")

    def encrypt_file(self, file_path: str, output_path: str = None) -> str:
        """
        Encrypt a file

        Args:
            file_path: Path to file to encrypt
            output_path: Optional path for encrypted file

        Returns:
            Path to encrypted file
        """
        try:
            # Default output path
            if not output_path:
                output_path = f"{file_path}.encrypted"

            # Read and encrypt file
            with open(file_path, 'rb') as f:
                data = f.read()
                encrypted_data = self.encrypt(data)

            # Write encrypted file
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)

            return output_path

        except Exception as e:
            raise EncryptionError(f"File encryption failed: {str(e)}")

    def decrypt_file(self, file_path: str, output_path: str = None) -> str:
        """
        Decrypt a file

        Args:
            file_path: Path to encrypted file
            output_path: Optional path for decrypted file

        Returns:
            Path to decrypted file
        """
        try:
            # Default output path
            if not output_path:
                output_path = file_path.replace('.encrypted', '.decrypted')

            # Read and decrypt file
            with open(file_path, 'rb') as f:
                encrypted_data = f.read()
                decrypted_data = self.decrypt(encrypted_data)

            # Write decrypted file
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)

            return output_path

        except Exception as e:
            raise EncryptionError(f"File decryption failed: {str(e)}")

    def encrypt_metadata(self, metadata: Dict[str, Any]) -> bytes:
        """
        Encrypt metadata dictionary

        Args:
            metadata: Dictionary of metadata

        Returns:
            Encrypted bytes
        """
        try:
            return self.encrypt(metadata)
        except Exception as e:
            raise EncryptionError(f"Metadata encryption failed: {str(e)}")

    def decrypt_metadata(self, encrypted_metadata: bytes) -> Dict[str, Any]:
        """
        Decrypt metadata

        Args:
            encrypted_metadata: Encrypted metadata bytes

        Returns:
            Decrypted metadata dictionary
        """
        try:
            decrypted = self.decrypt(encrypted_metadata)
            if not isinstance(decrypted, dict):
                raise ValueError("Decrypted data is not a dictionary")
            return decrypted
        except Exception as e:
            raise EncryptionError(f"Metadata decryption failed: {str(e)}")


class EncryptionError(Exception):
    """Custom exception for encryption errors"""
    pass