import pytest
import os
from data_pipeline.source.database.db_config import DatabaseConfig, EncryptionError

class TestDatabaseConfig:
    @pytest.fixture
    def sample_config_dict(self):
        return {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_password'
        }

    @pytest.fixture
    def setup_encryption_key(self):
        key = DatabaseConfig.generate_encryption_key()
        os.environ['ENCRYPTION_KEY'] = key.decode()
        yield key
        if 'ENCRYPTION_KEY' in os.environ:
            del os.environ['ENCRYPTION_KEY']

    def test_encryption_key_generation(self):
        key = DatabaseConfig.generate_encryption_key()
        assert isinstance(key, bytes)
        assert len(key) > 0

    def test_config_creation_with_encryption(self, sample_config_dict, setup_encryption_key):
        config = DatabaseConfig.from_dict(sample_config_dict)
        assert config.host == 'localhost'
        assert config.port == 5432
        # Ensure password is encrypted
        assert config.password != 'test_password'

        # Test decryption
        decrypted_config = config.to_dict(decrypt=True)
        assert decrypted_config['password'] == 'test_password'

    def test_connection_config_generation(self, sample_config_dict, setup_encryption_key):
        config = DatabaseConfig.from_dict(sample_config_dict)
        conn_config = config.get_connection_config()
        assert conn_config['user'] == 'test_user'
        assert conn_config['password'] == 'test_password'
        assert conn_config['host'] == 'localhost'

    def test_missing_encryption_key(self, sample_config_dict):
        if 'ENCRYPTION_KEY' in os.environ:
            del os.environ['ENCRYPTION_KEY']
        with pytest.raises(EncryptionError):
            DatabaseConfig.from_dict(sample_config_dict)