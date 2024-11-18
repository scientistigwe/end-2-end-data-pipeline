import pytest
import pandas as pd
import os
import io
from unittest.mock import Mock, patch
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.file.file_config import Config


@pytest.fixture
def mock_file():
    class MockFile:
        def __init__(self, content, filename, content_type):
            self.content = content.encode('utf-8') if isinstance(content, str) else content
            self.filename = filename
            self.content_type = content_type
            self._position = 0

        def read(self):
            return self.content

        def seek(self, position):
            self._position = position

        @property
        def stream(self):
            return io.BytesIO(self.content)

    return MockFile


class TestFileManager:
    """Test suite for FileManager class"""

    def test_get_file_metadata_success(self, mock_file):
        """Test successful metadata extraction from valid CSV file"""
        content = "col1,col2\n1,2\n3,4"
        file = mock_file(content, "test.csv", "text/csv")
        manager = FileManager(file, "csv")

        metadata = manager.get_file_metadata()
        assert "file_size_mb" in metadata
        assert metadata["file_format"] == "csv"
        assert metadata["columns"] == ["col1", "col2"]
        assert metadata["row_count"] == 2

    def test_get_file_metadata_invalid_file(self, mock_file):
        """Test metadata extraction with invalid file content"""
        content = "invalid content"
        file = mock_file(content, "test.csv", "text/csv")
        manager = FileManager(file, "csv")

        metadata = manager.get_file_metadata()
        assert "error" in metadata

    def test_prepare_small_file(self, mock_file):
        """Test preparation of small files that should be returned as DataFrame"""
        content = "col1,col2\n" + "\n".join([f"{i},{i + 1}" for i in range(10)])
        file = mock_file(content, "test.csv", "text/csv")
        manager = FileManager(file, "csv")

        result = manager.prepare_for_orchestration()
        assert result["status"] == "success"
        assert "data" in result
        assert isinstance(result["data"], list)
        assert len(result["data"]) == 10

    @pytest.mark.parametrize("file_size_mb,expected_output", [
        (Config.FILE_SIZE_THRESHOLD_MB + 1, "parquet"),
        (Config.FILE_SIZE_THRESHOLD_MB - 1, "dataframe")
    ])
    def test_prepare_file_size_threshold(self, mock_file, file_size_mb, expected_output):
        """Test file preparation based on size threshold"""
        # Create a mock DataFrame with calculated size
        content = "col1,col2\n" + "\n".join([f"{i},{i + 1}" for i in range(1000)])
        file = mock_file(content, "test.csv", "text/csv")
        manager = FileManager(file, "csv")

        # Mock the file_size_mb property
        manager.fetcher.file_size_mb = file_size_mb

        result = manager.prepare_for_orchestration()

        if expected_output == "parquet":
            assert "file_path" in result
            assert result["file_path"].endswith(".parquet")
        else:
            assert "data" in result
            assert isinstance(result["data"], list)

    @patch('pandas.DataFrame.to_parquet')
    def test_save_as_parquet_success(self, mock_to_parquet, mock_file):
        """Test successful Parquet file saving"""
        content = "col1,col2\n1,2\n3,4"
        file = mock_file(content, "test.csv", "text/csv")
        manager = FileManager(file, "csv")

        df = pd.DataFrame({"col1": [1, 3], "col2": [2, 4]})
        output_path = os.path.join(Config.STAGING_AREA, "test.parquet")

        manager._save_as_parquet(df, output_path)
        mock_to_parquet.assert_called_once_with(output_path, index=False)

    @patch('pandas.DataFrame.to_parquet')
    def test_save_as_parquet_error(self, mock_to_parquet, mock_file):
        """Test error handling when saving Parquet file fails"""
        mock_to_parquet.side_effect = Exception("Parquet save error")

        content = "col1,col2\n1,2\n3,4"
        file = mock_file(content, "test.csv", "text/csv")
        manager = FileManager(file, "csv")

        df = pd.DataFrame({"col1": [1, 3], "col2": [2, 4]})
        output_path = os.path.join(Config.STAGING_AREA, "test.parquet")

        with pytest.raises(Exception) as exc_info:
            manager._save_as_parquet(df, output_path)
        assert "Parquet save error" in str(exc_info.value)

    def test_file_format_handling(self, mock_file):
        """Test handling of different file formats"""
        # Test CSV
        csv_content = "col1,col2\n1,2\n3,4"
        csv_file = mock_file(csv_content, "test.csv", "text/csv")
        csv_manager = FileManager(csv_file, "csv")
        csv_result = csv_manager.get_file_metadata()
        assert csv_result["file_format"] == "csv"

        # Test Excel
        excel_content = pd.DataFrame({"col1": [1, 3], "col2": [2, 4]}).to_excel(index=False)
        excel_file = mock_file(excel_content, "test.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        excel_manager = FileManager(excel_file, "excel")
        excel_result = excel_manager.get_file_metadata()
        assert excel_result["file_format"] == "excel"

    def test_error_handling(self, mock_file):
        """Test error handling for various scenarios"""
        # Test with empty file
        empty_file = mock_file("", "empty.csv", "text/csv")
        empty_manager = FileManager(empty_file, "csv")
        empty_result = empty_manager.get_file_metadata()
        assert "error" in empty_result

        # Test with corrupted content
        corrupted_file = mock_file("corrupted,content\n1,2,3", "corrupt.csv", "text/csv")
        corrupted_manager = FileManager(corrupted_file, "csv")
        corrupted_result = corrupted_manager.get_file_metadata()
        assert "error" in corrupted_result