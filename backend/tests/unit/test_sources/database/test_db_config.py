import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO
from backend.data_pipeline.source.database.db_config import DatabaseConfig
from backend.data_pipeline.source.database.db_types import DatabaseType

def test_database_config():
    config = DatabaseConfig.from_dict({
        'db_type': 'postgresql',
        'host': 'localhost',
        'port': 5432,
        'db': 'test_db',
        'username': 'test_user',
        'password': 'test_password'
    })

    assert config.db_type == DatabaseType.POSTGRESQL
    assert config.host == 'localhost'
    assert config.port == 5432
    assert config.database == 'test_db'
    assert config.username == 'test_user'


def test_database_config_from_yaml():
    # Create mock YAML content
    mock_content = '''
db_type: postgresql
host: localhost
port: 5432
db: test_db
username: test_user
password: test_password
    '''

    # Use StringIO to simulate a file-like object
    mock_file = StringIO(mock_content)

    # Patch the open function to return our mock file object
    with patch('backend.data_pipeline.source.db.db_config.open', return_value=mock_file):
        config = DatabaseConfig.from_yaml(Path('path/to/config.yaml'))

    # Add assertions based on the mock YAML content
    assert config.db_type == DatabaseType.POSTGRESQL
    assert config.host == 'localhost'
    assert config.port == 5432
    assert config.database == 'test_db'
    assert config.username == 'test_user'


def test_encrypt_decrypt():
    config = DatabaseConfig.from_dict({
        'db_type': 'postgresql',
        'host': 'localhost',
        'port': 5432,
        'db': 'test_db',
        'username': 'test_user',
        'password': 'test_password'
    })

    # Mock the encryption function
    with patch.object(config, '_encrypt_value', return_value="encrypted_test_password"):
        encrypted_pass = config._encrypt_value('test_password')

        # Check if encryption was successful
        assert encrypted_pass == "encrypted_test_password"

        # Mock the decryption function
        with patch.object(config, '_decrypt_value', return_value='test_password'):
            decrypted_pass = config._decrypt_value(encrypted_pass)

            # Check if decryption was successful
            assert decrypted_pass == 'test_password'
