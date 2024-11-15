import logging
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_loader import FileLoader
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator import FileValidator

# Set up logging for the script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_file_source(file_path: str, required_columns: list = None) -> dict:
    """
    Handles file validation, loading, and processing.

    Args:
        file_path: Path to the file to process
        required_columns: List of required columns in the file

    Returns:
        dict: Processing results including validation status and data
    """
    try:
        # Step 1: Load the file using the FileLoader
        loader = FileLoader(file_path=file_path, required_columns=required_columns)
        df = loader.load_file()  # Remove the file_path parameter here

        # Log successful data loading
        logger.info("Data loaded successfully")

        # Step 2: Initialize the FileValidator with required columns and validate
        validator = FileValidator(required_columns=required_columns)
        validation_results = validator.validate_file(df)

        # Step 3: Process validation results
        quality_gauge = validation_results.get("quality_gauge", 0)
        validation_details = validation_results.get("validation_results", {})

        # Log validation results
        if quality_gauge < 90:
            logger.warning(f"File quality gauge is below 90%. Quality: {quality_gauge}")
            logger.warning(f"Validation results: {validation_details}")
        else:
            logger.info(f"File validation passed with quality gauge of {quality_gauge}%")

        # Step 4: Handle empty data case
        if df.empty:
            logger.warning("Loaded data is empty")

        return {
            "validation_results": validation_results,
            "data": df,
            "success": quality_gauge >= 90 and not df.empty
        }

    except Exception as e:
        logger.error(f"Error occurred while processing file: {str(e)}")
        raise
