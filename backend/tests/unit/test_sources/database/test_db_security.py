import pytest
from backend.backend.data_pipeline.source.database.db_security import DataSecurityManager


@pytest.fixture
def security_manager():
    return DataSecurityManager()


def test_setup_encryption(security_manager):
    security_manager.setup_encryption()
    assert hasattr(security_manager, '_fernet')


def test_encrypt_decrypt(security_manager):
    original_data = [
        {'id': 1, 'table_name': 'users', 'data_type': 'postgresql', 'last_updated': '2023-01-01 12:00:00.123456'}
    ]

    try:
        encrypted_data = security_manager.encrypt(original_data)
        decrypted_data = security_manager.decrypt(encrypted_data)

        assert isinstance(decrypted_data, list)
        assert len(decrypted_data) == 1
        assert decrypted_data[0]['id'] == 1
    except Exception as e:
        pytest.fail(f"Encryption/Decryption failed: {str(e)}")
