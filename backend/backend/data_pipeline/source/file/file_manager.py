import logging
import pandas as pd
from .file_config import Config
from .file_fetcher import FileFetcher
import io

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, file, file_format: str = None):
        """
        Initializes the FileManager with the file and format.

        Args:
            file: File object (in-memory).
            file_format: Expected format (optional).
        """
        self.file = file
        self.file_format = file_format
        self.fetcher = FileFetcher(file, file_format)

    def get_file_metadata(self) -> dict:
        """
        Extracts metadata about the uploaded file for sending to the React frontend.

        Returns:
            dict: Metadata information, including format, size, columns, etc.
        """
        try:
            df, message = self.fetcher.fetch_file()
            if df is None:
                return {"error": message}

            metadata = {
                "file_size_mb": self.fetcher.file_size_mb,
                "file_format": self.file_format or 'unknown',
                "columns": df.columns.tolist(),
                "row_count": len(df)
            }

            return metadata
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {"error": f"Error extracting metadata: {str(e)}"}

    def prepare_for_orchestrator(self) -> dict:
        """
        Prepares the uploaded file for orchestration, either as a DataFrame or in-memory Parquet.

        Returns:
            dict: Processed file data or in-memory Parquet file.
        """
        try:
            # Fetch file as DataFrame
            df, message = self.fetcher.fetch_file()
            if df is None:
                return {"error": message}

            logger.info(f"Processing file: {self.file} | Size: {self.fetcher.file_size_mb}MB | Format: {self.file_format or 'unknown'}")

            # Decide on whether to load as DataFrame or save as in-memory Parquet
            if self.fetcher.file_size_mb > Config.FILE_SIZE_THRESHOLD_MB:
                # Save as in-memory Parquet if file is too large
                parquet_buffer = self._save_as_parquet_in_memory(df)
                return {
                    "status": "success",
                    "message": "File converted to in-memory Parquet.",
                    "parquet_data": parquet_buffer.getvalue()  # Send the buffer content as bytes
                }

            # Return DataFrame as JSON if within size threshold
            return {
                "status": "success",
                "message": "File loaded as DataFrame.",
                "data": df.to_dict(orient="records")
            }

        except Exception as e:
            logger.error(f"Error preparing file for orchestrator: {str(e)}")
            return {"error": f"Error preparing file: {str(e)}"}

    def _save_as_parquet_in_memory(self, df: pd.DataFrame) -> io.BytesIO:
        """
        Saves the DataFrame as an in-memory Parquet file.

        Args:
            df: DataFrame to be saved.

        Returns:
            io.BytesIO: In-memory Parquet file as a BytesIO object.
        """
        try:
            buffer = io.BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)  # Reset buffer position to the beginning
            logger.info(f"Parquet file created in memory.")
            return buffer
        except Exception as e:
            logger.error(f"Error saving DataFrame as in-memory Parquet: {str(e)}")
            raise

    def fetch_data(self, source_details: dict) -> dict:
        """
        Fetches the data from the file source and prepares it for the orchestrator.

        Args:
            source_details (dict): Source details required to fetch data.

        Returns:
            dict: The processed data (either as DataFrame or in-memory Parquet).
        """
        try:
            logger.info(f"Fetching data from source: {source_details.get('source_id', 'unknown')}")

            # Prepare data for orchestrator
            return self.prepare_for_orchestrator()
        except Exception as e:
            logger.error(f"Error fetching data from source: {str(e)}")
            return {"error": f"Error fetching data: {str(e)}"}
