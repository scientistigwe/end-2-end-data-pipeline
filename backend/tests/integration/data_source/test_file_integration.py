
import pytest
import pandas as pd
import os
from unittest.mock import patch, mock_open, Mock
from pandas.errors import EmptyDataError

from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader import FileLoader
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator import FileValidator
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.config import Config
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main import handle_file_source

class ChunkedFileMock:
    """Helper class to simulate pandas chunked file reading"""

    def __init__(self, chunks):
        self.chunks = chunks
        self._validate_chunks()

    def __iter__(self):
        return iter(self.chunks)

    @property
    def columns(self):
        """Simulate the columns attribute by using the first chunk's columns."""
        return self.chunks[0].columns if self.chunks else None

    def _validate_chunks(self):
        if not all(isinstance(chunk, pd.DataFrame) for chunk in self.chunks):
            raise ValueError("All chunks must be pandas DataFrames")


# Test data constants
VALID_CSV_CONTENT = """id,name,value
1,test1,100
2,test2,200
3,test3,300"""

INVALID_CSV_CONTENT = """id,value
1,100
2,200"""


@pytest.fixture
def valid_df():
    return pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['test1', 'test2', 'test3'],
        'value': [100, 200, 300]
    })


@pytest.fixture
def invalid_df():
    return pd.DataFrame({
        'id': [1, 2],
        'value': [100, 200]
    })


@pytest.fixture
def mock_file_environment():
    with patch('os.path.exists', return_value=True), \
            patch('os.path.getsize', return_value=1024):
        yield


class TestFileProcessingIntegration:
    def test_successful_end_to_end_processing(self, mock_file_environment, valid_df, caplog):
        """Test successful end-to-end file processing with all components."""
        test_file = "test_data.csv"
        required_columns = ['id', 'name', 'value']

        with patch('builtins.open', mock_open(read_data=VALID_CSV_CONTENT)), \
                patch('pandas.read_csv', return_value=valid_df), \
                patch.object(FileValidator, 'validate_file', return_value={
                    "validation_results": {"all": {"valid": True, "error": None}},
                    "quality_gauge": 100,
                    "recommendations": []
                }):
            result = handle_file_source(test_file, required_columns)

            assert result['success'] is True
            assert isinstance(result['data'], pd.DataFrame)
            assert all(col in result['data'].columns for col in required_columns)
            assert result['validation_results']['quality_gauge'] >= 90

    def test_large_file_chunked_processing(self, mock_file_environment, valid_df):
            """Test processing of large files using chunked reading."""
            test_file = "large_test.csv"
            required_columns = ['id', 'name', 'value']

            large_file_size = (Config.FILE_SIZE_THRESHOLD_MB * 1024 * 1024) + 1

            # Create chunks
            chunk1 = pd.DataFrame({
                'id': [1, 2, 3],
                'name': ['test1', 'test2', 'test3'],
                'value': [100, 200, 300]
            })
            chunk2 = pd.DataFrame({
                'id': [4, 5, 6],
                'name': ['test4', 'test5', 'test6'],
                'value': [400, 500, 600]
            })

            # Create chunked file mock
            chunked_file = ChunkedFileMock([chunk1, chunk2])

            with patch('os.path.exists', return_value=True), \
                    patch('os.path.getsize', return_value=large_file_size), \
                    patch('pandas.read_csv', return_value=chunked_file), \
                    patch.object(FileValidator, 'validate_file', return_value={
                        "validation_results": {"all": {"valid": True, "error": None}},
                        "quality_gauge": 95,
                        "recommendations": []
                    }):
                result = handle_file_source(test_file, required_columns)

                assert result['success'] is True
                assert isinstance(result['data'], pd.DataFrame)
                assert len(result['data']) == len(chunk1) + len(chunk2)
                assert list(result['data']['id']) == [1, 2, 3, 4, 5, 6]

    def test_missing_required_columns(self, mock_file_environment, invalid_df):
        """Test handling of missing required columns."""
        test_file = "invalid_data.csv"
        required_columns = ['id', 'name', 'value']

        validation_error = {
            "validation_results": {
                "completeness": {"valid": False, "error": "Missing required columns: name"},
                "all": {"valid": False, "error": "Missing required columns: name"}
            },
            "quality_gauge": 80,
            "recommendations": ["Add missing columns"]
        }

        with patch('builtins.open', mock_open(read_data=INVALID_CSV_CONTENT)), \
                patch('pandas.read_csv', return_value=invalid_df), \
                patch.object(FileValidator, 'validate_file', return_value=validation_error):
            with pytest.raises(ValueError) as exc_info:
                handle_file_source(test_file, required_columns)

            assert "Missing required columns: name" in str(exc_info.value)

    def test_empty_file_handling(self, mock_file_environment):
        """Test handling of empty files."""
        test_file = "empty.csv"
        required_columns = ['id', 'name', 'value']

        validation_error = {
            "validation_results": {
                "completeness": {"valid": False, "error": "File is empty"},
                "all": {"valid": False, "error": "File is empty"}
            },
            "quality_gauge": 20,
            "recommendations": ["Provide non-empty file"]
        }

        with patch('pandas.read_csv', side_effect=EmptyDataError), \
                patch.object(FileValidator, 'validate_file', return_value=validation_error):
            with pytest.raises(ValueError) as exc_info:
                handle_file_source(test_file, required_columns)

            assert "File is empty" in str(exc_info.value)

    @pytest.mark.parametrize("file_size_mb,expected_chunks", [
        (Config.FILE_SIZE_THRESHOLD_MB - 1, 1),  # Below threshold
        (Config.FILE_SIZE_THRESHOLD_MB + 1, 2)  # Above threshold
    ])


    def test_file_size_threshold_handling(self, file_size_mb, expected_chunks, valid_df):
            """Test handling of different file sizes."""
            test_file = "test_file.csv"
            required_columns = ['id', 'name', 'value']
            file_size_bytes = int(file_size_mb * 1024 * 1024)

            if expected_chunks == 1:
                # For small files, return the DataFrame directly
                mock_data = valid_df
            else:
                # For large files, create chunks
                chunk1 = pd.DataFrame({
                    'id': [1, 2, 3],
                    'name': ['test1', 'test2', 'test3'],
                    'value': [100, 200, 300]
                })
                chunk2 = pd.DataFrame({
                    'id': [4, 5, 6],
                    'name': ['test4', 'test5', 'test6'],
                    'value': [400, 500, 600]
                })
                mock_data = ChunkedFileMock([chunk1, chunk2])

            with patch('os.path.exists', return_value=True), \
                    patch('os.path.getsize', return_value=file_size_bytes), \
                    patch('pandas.read_csv', return_value=mock_data), \
                    patch.object(FileValidator, 'validate_file', return_value={
                        "validation_results": {"all": {"valid": True, "error": None}},
                        "quality_gauge": 95,
                        "recommendations": []
                    }):

                result = handle_file_source(test_file, required_columns)

                assert result['success'] is True
                assert isinstance(result['data'], pd.DataFrame)

                if expected_chunks == 1:
                    assert len(result['data']) == len(valid_df)
                else:
                    assert len(result['data']) == 6  # Total rows from both chunks