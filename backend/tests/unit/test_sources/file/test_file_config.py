import pytest
from backend.backend.data_pipeline.source.file.file_config import Config


class TestConfig:
    """Test suite for Config class"""

    def test_default_values(self):
        """Test that default configuration values are set correctly"""
        config = Config()
        assert Config.FILE_SIZE_THRESHOLD_MB == 50
        assert Config.CHUNK_SIZE == 10000
        assert Config.ALLOWED_FORMATS == ['csv', 'json', 'parquet', 'xlsx']
        assert Config.ENCODING == 'utf-8'

    def test_override_values(self):
        """Test that configuration values can be overridden"""
        custom_config = Config(
            FILE_SIZE_THRESHOLD_MB=100,
            CHUNK_SIZE=5000,
            ALLOWED_FORMATS=['csv', 'json'],
            ENCODING='latin-1'
        )

        assert Config.FILE_SIZE_THRESHOLD_MB == 100
        assert Config.CHUNK_SIZE == 5000
        assert Config.ALLOWED_FORMATS == ['csv', 'json']
        assert Config.ENCODING == 'latin-1'

    def test_partial_override(self):
        """Test that only specified values are overridden"""
        original_formats = Config.ALLOWED_FORMATS.copy()
        original_encoding = Config.ENCODING

        config = Config(FILE_SIZE_THRESHOLD_MB=75)

        assert Config.FILE_SIZE_THRESHOLD_MB == 75
        assert Config.ALLOWED_FORMATS == original_formats
        assert Config.ENCODING == original_encoding

    def test_invalid_attribute_override(self):
        """Test that invalid attributes are ignored"""
        config = Config(INVALID_SETTING=100)

        assert not hasattr(Config, 'INVALID_SETTING')
        assert Config.FILE_SIZE_THRESHOLD_MB == 50  # Default value remains

    @pytest.mark.parametrize("filename,expected", [
        ('test.csv', True),
        ('data.json', True),
        ('file.parquet', True),
        ('spreadsheet.xlsx', True),
        ('document.txt', False),
        ('script.py', False),
        ('file', False),
        ('.csv', True),
        ('test.CSV', True),
        ('test.XLSX', True),
        ('test.', False),
        ('', False),
    ])
    def test_allowed_file(self, filename, expected):
        """Test file extension validation with various filenames"""
        assert Config.allowed_file(filename) == expected

    def test_allowed_file_custom_formats(self):
        """Test allowed_file with custom format list"""
        # Save original formats
        original_formats = Config.ALLOWED_FORMATS.copy()

        # Test with custom formats
        Config.ALLOWED_FORMATS = ['txt', 'dat']
        assert Config.allowed_file('test.txt') == True
        assert Config.allowed_file('data.dat') == True
        assert Config.allowed_file('test.csv') == False

        # Restore original formats
        Config.ALLOWED_FORMATS = original_formats

    def test_multiple_dots_in_filename(self):
        """Test filenames containing multiple dots"""
        assert Config.allowed_file('my.backup.csv') == True
        assert Config.allowed_file('data.2023.json') == True
        assert Config.allowed_file('test.backup.txt') == False

    def test_case_sensitivity(self):
        """Test case sensitivity in file extensions"""
        assert Config.allowed_file('TEST.CSV') == True
        assert Config.allowed_file('test.Json') == True
        assert Config.allowed_file('DATA.XLSX') == True

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Fixture to reset Config class attributes after each test"""
        yield
        Config.FILE_SIZE_THRESHOLD_MB = 50
        Config.CHUNK_SIZE = 10000
        Config.ALLOWED_FORMATS = ['csv', 'json', 'parquet', 'xlsx']
        Config.ENCODING = 'utf-8'

    def test_concurrent_configs(self):
        """Test that multiple Config instances maintain class-level settings"""
        config1 = Config(FILE_SIZE_THRESHOLD_MB=75)
        assert Config.FILE_SIZE_THRESHOLD_MB == 75

        config2 = Config(FILE_SIZE_THRESHOLD_MB=100)
        assert Config.FILE_SIZE_THRESHOLD_MB == 100
        assert getattr(config1, 'FILE_SIZE_THRESHOLD_MB') == 100

    def test_type_preservation(self):
        """Test that value types are preserved when overriding settings"""
        config = Config(
            FILE_SIZE_THRESHOLD_MB=75.5,
            CHUNK_SIZE="5000",
            ALLOWED_FORMATS=tuple(['csv', 'json'])
        )

        assert isinstance(Config.FILE_SIZE_THRESHOLD_MB, float)
        assert isinstance(Config.CHUNK_SIZE, str)
        assert isinstance(Config.ALLOWED_FORMATS, tuple)