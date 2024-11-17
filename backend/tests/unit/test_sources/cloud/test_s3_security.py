import pytest
from unittest.mock import patch
from backend.backend.data_pipeline.source.cloud.s3_security import DataSecurityManager


@pytest.fixture
def security_manager():
    with patch('backend.backend.data_pipeline.source.cloud.s3_security.os.environ', {'ENCRYPTION_KEY': 'mock_key'}):
        return DataSecurityManager()

@patch('backend.backend.data_pipeline.source.cloud.s3_security.Fernet.encrypt')
def test_encrypt_data_string_success(mock_encrypt, security_manager):
    mock_encrypt.return_value = b'encrypted_data'
    data = 'test string'
    result = security_manager.encrypt_data(data)
    assert b'encrypted_data' in result

def test_encrypt_data_none(security_manager):
    with pytest.raises(ValueError):
        security_manager.encrypt_data(None)

@patch('backend.backend.data_pipeline.source.cloud.s3_security.Fernet.decrypt')
def test_decrypt_data_success(mock_decrypt, security_manager):
    mock_decrypt.return_value = b'test string'
    encrypted_data = b'string:mock_encrypted_data'
    result = security_manager.decrypt_data(encrypted_data)
    assert result == 'test string'

def test_decrypt_data_empty(security_manager):
    with pytest.raises(ValueError):
        security_manager.decrypt_data(b'')
