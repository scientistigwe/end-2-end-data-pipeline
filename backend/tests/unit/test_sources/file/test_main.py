import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main import handle_file_source
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator import FileValidator

# Mock data configurations
MOCK_DATA = {
    'valid_data.csv': pd.DataFrame({
        'column1': [1, 2, 3],
        'column2': ['a', 'b', 'c'],
        'column3': [True, False, True]
    }),
    'missing_columns_data.csv': pd.DataFrame({
        'column1': [1, 2, 3],
        'column2': ['a', 'b', 'c']
    }),
    'empty_data.csv': pd.DataFrame(columns=['column1', 'column2', 'column3'])
}


@pytest.fixture(autouse=True)
def patch_file_loader():
    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileLoader') as MockFileLoader:
        mock_instance = MagicMock()

        # Mock __init__ method
        mock_instance.__init__.return_value = None

        # Mock attributes
        mock_instance.file_path = MagicMock(return_value="valid_data.csv")
        mock_instance.required_columns = MagicMock()
        mock_instance.validator = MagicMock(spec=FileValidator)

        # Mock methods
        @staticmethod
        def mock_validate_file(file_path):
            return {
                "quality_gauge": 95,
                "validation_results": {"file_format": {"valid": True, "error": None}},
                "required_columns": []
            }

        @staticmethod
        def mock_load_csv(chunk_size=None):
            return pd.DataFrame({
                'column1': [1, 2, 3],
                'column2': ['a', 'b', 'c'],
                'column3': [True, False, True]
            })

        @staticmethod
        def mock_load_json():
            return pd.DataFrame({
                'column1': [1, 2, 3],
                'column2': ['a', 'b', 'c'],
                'column3': [True, False, True]
            })

        @staticmethod
        def mock_load_excel():
            return pd.DataFrame({
                'column1': [1, 2, 3],
                'column2': ['a', 'b', 'c'],
                'column3': [True, False, True]
            })

        @staticmethod
        def mock_load_parquet():
            return pd.DataFrame({
                'column1': [1, 2, 3],
                'column2': ['a', 'b', 'c'],
                'column3': [True, False, True]
            })

        @staticmethod
        def mock_load_in_chunks(reader_func, chunksize=None):
            return reader_func("test.parquet", chunksize=chunksize)

        # Assign mocked methods to the mock instance
        mock_instance.validate_file = staticmethod(mock_validate_file)
        mock_instance._load_csv = staticmethod(mock_load_csv)
        mock_instance._load_json = staticmethod(mock_load_json)
        mock_instance._load_excel = staticmethod(mock_load_excel)
        mock_instance._load_parquet = staticmethod(mock_load_parquet)
        mock_instance._load_in_chunks = staticmethod(mock_load_in_chunks)

        # Mock os.path.exists to always return True (simulate file existence)
        with patch('os.path.exists', return_value=True):
            yield MockFileLoader

            # Reset mocks after each test case
            MockFileLoader.reset_mock()
            mock_instance.file_path = MagicMock(return_value="valid_data.csv")

@pytest.fixture
def mock_file_validator():
    """Fixture to mock the FileValidator."""
    mock_validator = MagicMock(spec=FileValidator)  # Make sure it's a mock of the FileValidator class
    mock_validator.validate_file.return_value = {
        "validation_results": {"file_format": {"valid": True, "error": None}},
        "quality_gauge": 95,
        "required_columns": []
    }
    return mock_validator


# Test valid data scenario
def test_valid_data(caplog):
    with caplog.at_level("INFO"):
        result = handle_file_source("valid_data.csv", required_columns=["column1", "column2", "column3"])

    assert "Data loaded successfully" in caplog.text
    assert result["success"] is True


# Test invalid format scenario
@patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator.FileValidator', return_value=mock_file_validator)
def test_invalid_format(mock_file_validator, caplog):
    mock_file_validator.validate_file.return_value = {
        "validation_results": {"file_format": {"valid": False, "error": "Invalid format"}},
        "quality_gauge": 80,
        "recommendations": ["File format is invalid."]
    }

    with caplog.at_level("WARNING"):
        result = handle_file_source("valid_data.csv", required_columns=["column1", "column2", "column3"])

    assert "File quality gauge is below 90%. Quality: 80" in caplog.text
    assert result["success"] is False


# Test empty data scenario
def test_empty_data(caplog):
    with caplog.at_level("WARNING"):
        result = handle_file_source("empty_data.csv", required_columns=["column1", "column2", "column3"])

    assert "Data loaded successfully" in caplog.text
    assert "Loaded data is empty" in caplog.text
    assert result["success"] is False


# Test missing required columns scenario
def test_missing_required_columns(mock_file_validator, caplog):
    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator.FileValidator', return_value=mock_file_validator):
        mock_file_validator.validate_file.return_value = {
            "validation_results": {
                "file_format": {"valid": True, "error": None},
                "completeness": {"valid": False, "error": "Missing required columns"}
            },
            "quality_gauge": 70,
            "recommendations": ["Ensure the file has all required columns."]
        }

        with caplog.at_level("WARNING"):
            result = handle_file_source("missing_columns_data.csv", required_columns=["column1", "column2", "column3"])

        assert "File quality gauge is below 90%. Quality: 70" in caplog.text
        assert result["success"] is False


# Test when the data doesn't meet the quality gauge
def test_quality_below_threshold(mock_file_validator, caplog):
    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator.FileValidator', return_value=mock_file_validator):
        mock_file_validator.validate_file.return_value = {
            "validation_results": {"file_format": {"valid": True, "error": None}},
            "quality_gauge": 85,  # Below threshold
            "recommendations": ["File quality is below 90%. Please check the errors and fix them."]
        }

        with caplog.at_level("WARNING"):
            result = handle_file_source("valid_data.csv", required_columns=["column1", "column2", "column3"])

        assert "File quality gauge is below 90%. Quality: 85" in caplog.text
        assert result["success"] is False
