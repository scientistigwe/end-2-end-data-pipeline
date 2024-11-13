# data_ingestion_manager.py
from typing import Dict, Any
import logging


class DataIngestionManager:
    def __init__(self, validator: DataValidator):
        self.validator = validator
        self.logger = logging.getLogger(__name__)

    def process_data(self, file_path: str, source_type: DataSourceType, schema_name: str) -> Dict[str, Any]:
        try:
            # Create data source and read data
            data_source = DataSource(file_path, source_type)
            data = data_source.read_data()

            # Validate data
            validation_result = self.validator.validate_data(data, schema_name)

            if validation_result.status == ValidationStatus.SUCCESS:
                # Process the data further if needed
                return {
                    "status": "success",
                    "message": "Data processed successfully",
                    "rows_processed": len(data)
                }
            else:
                return {
                    "status": "error",
                    "message": validation_result.message,
                    "details": validation_result.details
                }

        except Exception as e:
            self.logger.error(f"Error processing data: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing data: {str(e)}"
            }


