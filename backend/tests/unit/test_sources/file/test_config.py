from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.config import Config

# Test default configuration
def test_default_config():
    config = Config()
    assert config.FILE_SIZE_THRESHOLD_MB == 50  # Assuming this is the default value
    assert config.CHUNK_SIZE == 10000  # Assuming this is the default value
    assert config.ENCODING == "utf-8"

# Test custom configuration
def test_custom_config():
    custom_config = Config(FILE_SIZE_THRESHOLD_MB=100, CHUNK_SIZE=20000, ENCODING="latin-1")
    assert custom_config.FILE_SIZE_THRESHOLD_MB == 100
    assert custom_config.CHUNK_SIZE == 20000
    assert custom_config.ENCODING == "latin-1"
