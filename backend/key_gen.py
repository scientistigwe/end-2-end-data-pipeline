#!/usr/bin/env python
"""
Script to generate encryption, security, and JWT keys for .env file
Usage: python generate_keys.py
"""

import base64
import secrets
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_encryption_key():
    """Generate a new Fernet encryption key"""
    key = Fernet.generate_key()
    return base64.b64encode(key).decode()


def generate_secret_key():
    """Generate a secure random secret key"""
    return secrets.token_hex(32)


def generate_jwt_keys():
    """Generate JWT private and public keys"""
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )

    # Get the public key
    public_key = private_key.public_key()

    # Serialize private key
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Serialize public key
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    return {
        'private': pem_private.decode().strip(),
        'public': pem_public.decode().strip()
    }


def update_env_file(env_path):
    """Update .env file with generated keys"""
    # Read existing .env content
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Prepare new lines
    new_lines = []
    keys_to_generate = {
        'SECRET_KEY': generate_secret_key,
        'JWT_SECRET_KEY': generate_secret_key,
        'ENCRYPTION_KEY': generate_encryption_key,
    }

    # JWT key generation is special case
    jwt_keys = generate_jwt_keys()

    for line in lines:
        stripped = line.strip()

        # Handle SECRET_KEY type keys
        for key_name, generator in keys_to_generate.items():
            if stripped.startswith(f'{key_name}=') and (stripped.endswith('=') or 'placeholder' in stripped.lower()):
                line = f'{key_name}={generator()}\n'
                break

        # Special handling for JWT keys
        if stripped.startswith('JWT_PRIVATE_KEY=') and (stripped.endswith('=') or 'placeholder' in stripped.lower()):
            line = f'JWT_PRIVATE_KEY={jwt_keys["private"]}\n'

        if stripped.startswith('JWT_PUBLIC_KEY=') and (stripped.endswith('=') or 'placeholder' in stripped.lower()):
            line = f'JWT_PUBLIC_KEY={jwt_keys["public"]}\n'

        new_lines.append(line)

    # Write back to .env
    with open(env_path, 'w') as f:
        f.writelines(new_lines)

    print(f"Keys generated and saved to {env_path}")


def main():
    # Attempt to find .env file
    possible_paths = [
        Path('utils/.env'),
        Path('backend/backend/.env'),
        Path('.env'),
        Path('../.env'),
        Path('../../.env')
    ]

    for path in possible_paths:
        if path.exists():
            update_env_file(path)
            return

    print("No .env file found. Please specify the correct path.")


if __name__ == '__main__':
    main()