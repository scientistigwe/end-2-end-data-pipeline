import pytest
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
from pandas.errors import EmptyDataError, ParserError
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.config import Config
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader import FileLoader

# Mock data and configurations
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
    """Mock file system operations, including path checks."""
    with patch('os.path.exists', return_value=True) as mock_exists, \
            patch('os.path.getsize', return_value=1024 * 1024) as mock_size, \
            patch('builtins.open', mock_open(read_data=MOCK_DATA['csv'])):
        yield {
            'exists': mock_exists,
            'size': mock_size
        }

@pytest.fixture
def mock_path_operations():
    """Mock os.path operations."""
    with patch('os.path.exists', return_value=True) as mock_exists, \
            patch('os.path.getsize', return_value=1024 * 1024) as mock_size:
        yield {
            'exists': mock_exists,
            'size': mock_size
        }

@pytest.fixture
def file_loader(mock_path_operations):
    """Create a FileLoader instance with mocked dependencies."""
    with patch(
            'backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader.FileValidator') as MockValidator:
        mock_instance = MockValidator.return_value
        mock_instance.validate_file.return_value = MOCK_DATA['validation_report']
        mock_instance.validate_completeness.return_value = (True, None)

        with patch('pandas.read_csv', return_value=MOCK_DATA['dataframe']):
            loader = FileLoader(
                file_path="test_files/valid_data.csv",
                required_columns=["column1", "column2"]
            )
            loader.validator = mock_instance
            return loader

class TestFileLoader:
    """Test suite for FileLoader class."""

    def test_initialization(self, mock_path_operations):
        """Test FileLoader initialization."""
        with patch(
                'backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader.FileValidator') as MockValidator:
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

    def test_chunk_loading(self):
        """Test chunk loading for large files."""
        # Create mock data to simulate two chunks of DataFrames
        chunk1 = pd.DataFrame({'column1': ['value1'], 'column2': ['value2']})
        chunk2 = pd.DataFrame({'column1': ['value3'], 'column2': ['value4']})

        # Create a MagicMock that will act as our TextFileReader
        csv_reader = MagicMock()
        # Make it iterable and return our chunks
        csv_reader.__iter__.return_value = iter([chunk1, chunk2])

        # Patch file system and reading functions
        with patch('os.path.exists', return_value=True), \
                patch('os.path.getsize', return_value=(Config.FILE_SIZE_THRESHOLD_MB + 1) * 1024 * 1024), \
                patch('pandas.read_csv', return_value=csv_reader):
            # Initialize FileLoader with a mocked file path
            file_loader = FileLoader(file_path="large_file.csv", required_columns=["column1", "column2"])

            # Mock the validator with MagicMock
            file_loader.validator.validate_file = MagicMock(return_value={
                'validation_results': {
                    'completeness': {'valid': True}
                }
            })

            # Load the file in chunks
            result = file_loader.load_file_in_chunks(chunk_size=1)

            # Assertions
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2  # Two rows total from both chunks
            assert list(result.columns) == ['column1', 'column2']
            assert result['column1'].tolist() == ['value1', 'value3']
            assert result['column2'].tolist() == ['value2', 'value4']

            # Verify that read_csv was called with the correct parameters
            pd.read_csv.assert_called_once_with(file_loader.file_path, chunksize=1)

    @pytest.mark.parametrize("error,expected_message", [
        (EmptyDataError("Empty file"), "File loading failed: Empty file"),
        (ParserError("Corrupted file"), "File loading failed: Corrupted file"),
        (UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid'), "File encoding error: 'utf-8' codec can't decode bytes")
    ])
    def test_file_reading_errors(self, file_loader, error, expected_message):
        """Test file reading errors."""
        with patch('pandas.read_csv', side_effect=error):
            with pytest.raises(ValueError, match=expected_message):
                file_loader.load_file()
