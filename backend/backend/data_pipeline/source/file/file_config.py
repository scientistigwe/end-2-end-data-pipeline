class Config:
    FILE_SIZE_THRESHOLD_MB = 50  # Default threshold for file size (in MB)
    CHUNK_SIZE = 10000  # Default chunk size for large files (in rows)
    ALLOWED_FORMATS = ['csv', 'json', 'parquet', 'xlsx']  # Supported file formats
    ENCODING = 'utf-8'  # Default encoding for reading files

    def __init__(self, **kwargs):
        """
        Initializes the Config class, allowing overrides for configuration attributes.
        """
        for key, value in kwargs.items():
            if hasattr(Config, key):  # Ensure we reference class attributes
                setattr(Config, key, value)

    @staticmethod
    def allowed_file(filename):
        """
        Checks if the uploaded file has an allowed extension.
        Returns True if the file extension is in ALLOWED_FORMATS, False otherwise.
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_FORMATS
