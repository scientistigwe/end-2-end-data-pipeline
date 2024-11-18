import pytest
from unittest.mock import patch
from backend.data_pipeline.source.file.file_fetcher import FileFetcher
from backend.data_pipeline.source.file.file_validator import FileValidator
from backend.data_pipeline.source.file.file_config import Config
from backend.data_pipeline.source.file.file_manager import FileManager
from io import BytesIO

# ------------------- Security Tests ------------------- #

def test_file_validator_invalid_file_path(mock_flask_app):
    file_path = "fakepath/../../etc/passwd"
    validator = FileValidator(file_path)

    with pytest.raises(ValueError):
        validator.validate_file_path()


@patch("backend.data_pipeline.source.file.file_fetcher.pd.read_csv")
def test_fetcher_with_malicious_content(mock_read_csv, mock_flask_app):
    # Mocking CSV reader to simulate malicious content processing
    mock_read_csv.return_value = "malicious content"

    content = "malicious content"
    file = BytesIO(content.encode(Config.ENCODING))

    fetcher = FileFetcher(file, file_format='csv')
    df, message = fetcher.fetch_file()

    assert df is None
    assert message == "Unsupported file format: csv"


def test_file_manager_invalid_format(mock_flask_app):
    content = "col1,col2\n1,2"
    file = BytesIO(content.encode(Config.ENCODING))

    with pytest.raises(ValueError):
        file_manager = FileManager(file, file_format="exe")
