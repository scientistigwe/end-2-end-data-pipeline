# test_file_validator.py
import pytest
import io
from unittest.mock import Mock, patch
from backend.data_pipeline.source.file.file_validator import FileValidator
from backend.data_pipeline.source.file.file_config import Config


@pytest.fixture
def mock_file():
    class MockFile:
        def __init__(self, content, filename, content_type):
            self.content = content.encode('utf-8') if isinstance(content, str) else content
            self.filename = filename
            self.content_type = content_type
            self._position = 0

        def read(self):
            return self.content

        def seek(self, position):
            self._position = position

        @property
        def stream(self):
            return io.BytesIO(self.content)

    return MockFile


class TestFileValidator:
    """Test suite for FileValidator class"""

    def test_valid_file_format(self, mock_file):
        """Test validation of allowed file formats"""
        file = mock_file("test", "test.csv", "text/csv")
        validator = FileValidator()
        is_valid, message = validator.validate_file_format(file)
        assert is_valid
        assert "valid" in message.lower()

    def test_invalid_file_format(self, mock_file):
        """Test rejection of disallowed file formats"""
        file = mock_file("test", "test.exe", "application/exe")
        validator = FileValidator()
        is_valid, message = validator.validate_file_format(file)
        assert not is_valid
        assert "invalid" in message.lower()

    @pytest.mark.parametrize("size_mb,expected_valid", [
        (1, True),  # Small file
        (Config.FILE_SIZE_THRESHOLD_MB - 1, True),  # Just under limit
        (Config.FILE_SIZE_THRESHOLD_MB + 1, False),  # Just over limit
        (100, False)  # Large file
    ])
    def test_file_size_validation(self, mock_file, size_mb, expected_valid):
        """Test file size validation with various file sizes"""
        content = b"0" * int(size_mb * 1024 * 1024)  # Create file content of specified size
        file = mock_file(content, "test.csv", "text/csv")
        validator = FileValidator()
        is_valid, message = validator.validate_file_size(file)
        assert is_valid == expected_valid

    @pytest.mark.parametrize("file_content,expected_valid", [
        ("col1,col2\n1,2", True),  # Valid CSV
        ("", False),  # Empty file
        ("col1,col2\n1,2\n,,", True),  # CSV with missing values
        ('{"key": "value"}', True),  # Valid JSON
        ('{"key": }', False),  # Invalid JSON
    ])
    def test_file_integrity(self, mock_file, file_content, expected_valid):
        """Test file integrity validation for various content types"""
        file = mock_file(file_content, "test.csv", "text/csv")
        validator = FileValidator()
        is_valid, message = validator.validate_file_integrity(file)
        assert is_valid == expected_valid

    def test_security_validation(self, mock_file):
        """Test security validation for potentially malicious content"""
        # Test various potentially malicious content
        test_cases = [
            ("=CMD('del *')", "csv"),  # Formula injection
            ("DROP TABLE users;--", "csv"),  # SQL injection
            ("<script>alert('xss')</script>", "csv"),  # XSS attempt
            ("../../../etc/passwd", "csv"),  # Path traversal
        ]

        validator = FileValidator()
        for content, ext in test_cases:
            file = mock_file(content, f"test.{ext}", f"text/{ext}")
            is_valid, message = validator.validate_security(file)
            assert is_valid  # Basic check should pass but log suspicious content

    @pytest.mark.parametrize("filename,content_type,expected_valid", [
        ("test.csv", "text/csv", True),
        ("test.json", "application/json", True),
        ("test.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True),
        ("test.parquet", "application/parquet", True),
        ("test.doc", "application/msword", False),
        ("test.pdf", "application/pdf", False),
    ])
    def test_file_format_extensions(self, mock_file, filename, content_type, expected_valid):
        """Test validation of various file extensions and content types"""
        file = mock_file("test", filename, content_type)
        validator = FileValidator()
        is_valid, message = validator.validate_file_format(file)
        assert is_valid == expected_valid

    def test_concurrent_validation(self, mock_file):
        """Test validator behavior with concurrent requests"""
        import threading
        validator = FileValidator()
        results = []

        def validate_file():
            file = mock_file("test", "test.csv", "text/csv")
            is_valid, _ = validator.validate_file_format(file)
            results.append(is_valid)

        threads = [threading.Thread(target=validate_file) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert all(results)  # All validations should succeed

    def test_error_handling(self, mock_file):
        """Test error handling for corrupted or problematic files"""
        # Test with corrupted file
        corrupted_file = mock_file(b'\x00\x01\x02\x03', "test.csv", "text/csv")
        validator = FileValidator()
        is_valid, message = validator.validate_file_integrity(corrupted_file)
        assert not is_valid
        assert "error" in message.lower()

        # Test with file that raises exception during read
        class ErrorFile(Mock):
            def read(self):
                raise IOError("Read error")

        error_file = ErrorFile()
        error_file.filename = "test.csv"
        error_file.content_type = "text/csv"
        is_valid, message = validator.validate_file_integrity(error_file)
        assert not is_valid
        assert "error" in message.lower()