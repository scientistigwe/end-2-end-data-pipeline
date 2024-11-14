#!/usr/bin/env python
"""
Script to generate encryption key and update .env file
Usage: python generate_key.py
"""

import base64
from cryptography.fernet import Fernet
import os
from pathlib import Path


def generate_encryption_key():
    """Generate a new Fernet encryption key and save it to .env file"""
    # Generate the key
    key = Fernet.generate_key()
    encoded_key = base64.b64encode(key).decode()

    env_path = Path('utils/.env')

    if env_path.exists():
        # Read existing .env content
        with open(env_path, 'r') as f:
            lines = f.readlines()

        # Update or add ENCRYPTION_KEY
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith('ENCRYPTION_KEY='):
                lines[i] = f'ENCRYPTION_KEY={encoded_key}\n'
                key_found = True
                break

        if not key_found:
            lines.append(f'\nENCRYPTION_KEY={encoded_key}\n')

        # Write back to .env
        with open(env_path, 'w') as f:
            f.writelines(lines)
    else:
        # Create new .env file with encryption key
        with open(env_path, 'w') as f:
            f.write(f'ENCRYPTION_KEY={encoded_key}\n')

    print(f"Encryption key generated and saved to .env file")
    print(f"Key: {encoded_key}")
    return encoded_key


if __name__ == '__main__':
    generate_encryption_key()