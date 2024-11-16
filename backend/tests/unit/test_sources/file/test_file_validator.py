import pytest
from unittest.mock import patch, mock_open, MagicMock
import pandas as pd
from pandas.errors import EmptyDataError
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator import FileValidator

# Constants
TEST_DATA = {
    'CSV_CONTENT': "column1,column2\nvalue1,value2",
    'DATAFRAME': pd.DataFrame({'column1': ['value1'], 'column2': ['value2']}),
    'EMPTY_DATAFRAME': pd.DataFrame(),
    'REQUIRED_COLUMNS': ['column1', 'column2'],
    'TEST_FILES': {
        'csv': 'test.csv',
        'parquet': 'test.parquet',
        'json': 'test.json',
        'invalid': 'test.txt'
    }
}

# Fixtures
@pytest.fixture
def validator():
    return FileValidator(required_columns=TEST_DATA['REQUIRED_COLUMNS'])

@pytest.fixture
def mock_file_exists():
    with patch('os.path.exists', return_value=True) as mock:
        yield mock

@pytest.fixture
def mock_pandas_reads():
    with patch.multiple(
        'pandas',
        read_csv=MagicMock(return_value=TEST_DATA['DATAFRAME']),
        read_parquet=MagicMock(return_value=TEST_DATA['DATAFRAME']),
        read_json=MagicMock(return_value=TEST_DATA['DATAFRAME'])
    ) as mocks:
        yield mocks

@pytest.fixture
def mock_file_open():
    with patch('builtins.open', mock_open(read_data=TEST_DATA['CSV_CONTENT'])) as mock:
        yield mock

# Test Classes
class TestFileFormat:
    @pytest.mark.parametrize("file_path,expected", [
        ('test.csv', (True, None)),
        ('test.parquet', (True, None)),
        ('test.json', (True, None)),
        ('test.txt', (False, "Invalid file format"))
    ])
    def test_validate_file_format(self, validator, file_path, expected):
        result = validator.validate_file_format(file_path)
        assert result[0] == expected[0]
        if not expected[0]:
            assert expected[1] in result[1]


class TestCompleteness:
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_file_exists, mock_pandas_reads, mock_file_open):
        self.mock_file_exists = mock_file_exists
        self.mock_pandas_reads = mock_pandas_reads
        self.mock_file_open = mock_file_open

    def test_valid_csv(self, validator):
        valid, error = validator.validate_completeness(TEST_DATA['TEST_FILES']['csv'])
        assert valid
        assert error is None

    def test_missing_columns(self, validator):
        df_missing_column = pd.DataFrame({'column1': ['value1']})
        with patch('pandas.read_csv', return_value=df_missing_column):
            valid, error = validator.validate_completeness(TEST_DATA['TEST_FILES']['csv'])
            assert not valid
            assert "Missing required columns" in error

    def test_empty_file(self, validator):
        with patch('os.path.exists', return_value=True), \
                patch('pandas.read_csv', side_effect=EmptyDataError("Empty file")):
            valid, error = validator.validate_completeness(TEST_DATA['TEST_FILES']['csv'])
            assert not valid
            assert "File is empty" in error

    def test_file_not_found(self, validator):
        with patch('os.path.exists', return_value=False):
            valid, error = validator.validate_completeness('nonexistent.csv')
            assert not valid
            assert "File does not exist" in error

    @pytest.mark.parametrize("file_type,read_function", [
        ('parquet', 'read_parquet'),
        ('json', 'read_json')
    ])
    def test_other_formats(self, validator, file_type, read_function):
        with patch(f'pandas.{read_function}', return_value=TEST_DATA['DATAFRAME']):
            valid, error = validator.validate_completeness(TEST_DATA['TEST_FILES'][file_type])
            assert valid
            assert error is None

class TestFileIntegrity:
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_file_exists, mock_pandas_reads, mock_file_open):
        self.mock_file_exists = mock_file_exists
        self.mock_pandas_reads = mock_pandas_reads
        self.mock_file_open = mock_file_open

    def test_valid_csv(self, validator):
        valid, error = validator.validate_file_integrity(TEST_DATA['TEST_FILES']['csv'])
        assert valid
        assert error is None

    def test_read_error(self, validator):
        with patch('pandas.read_csv', side_effect=Exception("Read error")):
            valid, error = validator.validate_file_integrity(TEST_DATA['TEST_FILES']['csv'])
            assert not valid
            assert "File integrity check failed" in error

class TestEncoding:
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_file_exists, mock_file_open):
        self.mock_file_exists = mock_file_exists
        self.mock_file_open = mock_file_open

    def test_valid_encoding(self, validator):
        valid, error = validator.validate_encoding(TEST_DATA['TEST_FILES']['csv'])
        assert valid
        assert error is None

    def test_invalid_encoding(self, validator):
        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
            valid, error = validator.validate_encoding(TEST_DATA['TEST_FILES']['csv'])
            assert not valid
            assert "File encoding error" in error

class TestMetadata:
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_file_exists, mock_file_open):
        self.mock_file_exists = mock_file_exists
        self.mock_file_open = mock_file_open

    def test_valid_csv(self, validator):
        valid, error = validator.validate_metadata(TEST_DATA['TEST_FILES']['csv'])
        assert valid
        assert error is None

    def test_empty_csv(self, validator):
        with patch('builtins.open', mock_open(read_data="")):
            valid, error = validator.validate_metadata(TEST_DATA['TEST_FILES']['csv'])
            assert not valid
            assert "CSV file does not have headers" in error

class TestCompleteValidation:
    @pytest.fixture(autouse=True)
    def setup_mocks(self, mock_file_exists, mock_pandas_reads, mock_file_open):
        self.mock_file_exists = mock_file_exists
        self.mock_pandas_reads = mock_pandas_reads
        self.mock_file_open = mock_file_open

    def test_all_validations_pass(self, validator):
        with patch.multiple(
            FileValidator,
            validate_file_format=MagicMock(return_value=(True, None)),
            validate_completeness=MagicMock(return_value=(True, None)),
            validate_file_integrity=MagicMock(return_value=(True, None)),
            validate_encoding=MagicMock(return_value=(True, None)),
            validate_metadata=MagicMock(return_value=(True, None))
        ):
            result = validator.validate_file(TEST_DATA['TEST_FILES']['csv'])
            assert isinstance(result, dict)
            assert all(key in result for key in ['validation_results', 'quality_gauge', 'recommendations'])
            assert result['quality_gauge'] == 100.0
            assert len(result['recommendations']) == 0

    def test_partial_validation_failure(self, validator):
        with patch.multiple(
            FileValidator,
            validate_file_format=MagicMock(return_value=(False, "Format error")),
            validate_completeness=MagicMock(return_value=(False, "Completeness error")),
            validate_file_integrity=MagicMock(return_value=(True, None)),
            validate_encoding=MagicMock(return_value=(True, None)),
            validate_metadata=MagicMock(return_value=(True, None))
        ):
            result = validator.validate_file(TEST_DATA['TEST_FILES']['csv'])
            assert result['quality_gauge'] == 60.0  # 3 out of 5 checks passed
            assert len(result['recommendations']) > 0
            assert any("Invalid file format" in rec for rec in result['recommendations'])