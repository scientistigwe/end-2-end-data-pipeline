"""
data_manager.py

Manages data operations and prepares it for the orchestrator.
"""

from .data_loader import DataLoader


class DataManager:
    def __init__(self, loader):
        """
        Initializes the data manager with a data loader.

        Args:
            loader (DataLoader): The data loader object to manage data from.
        """
        self.loader = loader

    def manage_data(self):
        """Manages data fetched from the stream and sends it to the orchestrator.

        Returns:
            str: A message indicating the data handling result.
        """
        data = self.loader.fetch_data()
        if data is not None:
            # Send DataFrame to the orchestrator
            print("Sending DataFrame to orchestrator...")
            return "DataFrame sent to orchestrator"
        else:
            # Parquet file is already saved in the staging area
            print("Parquet file is staged for further processing.")
            return "Parquet staged"
