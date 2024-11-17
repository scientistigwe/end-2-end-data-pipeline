# test_file_fetcher.py
import pytest
import pandas as pd
import io
from unittest.mock import Mock, patch
from pandas.errors import EmptyDataError, ParserError
from backend.backend.data_pipeline.source.file.file_fetcher import FileFetcher
from backend.backend.data_pipeline.source.file.file_config import Config


@pytest.fixture
def sample_csv_content():
    return "col1,col2\n1,2\n3,4"


@pytest.fixture
def sample_json_content():
    return '{"col1":[1,3],"col2":[2,4]}'


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


class TestFileFetcher:
    """Test suite for FileFetcher class"""

    def test_file_format_inference(self, mock_file):
        """Test correct inference of file formats"""
        test_cases = [
            ("test.csv", "csv"),
            ("test.json", "json"),
            ("test.xlsx", "xlsx"),
            ("test.parquet", "parquet"),
            ("test.unknown", None),
        ]

        for filename, expected_format in test_cases:
            file = mock_file("test", filename, "text/plain")
            fetcher = FileFetcher(file)
            assert fetcher.file_format == expected_format

    def test_successful_csv_load(self, mock_file, sample_csv_content):
        """Test successful loading of CSV file"""
        file = mock_file(sample_csv_content, "test.csv", "text/csv")
        fetcher = FileFetcher(file)
        df, message = fetcher.fetch_file()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (2, 2)
        assert "success" in message.lower()

    def test_successful_json_load(self, mock_file, sample_json_content):
        """Test successful loading of JSON file"""
        file = mock_file(sample_json_content, "test.json", "application/json")
        fetcher = FileFetcher(file)
        df, message = fetcher.fetch_file()
        assert isinstance(df, pd.DataFrame)
        assert df.shape == (2, 2)
        assert "success" in message.lower()

    @pytest.mark.parametrize("chunk_size", [1, 10, 100])
    def test_chunk_loading(self, mock_file, chunk_size):
        """Test loading files in chunks with different chunk sizes"""
        # Create large CSV content
        rows = 1000
        content = "col1,col2\n" + "\n".join([f"{i},{i + 1}" for i in range(rows)])
        file = mock_file(content, "test.csv", "text/csv")
        fetcher = FileFetcher(file)
        df, message = fetcher.load_file_in_chunks(chunk_size=chunk_size)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == rows
        assert "success" in message.lower()

    def test_empty_file_handling(self, mock_file):
        """Test handling of empty files"""
        file = mock_file("", "test.csv", "text/csv")
        fetcher = FileFetcher(file)
        df, message = fetcher.fetch_file()
        assert df is None
        assert "error" in message.lower()

    def test_corrupted_file_handling(self, mock_file):
        """Test handling of corrupted files"""
        # Corrupted CSV
        file = mock_file("col1,col2\n1,2,3\n4,5", "test.csv", "text/csv")
        fetcher = FileFetcher(file)
        df, message = fetcher.fetch_file()
        assert df is None or isinstance(df, pd.DataFrame)

        # Corrupted JSON
        file = mock_file("{invalid_json}", "test.json", "application/json")
        fetcher = FileFetcher(file)
        df, message = fetcher.fetch_file()
        assert df is None
        assert "error" in message.lower()

    @pytest.mark.parametrize("file_format,content", [
        ("csv", "col1,col2\n1,2"),
        ("json", '{"col1":[1],"col2":[2]}'),
        ("xlsx", b"mock_xlsx_content"),
        ("parquet", b"mock_parquet_content")
    ])
    def test_different_file_formats(self, mock_file, file_format, content):
        """Test handling of different file formats"""
        file = mock_file(content, f"test.{file_format}", f"application/{file_format}")
        fetcher = FileFetcher(file)

        with patch(f"pandas.read_{file_format}") as mock_read:
            mock_read.return_value = pd.DataFrame({"col1": [1], "col2": [2]})
            df, message = fetcher.fetch_file()
            assert isinstance(df, pd.DataFrame)
            assert "success" in message.lower()

    def test_performance_large_files(self, mock_file):
        """Test performance with large files"""
        import time

        # Generate large CSV content
        rows = 100000
        content = "col1,col2\n" + "\n".join([f"{i},{i + 1}" for i in range(rows)])
        file = mock_file(content, "test.csv", "text/csv")

        fetcher = FileFetcher(file)
        start_time = time.time()
        df, message = fetcher.load_file_in_chunks()
        duration = time.time() - start_time

        assert isinstance(df, pd.DataFrame)
        assert len(df) == rows
        assert duration < 30  # Should process within 30 seconds

    def test_memory_usage(self, mock_file):
        """Test memory usage with large files"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Generate large CSV content
        rows = 100000
        content = "col1,col2\n" + "\n".join([f"{i},{i + 1}" for i in range(rows)])
        file = mock_file(content, "test.csv", "text/csv")

        fetcher = FileFetcher(file)
        df, message = fetcher.load_file_in_chunks()

        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB

        assert memory_increase < 1000  # Memory increase should be less than 1GB