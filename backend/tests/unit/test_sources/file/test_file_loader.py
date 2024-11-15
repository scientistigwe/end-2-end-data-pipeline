import pytest
from unittest.mock import patch, mock_open
import pandas as pd
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.config import Config
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader import FileLoader

# Mock data and fixtures
MOCK_DATA = {
    'csv': "column1,column2\nvalue1,value2",
    'dataframe': pd.DataFrame({'column1': ['value1'], 'column2': ['value2']}),
    'validation_report': {
        'quality_gauge': 95,
        'validation_results': {
            'completeness': {'valid': True, 'error': None},
            'required_columns': {'valid': True, 'error': None}
        }
    },
    'failed_validation_report': {
        'quality_gauge': 85,
        'validation_results': {
            'completeness': {'valid': False, 'error': 'Missing data'},
            'required_columns': {'valid': True, 'error': None}
        }
    }
}


@pytest.fixture
def mock_file_system():
    """Mock file system operations."""
    with patch('os.path.exists') as mock_exists, \
            patch('os.path.getsize') as mock_size, \
            patch('builtins.open', mock_open(read_data=MOCK_DATA['csv'])):
        mock_exists.return_value = True
        mock_size.return_value = 1024 * 1024  # 1MB
        yield {'exists': mock_exists, 'size': mock_size}


@pytest.fixture
def mock_validator():
    """Mock FileValidator class."""
    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader.FileValidator') as MockValidator:
        instance = MockValidator.return_value
        instance.validate_file.return_value = MOCK_DATA['validation_report']
        instance.validate_completeness.return_value = (True, None)
        yield instance


@pytest.fixture
def file_loader(mock_file_system, mock_validator):
    """Create FileLoader instance with mocked dependencies."""
    with patch('pandas.read_csv', return_value=MOCK_DATA['dataframe']):
        loader = FileLoader(
            file_path="test_files/valid_data.csv",
            required_columns=["column1", "column2"]
        )
        return loader


class TestFileLoader:
    """Test suite for FileLoader class."""

    def test_initialization(self, mock_file_system):
        """Test FileLoader initialization."""
        with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader.FileValidator') as MockValidator:
            loader = FileLoader("test.csv", ["col1", "col2"])
            assert loader.file_path == "test.csv"
            assert loader.required_columns == ["col1", "col2"]
            assert loader.file_size_mb == 1.0
            MockValidator.assert_called_once_with(required_columns=["col1", "col2"])

    def test_initialization_file_not_found(self):
        """Test initialization with non-existent file."""
        with patch('os.path.exists', return_value=False):
            with pytest.raises(FileNotFoundError):
                FileLoader("nonexistent.csv", ["col1", "col2"])

    @pytest.mark.parametrize("file_ext,reader_func", [
        ('.csv', 'read_csv'),
        ('.json', 'read_json'),
        ('.xlsx', 'read_excel'),
        ('.parquet', 'read_parquet')
    ])
    def test_load_supported_formats(self, file_loader, mock_validator, file_ext, reader_func):
        """Test loading different supported file formats."""
        file_loader.file_path = f"test_file{file_ext}"

        with patch(f'pandas.{reader_func}', return_value=MOCK_DATA['dataframe']):
            df = file_loader.load_file()
            assert isinstance(df, pd.DataFrame)
            assert list(df.columns) == ['column1', 'column2']
            mock_validator.validate_file.assert_called_once_with(file_loader.file_path)

    def test_unsupported_format(self, file_loader):
        """Test loading unsupported file format."""
        file_loader.file_path = "test.unsupported"
        with pytest.raises(ValueError, match="Unsupported file format"):
            file_loader.load_file()

    def test_low_quality_file(self, file_loader, mock_validator):
        """Test loading file with low quality gauge."""
        mock_validator.validate_file.return_value = MOCK_DATA['failed_validation_report']

        with pytest.raises(ValueError, match="File quality gauge is too low"):
            file_loader.load_file()

    def test_validation_failure(self, file_loader, mock_validator):
        """Test loading file that fails validation."""
        mock_validator.validate_completeness.return_value = (False, "Missing required data")

        with patch('pandas.read_csv', return_value=MOCK_DATA['dataframe']):
            with pytest.raises(ValueError, match="File validation failed"):
                file_loader.load_file()

            # Verify the validator was called
            mock_validator.validate_completeness.assert_called_once_with(file_loader.file_path)

    def test_chunk_loading(self, mock_file_system):
        """Test loading large file in chunks."""
        # Set file size above threshold
        mock_file_system['size'].return_value = (Config.FILE_SIZE_THRESHOLD_MB + 1) * 1024 * 1024

        with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader.FileValidator') as MockValidator:
            mock_validator = MockValidator.return_value
            mock_validator.validate_file.return_value = MOCK_DATA['validation_report']
            mock_validator.validate_completeness.return_value = (True, None)

            file_loader = FileLoader("large_file.csv", ["column1", "column2"])
            chunks = [
                pd.DataFrame({'column1': ['value1'], 'column2': ['value2']}),
                pd.DataFrame({'column1': ['value3'], 'column2': ['value4']})
            ]

            with patch('pandas.read_csv') as mock_read_csv:
                mock_read_csv.return_value = iter(chunks)
                df = file_loader.load_file()

                assert isinstance(df, pd.DataFrame)
                assert len(df) == sum(len(chunk) for chunk in chunks)
                # Verify validator was called for each chunk
                assert mock_validator.validate_completeness.call_count == len(chunks)

    @pytest.mark.parametrize("error,expected_match", [
        (UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid'), "File validation failed"),
        (pd.errors.EmptyDataError(), "File validation failed"),
        (Exception("Corrupted file"), "File validation failed")
    ])
    def test_file_reading_errors(self, file_loader, mock_validator, error, expected_match):
        """Test various file reading errors."""
        with patch('pandas.read_csv', side_effect=error):
            with pytest.raises(ValueError, match=expected_match):
                file_loader.load_file()