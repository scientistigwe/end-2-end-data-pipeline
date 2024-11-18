import pytest
from unittest.mock import patch
from io import BytesIO
import pandas as pd
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.file.file_fetcher import FileFetcher
from backend.data_pipeline.source.file.file_validator import FileValidator
from backend.data_pipeline.source.file.file_config import Config

# ------------------- Integration Tests ------------------- #

@patch("backend.data_pipeline.source.file.file_fetcher.FileFetcher.fetch_file")
@patch("backend.data_pipeline.source.file.file_validator.FileValidator.validate_file_path")
def test_full_file_system_workflow(mock_validate_file_path, mock_fetch_file, mock_flask_app):
    # Mock file validation and fetcher behavior
    mock_validate_file_path.return_value = True  # Assume file path is valid
    mock_fetch_file.return_value = pd.DataFrame({"col1": [1], "col2": [2]}), None

    # Mock file content
    content = "col1,col2\n1,2"
    file = BytesIO(content.encode(Config.ENCODING))

    # FileManager will use the mocked FileFetcher and FileValidator
    file_manager = FileManager(file, file_format='csv')

    # File validation
    file_manager.validate_file_path()

    # Metadata extraction
    metadata = file_manager.get_file_metadata()
    assert metadata["file_size_mb"] > 0
    assert metadata["columns"] == ["col1", "col2"]

    # File preparation
    result = file_manager.prepare_for_orchestration()
    assert result["status"] == "success"
    assert "data" in result  # Should return DataFrame


@patch("backend.data_pipeline.source.file.file_fetcher.FileFetcher.fetch_file")
@patch("backend.data_pipeline.source.file.file_manager.FileManager.prepare_for_orchestration")
def test_file_system_error_handling(mock_prepare_for_orchestration, mock_fetch_file, mock_flask_app):
    # Simulate a failed fetcher
    mock_fetch_file.return_value = None, "Failed to fetch file"
    content = "col1,col2\n1,2"
    file = BytesIO(content.encode(Config.ENCODING))

    file_manager = FileManager(file, file_format='csv')

    # Check error handling when fetching file fails
    result = file_manager.prepare_for_orchestration()

    assert "error" in result
    assert result["error"] == "Failed to fetch file"
