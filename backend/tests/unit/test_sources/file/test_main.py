import pytest
import pandas as pd
from unittest.mock import Mock, patch
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader import FileLoader
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator import FileValidator
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main import handle_file_source


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'column1': [1, 2, 3],
        'column2': ['a', 'b', 'c']
    })


@pytest.fixture
def required_columns():
    return ['column1', 'column2']


def test_valid_data(sample_df, required_columns):
    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileLoader') as MockFileLoader, \
            patch(
                'backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileValidator') as MockFileValidator:
        # Configure FileLoader mock
        instance = MockFileLoader.return_value
        instance.load_file.return_value = sample_df

        # Configure FileValidator mock
        validator_instance = MockFileValidator.return_value
        validator_instance.validate_file.return_value = {
            "quality_gauge": 95,
            "validation_results": {"all_passed": True}
        }

        # Execute the function
        result = handle_file_source("dummy_path.csv", required_columns)

        # Assertions
        assert result["success"] is True
        assert result["validation_results"]["quality_gauge"] == 95
        assert isinstance(result["data"], pd.DataFrame)
        assert not result["data"].empty

        # Verify the FileLoader was initialized correctly
        MockFileLoader.assert_called_once_with(file_path="dummy_path.csv", required_columns=required_columns)


def test_invalid_format(required_columns):
    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileLoader') as MockFileLoader:
        # Configure FileLoader mock to raise an exception
        instance = MockFileLoader.return_value
        instance.load_file.side_effect = Exception("Invalid file format")

        with pytest.raises(Exception) as exc_info:
            handle_file_source("invalid.xyz", required_columns)
        assert "Invalid file format" in str(exc_info.value)


def test_empty_data(required_columns):
    empty_df = pd.DataFrame()

    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileLoader') as MockFileLoader, \
            patch(
                'backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileValidator') as MockFileValidator:
        # Configure FileLoader mock
        instance = MockFileLoader.return_value
        instance.load_file.return_value = empty_df

        # Configure FileValidator mock
        validator_instance = MockFileValidator.return_value
        validator_instance.validate_file.return_value = {
            "quality_gauge": 100,
            "validation_results": {}
        }

        result = handle_file_source("empty.csv", required_columns)
        assert result["success"] is False
        assert result["data"].empty


def test_missing_required_columns(required_columns):
    df_missing_columns = pd.DataFrame({'column1': [1, 2, 3]})

    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileLoader') as MockFileLoader, \
            patch(
                'backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileValidator') as MockFileValidator:
        # Configure FileLoader mock
        instance = MockFileLoader.return_value
        instance.load_file.return_value = df_missing_columns

        # Configure FileValidator mock
        validator_instance = MockFileValidator.return_value
        validator_instance.validate_file.return_value = {
            "quality_gauge": 50,
            "validation_results": {"missing_columns": ["column2"]}
        }

        result = handle_file_source("missing_columns.csv", required_columns)
        assert result["success"] is False
        assert result["validation_results"]["quality_gauge"] == 50


def test_quality_below_threshold(sample_df, required_columns):
    with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileLoader') as MockFileLoader, \
            patch(
                'backend.src.end_2_end_data_pipeline.data_pipeline.source.file.main.FileValidator') as MockFileValidator:
        # Configure FileLoader mock
        instance = MockFileLoader.return_value
        instance.load_file.return_value = sample_df

        # Configure FileValidator mock
        validator_instance = MockFileValidator.return_value
        validator_instance.validate_file.return_value = {
            "quality_gauge": 85,
            "validation_results": {"quality_issues": True}
        }

        result = handle_file_source("low_quality.csv", required_columns)
        assert result["success"] is False
        assert result["validation_results"]["quality_gauge"] == 85