class Config:
    FILE_SIZE_THRESHOLD_MB = 50  # Default threshold
    CHUNK_SIZE = 10000  # Default chunk size
    ALLOWED_FORMATS = ['csv', 'json', 'parquet', 'xlsx']
    ENCODING = 'utf-8'  # Add this if needed by the tests or file reading logic

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(Config, key):  # Ensure we reference class attributes
                setattr(Config, key, value)
