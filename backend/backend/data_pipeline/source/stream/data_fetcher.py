"""
data_loader.py

Loads data from the established stream connection.
"""

from .stream_connector import StreamConnector
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


class DataLoader:
    def __init__(self, connector):
        """
        Initializes the data loader with a given stream connector.

        Args:
            connector (StreamConnector): The connector object to load data from.
        """
        self.connector = connector

    def fetch_data(self):
        """Fetches data from the stream and returns it as a DataFrame or saves as Parquet.

        Returns:
            pd.DataFrame or None: DataFrame if data is small, None if data is saved as Parquet.
        """
        # Placeholder: Simulate fetching data
        data = [{'timestamp': '2024-11-16T12:00:00Z', 'value': 42}, {'timestamp': '2024-11-16T12:01:00Z', 'value': 45}]
        df = pd.DataFrame(data)

        if df.memory_usage(deep=True).sum() > 10 * 1024 * 1024:  # 10 MB threshold
            pq.write_table(pa.Table.from_pandas(df), 'staging_area/stream_data.parquet')
            print("Data saved as Parquet in staging area.")
            return None
        else:
            return df
