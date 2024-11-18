from backend.backend.data_pipeline.source.file.file_manager import FileManager
from backend.backend.data_pipeline.source.api.api_manager import ApiManager
from backend.backend.data_pipeline.source.stream.stream_manager import StreamManager
from backend.backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager
from backend.backend.data_pipeline.source.database.db_data_manager import DBDataManager
from backend.backend.core.staging.staging_area import StagingArea
from backend.backend.data_pipeline.analysis.data_quality_gauge import DataQualityGate
from backend.backend.core.orchestration.conductor import DataConductor
from backend.backend.core.messaging.broker import MessageBroker
from typing import Dict, Any, Optional

class DataOrchestrator:
    """
    Main orchestrator that manages the flow of data through the pipeline.
    It interacts with different source managers (File, API, Stream, Cloud, Database) 
    to fetch data, pass it through various stages like Staging, Quality Gate, 
    and Data Conductor, and provides messaging updates to the user.
    """

    def __init__(self, source_manager_type: str, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the DataOrchestrator with the specified source manager type and configuration.

        Args:
            source_manager_type (str): The type of the source manager (e.g., 'file', 'api').
            config (Optional[Dict[str, Any]], optional): Optional configuration for source managers.
        """
        self.source_manager = self._get_source_manager(source_manager_type)
        self.config = config if config else {}

        self.staging_area = StagingArea()
        self.data_quality_gate = DataQualityGate()
        self.data_conductor = DataConductor()
        self.message_broker = MessageBroker()

    def _get_source_manager(self, source_manager_type: str):
        """
        Returns the appropriate source manager based on the source type.

        Args:
            source_manager_type (str): The type of the source manager (e.g., 'file', 'api').

        Raises:
            ValueError: If an invalid source manager type is provided.
        """
        if source_manager_type == "file":
            return FileManager(self.config)
        elif source_manager_type == "api":
            return ApiManager(self.config)
        elif source_manager_type == "stream":
            return StreamManager(self.config)
        elif source_manager_type == "cloud":
            return S3DataManager(self.config)
        elif source_manager_type == "database":
            return DBDataManager(self.config)
        else:
            raise ValueError("Invalid source manager type")

    def ingest_data(self, source_details: Dict[str, Any]):
        """
        Ingests data from the specified source and processes it through the pipeline.

        Args:
            source_details (Dict[str, Any]): The details required to fetch data from the source.

        The data goes through the following stages:
            - Staging Area: Temporarily stores data.
            - Quality Gate: Checks data quality and triggers processing if quality is acceptable.
            - Data Conductor: Processes and redirects the data to the next stage.
            - Message Broker: Sends updates to the user.
        """
        # Fetch data from the selected source
        data = self.source_manager.fetch_data(source_details)
        source_id = source_details.get("source_id", "unknown_source")

        # Stage the data
        staging_id = self.staging_area.stage_data(data, source_id, source_details)

        # Check data quality
        quality_score = self.data_quality_gate.check_quality(staging_id)

        # If quality is acceptable, proceed with processing; otherwise, hold in the staging area
        if quality_score >= 90:
            self.message_broker.send_message(f"Data quality is good. Proceeding with processing.")
            self.data_conductor.process_data(staging_id)
        else:
            self.message_broker.send_message(f"Data quality is poor (Score: {quality_score}). Holding in Staging Area.")
            self.staging_area.update_status(staging_id, "FAILED")

    def retrieve_staging_metadata(self, staging_id: str):
        """
        Retrieves metadata for the specified staging ID.

        Args:
            staging_id (str): The ID of the staged data.

        Returns:
            StagingMetadata: Metadata related to the staged data.
        """
        return self.staging_area.get_metadata(staging_id)
