from dataclasses import dataclass
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone


@dataclass
class StagingMetadata:
    """
    Metadata class that holds information about the staged data.
    """
    source_type: str
    source_id: str
    format: str
    size_bytes: int
    row_count: Optional[int]
    columns: Optional[List[str]]
    tags: Dict[str, str]
    quality_score: float


class StagingArea:
    """
    Staging area for temporarily holding data before it goes through further processing.
    Data is stored in a dictionary and is identified by a unique staging ID.
    """

    def __init__(self):
        """
        Initializes an empty staging area.
        """
        self.staging_area = {}

    def stage_data(self, data: Any, source_id: str, source_details: Dict[str, Any]) -> str:
        """
        Stages the data by generating a unique staging ID and storing the data
        along with metadata and a history of processing steps.

        Args:
            data (Any): The data to be staged.
            source_id (str): The identifier for the source of the data.
            source_details (Dict[str, Any]): The details about the source.

        Returns:
            str: A unique ID for the staged data.
        """
        staging_id = str(datetime.now(timezone.utc).timestamp())
        staging_metadata = StagingMetadata(
            source_type=source_details["source_type"],
            source_id=source_id,
            format="dataframe",  # Placeholder format (can be adjusted based on actual data format)
            size_bytes=len(data),  # Placeholder for actual size calculation
            row_count=len(data),
            columns=data.columns.tolist() if hasattr(data, "columns") else [],
            tags={},
            quality_score=100.0,  # Placeholder quality score
        )

        # Stage the data and initialize its status as 'RECEIVED'
        self.staging_area[staging_id] = {
            "data": data,
            "metadata": staging_metadata,
            "status": "RECEIVED",
            "metadata_history": [{
                "timestamp": datetime.now(timezone.utc),
                "status": "RECEIVED",
                "details": "Data fetched"
            }]
        }
        return staging_id

    def update_status(self, staging_id: str, status: str, details: str = ""):
        """
        Updates the status of the staged data and appends to the metadata history.

        Args:
            staging_id (str): The ID of the staged data.
            status (str): The new status for the staged data (e.g., 'PROCESSING', 'FAILED').
            details (str): Additional details to be recorded for the status update.
        """
        if staging_id in self.staging_area:
            # Update the status of the data and record the metadata history
            self.staging_area[staging_id]["status"] = status
            self.staging_area[staging_id]["metadata_history"].append({
                "timestamp": datetime.now(timezone.utc),
                "status": status,
                "details": details
            })

    def get_metadata(self, staging_id: str) -> Optional[StagingMetadata]:
        """
        Retrieves the metadata for the specified staged data.

        Args:
            staging_id (str): The ID of the staged data.

        Returns:
            Optional[StagingMetadata]: The metadata of the staged data or None if not found.
        """
        return self.staging_area.get(staging_id, {}).get("metadata")

    def cleanup(self, staging_id: str):
        """
        Cleans up the old staged data by deleting it.

        Args:
            staging_id (str): The ID of the staged data to be cleaned up.
        """
        if staging_id in self.staging_area:
            del self.staging_area[staging_id]

    def replace_stage(self, staging_id: str, new_data: Any, new_metadata: StagingMetadata):
        """
        Replaces the current stage with new data and updated metadata.

        Args:
            staging_id (str): The ID of the staged data to be replaced.
            new_data (Any): The new data to stage.
            new_metadata (StagingMetadata): The new metadata associated with the new stage.
        """
        if staging_id in self.staging_area:
            # Replace the old staged data with the new data and metadata
            self.staging_area[staging_id]["data"] = new_data
            self.staging_area[staging_id]["metadata"] = new_metadata
            self.staging_area[staging_id]["status"] = "RECEIVED"  # Set status to 'RECEIVED' initially

            # Append to the metadata history to track the changes
            self.staging_area[staging_id]["metadata_history"].append({
                "timestamp": datetime.now(timezone.utc),
                "status": "RECEIVED",
                "details": "Replaced with new data"
            })


# # Example usage of the StagingArea class
# if __name__ == "__main__":
#     # Simulating a dataframe-like object (for example purposes)
#     import pandas as pd
#
#     data = pd.DataFrame({
#         "Column1": [1, 2, 3],
#         "Column2": ["A", "B", "C"]
#     })
#
#     # Simulating source details
#     source_details = {
#         "source_type": "API",
#         "source_id": "api_123"
#     }
#
#     # Creating an instance of StagingArea
#     staging_area = StagingArea()
#
#     # Stage initial data
#     staging_id = staging_area.stage_data(data, source_id="source_1", source_details=source_details)
#     print(f"Data staged with ID: {staging_id}")
#
#     # Simulate an update of the staged data (after transformation)
#     new_data = pd.DataFrame({
#         "Column1": [4, 5, 6],
#         "Column2": ["X", "Y", "Z"]
#     })
#     new_metadata = StagingMetadata(
#         source_type="API",
#         source_id="source_1",
#         format="dataframe",
#         size_bytes=len(new_data),
#         row_count=len(new_data),
#         columns=new_data.columns.tolist(),
#         tags={"stage": "transformation1"},
#         quality_score=95.0
#     )
#
#     # Replace the current stage with new data and updated metadata
#     staging_area.replace_stage(staging_id, new_data, new_metadata)
#     print(f"Staged data replaced for ID: {staging_id}")
#
#     # Retrieve metadata and print it
#     metadata = staging_area.get_metadata(staging_id)
#     print("Current metadata:", metadata)
#
#     # Cleanup: Remove staged data after processing
#     staging_area.cleanup(staging_id)
#     print(f"Data with ID {staging_id} cleaned up.")
