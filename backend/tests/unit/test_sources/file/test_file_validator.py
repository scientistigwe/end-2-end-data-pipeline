import pytest
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
from pandas.errors import EmptyDataError
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator import FileValidator

# Test data
MOCK_CSV_CONTENT = "column1,column2\nvalue1,value2"
MOCK_DATAFRAME = pd.DataFrame({'column1': ['value1'], 'column2': ['value2']})
MOCK_EMPTY_DATAFRAME = pd.DataFrame()


@pytest.fixture
def validator():
    return FileValidator(required_columns=['column1', 'column2'])


@pytest.fixture
def mock_file_exists():
    with patch('os.path.exists') as mock:
        mock.return_value = True
        yield mock


def test_validate_file_format(validator):
    # Test valid formats
    assert validator.validate_file_format('test.csv') == (True, None)
    assert validator.validate_file_format('test.parquet') == (True, None)
    assert validator.validate_file_format('test.json') == (True, None)

    # Test invalid format
    valid, error = validator.validate_file_format('test.txt')
    assert not valid
    assert "Invalid file format" in error


def test_validate_completeness_csv(validator, mock_file_exists):
    with patch('pandas.read_csv', return_value=MOCK_DATAFRAME):
        valid, error = validator.validate_completeness('test.csv')
        assert valid
        assert error is None


def test_validate_completeness_missing_columns(validator, mock_file_exists):
    df_missing_column = pd.DataFrame({'column1': ['value1']})
    with patch('pandas.read_csv', return_value=df_missing_column):
        valid, error = validator.validate_completeness('test.csv')
        assert not valid
        assert "Missing required columns" in error


def test_validate_completeness_empty_file(validator, mock_file_exists):
    with patch('pandas.read_csv', side_effect=EmptyDataError):
        valid, error = validator.validate_completeness('test.csv')
        assert not valid
        assert "File is empty" in error


def test_validate_completeness_file_not_found(validator):
    with patch('os.path.exists', return_value=False):
        valid, error = validator.validate_completeness('nonexistent.csv')
        assert not valid
        assert "File does not exist" in error


def test_validate_completeness_parquet(validator, mock_file_exists):
    with patch('pandas.read_parquet', return_value=MOCK_DATAFRAME):
        valid, error = validator.validate_completeness('test.parquet')
        assert valid
        assert error is None


def test_validate_completeness_json(validator, mock_file_exists):
    with patch('pandas.read_json', return_value=MOCK_DATAFRAME):
        valid, error = validator.validate_completeness('test.json')
        assert valid
        assert error is None


def test_validate_file_integrity_csv(validator):
    with patch('pandas.read_csv') as mock_read:
        mock_read.return_value = MOCK_DATAFRAME
        valid, error = validator.validate_file_integrity('test.csv')
        assert valid
        assert error is None


def test_validate_file_integrity_error(validator):
    with patch('pandas.read_csv', side_effect=Exception("Read error")):
        valid, error = validator.validate_file_integrity('test.csv')
        assert not valid
        assert "File integrity check failed" in error


def test_validate_encoding_valid(validator):
    mock_file = mock_open(read_data=MOCK_CSV_CONTENT)
    with patch('builtins.open', mock_file):
        valid, error = validator.validate_encoding('test.csv')
        assert valid
        assert error is None


def test_validate_encoding_invalid(validator):
    with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
        valid, error = validator.validate_encoding('test.csv')
        assert not valid
        assert "File encoding error" in error


def test_validate_metadata_valid_csv(validator):
    mock_file = mock_open(read_data=MOCK_CSV_CONTENT)
    with patch('builtins.open', mock_file):
        valid, error = validator.validate_metadata('test.csv')
        assert valid
        assert error is None


def test_validate_metadata_empty_csv(validator):
    mock_file = mock_open(read_data="")
    with patch('builtins.open', mock_file):
        valid, error = validator.validate_metadata('test.csv')
        assert not valid
        assert "CSV file does not have headers" in error


def test_validate_file_complete(validator, mock_file_exists):
    # Mock all individual validation methods
    with patch.multiple(FileValidator,
                        validate_file_format=MagicMock(return_value=(True, None)),
                        validate_completeness=MagicMock(return_value=(True, None)),
                        validate_file_integrity=MagicMock(return_value=(True, None)),
                        validate_encoding=MagicMock(return_value=(True, None)),
                        validate_metadata=MagicMock(return_value=(True, None))):
        result = validator.validate_file('test.csv')

        assert isinstance(result, dict)
        assert 'validation_results' in result
        assert 'quality_gauge' in result
        assert 'recommendations' in result
        assert result['quality_gauge'] == 100.0
        assert len(result['recommendations']) == 0


def test_validate_file_with_errors(validator, mock_file_exists):
    # Mock methods to return errors
    with patch.multiple(FileValidator,
                        validate_file_format=MagicMock(return_value=(False, "Format error")),
                        validate_completeness=MagicMock(return_value=(False, "Completeness error")),
                        validate_file_integrity=MagicMock(return_value=(True, None)),
                        validate_encoding=MagicMock(return_value=(True, None)),
                        validate_metadata=MagicMock(return_value=(True, None))):
        result = validator.validate_file('test.csv')

        assert result['quality_gauge'] == 60.0  # 3 out of 5 checks passed
        assert len(result['recommendations']) > 0
        assert any("Invalid file format" in rec for rec in result['recommendations'])