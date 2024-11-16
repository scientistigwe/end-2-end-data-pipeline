import logging
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.config import Config
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_fetcher import FileFetcher
import os
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self, file_path: str, file_format: str = None, required_columns: list = None,
                 is_directory: bool = False):
        """
        Initializes the FileManager with the file path, format, and required columns.

        Args:
            file_path: Path to the file or directory to process.
            file_format: Expected format (optional).
            required_columns: List of required columns for validation (optional).
            is_directory: Whether the path points to a directory (optional).
        """
        self.file_path = file_path
        self.file_format = file_format
        self.required_columns = required_columns
        self.is_directory = is_directory
        self.fetcher = FileFetcher(file_path, file_format, required_columns, is_directory)

    def get_file_metadata(self) -> dict:
        """
        Extracts metadata about the file for sending to the React frontend.

        Returns:
            dict: Metadata information, including format, size, columns, etc.
        """
        try:
            files, message = self.fetcher.fetch_file()

            if not files:
                return {"error": message}

            metadata = {
                "file_path": self.file_path,
                "file_size_mb": self.fetcher.file_size_mb,
                "file_format": os.path.splitext(self.file_path)[1].lower(),
                "file_count": len(files) if self.is_directory else 1,
                "valid_columns": self.required_columns,
            }

            logger.info(f"File metadata: {metadata}")
            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {"error": f"Error extracting metadata: {str(e)}"}

    def prepare_for_orchestrator(self) -> dict:
        """
        Prepares the file(s) for orchestration, either as a DataFrame or Parquet.

        Returns:
            dict: Processed file data or file path for Parquet.
        """
        try:
            files, message = self.fetcher.fetch_file()

            if not files:
                return {"error": message}

            # Decide on whether to load as DataFrame or save as Parquet based on size and criteria
            if self.fetcher.file_size_mb > Config.FILE_SIZE_THRESHOLD_MB:
                # Save as Parquet if file is too large
                output_path = os.path.join(Config.STAGING_AREA, "output.parquet")
                self._save_as_parquet(files, output_path)
                return {
                    "status": "success",
                    "message": "File saved as Parquet.",
                    "file_path": output_path
                }

            # Else, load and return DataFrame
            df, message = self.fetcher.load_file(self.file_path)
            if df is not None:
                return {
                    "status": "success",
                    "message": "File loaded as DataFrame.",
                    "data": df.to_dict(orient="records")  # Send DataFrame as JSON
                }
            else:
                return {"error": message}

        except Exception as e:
            logger.error(f"Error preparing file for orchestrator: {str(e)}")
            return {"error": f"Error preparing file: {str(e)}"}

    def _save_as_parquet(self, files, output_path: str):
        """
        Saves the loaded files as a Parquet file in the specified output path.

        Args:
            files: List of files to be processed.
            output_path: Path to save the Parquet file.
        """
        try:
            df = pd.concat([self.fetcher.load_file(file)[0] for file in files], ignore_index=True)
            df.to_parquet(output_path, index=False)
            logger.info(f"Parquet file saved at {output_path}")
        except Exception as e:
            logger.error(f"Error saving files as Parquet: {str(e)}")
            raise
