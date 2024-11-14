import pytest
from unittest.mock import patch, mock_open
from data_pipeline.source.file.file_loader import FileLoader
from data_pipeline.source.file.config import Config
import pandas as pd

# Mock data constants
VALID_CSV_CONTENT = """column1,column2,column3
value1,value2,value3
value4,value5,value6"""

MISSING_COLUMN_CSV_CONTENT = """column1,column3
value1,value3
value4,value6"""


@pytest.fixture
def mock_file_exists():
    with patch('os.path.exists') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_file_size():
    with patch('os.path.getsize') as mock:
        mock.return_value = 1024  # 1KB
        yield mock


@pytest.fixture
def file_loader(mock_file_exists, mock_file_size):
    return FileLoader(
        file_path="tests/test_files/valid_data.csv",
        required_columns=["column1", "column2"]
    )


def test_file_loader_integration(file_loader):
    # Test loading a valid file
    valid_df = pd.DataFrame({
        'column1': ['value1', 'value4'],
        'column2': ['value2', 'value5'],
        'column3': ['value3', 'value6']
    })

    missing_column_df = pd.DataFrame({
        'column1': ['value1', 'value4'],
        'column3': ['value3', 'value6']
    })

    # Test loading a valid file
    with patch('builtins.open', mock_open(read_data=VALID_CSV_CONTENT)), \
            patch('pandas.read_csv', return_value=valid_df):
        df = file_loader.load_file()
        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert "column1" in df.columns
        assert "column2" in df.columns

    # Test invalid file format
    file_loader.file_path = "tests/test_files/invalid_data.txt"
    with patch('builtins.open', mock_open(read_data="invalid content")):
        with pytest.raises(ValueError, match="Unsupported file format"):
            file_loader.load_file()

    # Test missing required columns
    file_loader.file_path = "tests/test_files/missing_column.csv"
    with patch('builtins.open', mock_open(read_data=MISSING_COLUMN_CSV_CONTENT)), \
            patch('pandas.read_csv', return_value=missing_column_df):
        with pytest.raises(ValueError, match="Missing required columns"):
            file_loader.load_file()


def test_file_loader_chunked_reading(mock_file_exists):
    # Mock a large file size to trigger chunked reading
    with patch('os.path.getsize') as mock_size:
        mock_size.return_value = Config.FILE_SIZE_THRESHOLD_MB * 1024 * 1024 + 1

        file_loader = FileLoader(
            file_path="tests/test_files/valid_data.csv",
            required_columns=["column1", "column2"]
        )

        chunk1 = pd.DataFrame({
            'column1': ['value1'],
            'column2': ['value2']
        })
        chunk2 = pd.DataFrame({
            'column1': ['value3'],
            'column2': ['value4']
        })

        with patch('builtins.open', mock_open(read_data=VALID_CSV_CONTENT)), \
                patch('pandas.read_csv') as mock_read_csv:
            mock_read_csv.return_value = chunk1
            df = file_loader.load_file()

            assert isinstance(df, pd.DataFrame)
            assert "column1" in df.columns
            assert "column2" in df.columns


def test_file_loader_parquet(mock_file_exists, mock_file_size):
    file_loader = FileLoader(
        file_path="tests/test_files/valid_data.parquet",
        required_columns=["column1", "column2"]
    )

    valid_df = pd.DataFrame({
        'column1': ['value1', 'value4'],
        'column2': ['value2', 'value5']
    })

    with patch('builtins.open', mock_open()), \
            patch('pandas.read_parquet', return_value=valid_df):
        df = file_loader.load_file()
        assert isinstance(df, pd.DataFrame)
        assert "column1" in df.columns
        assert "column2" in df.columns


def test_file_loader_json(mock_file_exists, mock_file_size):
    file_loader = FileLoader(
        file_path="tests/test_files/valid_data.json",
        required_columns=["column1", "column2"]
    )

    valid_df = pd.DataFrame({
        'column1': ['value1', 'value4'],
        'column2': ['value2', 'value5']
    })

    with patch('builtins.open', mock_open()), \
            patch('pandas.read_json', return_value=valid_df):
        df = file_loader.load_file()
        assert isinstance(df, pd.DataFrame)
        assert "column1" in df.columns
        assert "column2" in df.columns


def test_file_not_found():
    with patch('os.path.exists', return_value=False):
        with pytest.raises(FileNotFoundError):
            FileLoader(file_path="nonexistent.csv")


def test_empty_file(mock_file_exists, mock_file_size):
    file_loader = FileLoader(
        file_path="tests/test_files/empty.csv",
        required_columns=["column1", "column2"]
    )

    with patch('builtins.open', mock_open(read_data="")), \
            patch('pandas.read_csv', return_value=pd.DataFrame()):
        with pytest.raises(ValueError, match="File is empty"):
            file_loader.load_file()