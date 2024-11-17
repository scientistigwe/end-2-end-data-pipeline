import pytest
from io import BytesIO
from backend.backend.data_pipeline.source.file.file_manager import FileManager
from backend.backend.data_pipeline.source.file.file_config import Config
import pandas as pd


# ------------------- Edge Case Tests ------------------- #

def test_empty_file(mock_flask_app):
    file = BytesIO(b"")
    file_manager = FileManager(file, file_format='csv')
    result = file_manager.prepare_for_orchestrator()

    assert result["error"] == "Error reading file: No columns to parse from file"


def test_file_with_missing_columns(mock_flask_app):
    content = "col1,col2\n1"
    file = BytesIO(content.encode(Config.ENCODING))

    file_manager = FileManager(file, file_format='csv')
    result = file_manager.prepare_for_orchestrator()

    assert result["error"] == "Error processing file: Expected 2 columns, found 1."


def test_invalid_json_file(mock_flask_app):
    content = "{col1: 1, col2: 2}"
    file = BytesIO(content.encode(Config.ENCODING))

    file_manager = FileManager(file, file_format='json')
    result = file_manager.prepare_for_orchestrator()

    assert result["error"] == "Error processing file: Invalid JSON format"


def test_non_existent_file(mock_flask_app):
    file = BytesIO(b"")
    file_manager = FileManager(file, file_format='csv')

    # Mocking the situation where the file doesn't exist
    with pytest.raises(FileNotFoundError):
        file_manager.prepare_for_orchestrator()
