"""
Utility for managing encryption keys
"""
import base64
from cryptography.fernet import Fernet
import os
from typing import Optional
from pathlib import Path


class KeyManager:
    """Manages encryption keys for the data pipeline"""

    def __init__(self, env_path: str = '.env'):
        self.env_path = Path(env_path)

    def generate_key(self, force: bool = False) -> str:
        """
        Generate a new encryption key

        Args:
            force: If True, overwrites existing key

        Returns:
            Base64 encoded key string
        """
        if not force and self._get_existing_key():
            raise ValueError("Encryption key already exists. Use force=True to overwrite")

        key = Fernet.generate_key()
        encoded_key = base64.b64encode(key).decode()
        self._save_key(encoded_key)
        return encoded_key

    def _get_existing_key(self) -> Optional[str]:
        """Get existing key from .env file"""
        if not self.env_path.exists():
            return None

        with open(self.env_path, 'r') as f:
            for line in f:
                if line.startswith('ENCRYPTION_KEY='):
                    return line.split('=')[1].strip()
        return None

    def _save_key(self, key: str) -> None:
        """Save key to .env file"""
        if self.env_path.exists():
            with open(self.env_path, 'r') as f:
                lines = f.readlines()

            # Update or add key
            key_found = False
            for i, line in enumerate(lines):
                if line.startswith('ENCRYPTION_KEY='):
                    lines[i] = f'ENCRYPTION_KEY={key}\n'
                    key_found = True
                    break

            if not key_found:
                lines.append(f'\nENCRYPTION_KEY={key}\n')

            with open(self.env_path, 'w') as f:
                f.writelines(lines)
        else:
            with open(self.env_path, 'w') as f:
                f.write(f'ENCRYPTION_KEY={key}\n')

    def validate_key(self, key: str) -> bool:
        """
        Validate if a key is properly formatted

        Args:
            key: Base64 encoded key string

        Returns:
            True if key is valid
        """
        try:
            decoded = base64.b64decode(key)
            Fernet(decoded)
            return True
        except Exception:
            return False


def setup_encryption():
    """Interactive setup for encryption key"""
    manager = KeyManager()

    try:
        existing_key = manager._get_existing_key()
        if existing_key:
            print("Existing encryption key found.")
            choice = input("Do you want to generate a new key? (y/N): ")
            if choice.lower() != 'y':
                print("Keeping existing key.")
                return existing_key

        key = manager.generate_key(force=True)
        print("New encryption key generated successfully.")
        print(f"Key: {key}")
        print("\nThis key has been saved to your .env file.")
        print("Make sure to back up this key securely!")
        return key

    except Exception as e:
        print(f"Error setting up encryption: {str(e)}")
        return None


if __name__ == '__main__':
    setup_encryption()