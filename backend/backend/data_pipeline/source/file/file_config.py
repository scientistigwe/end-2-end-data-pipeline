import os


class Config:
    """Configuration and validation for file uploads."""
    ALLOWED_FORMATS = ['csv', 'json', 'parquet', 'xlsx']
    FILE_SIZE_THRESHOLD_MB = 50  # Default threshold for file size
    ENCODING = 'utf-8'  # Default encoding for reading files
    CHUNK_SIZE = 10000  # Default chunk size for large files

    def __init__(self, **kwargs):
        """
        Initializes the Config class, allowing overrides for configuration attributes.

        Args:
            **kwargs: Keyword arguments to override default configurations
        """
        for key, value in kwargs.items():
            if hasattr(Config, key):
                setattr(Config, key, value)

    @classmethod
    def allowed_file(cls, filename):
        """
        Checks if the uploaded file has an allowed extension.

        Args:
            filename (str): Name of the file to validate

        Returns:
            bool: True if file extension is allowed, False otherwise
        """
        return ('.' in filename and
                filename.rsplit('.', 1)[1].lower() in cls.ALLOWED_FORMATS)

    @classmethod
    def validate_file_size(cls, file, max_size_mb=None):
        """
        Validate file size against maximum allowed size.

        Args:
            file: File object to check
            max_size_mb (float, optional): Maximum file size in MB. 
                                           Defaults to class threshold.

        Returns:
            bool: True if file size is within limit, False otherwise
        """
        max_size = max_size_mb or cls.FILE_SIZE_THRESHOLD_MB
        file.seek(0, os.SEEK_END)
        file_size = file.tell() / (1024 * 1024)
        file.seek(0)
        return file_size <= max_size