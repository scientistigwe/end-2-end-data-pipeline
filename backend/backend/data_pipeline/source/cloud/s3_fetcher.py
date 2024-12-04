import logging
import pandas as pd
from io import BytesIO
from backend.data_pipeline.exceptions import CloudQueryError

logger = logging.getLogger(__name__)

class S3DataLoader:
    def __init__(self, s3_connector):
        self.s3_connector = s3_connector

    def load_data(self, bucket_name, key, data_format='pandas'):
        try:
            self.s3_connector.connect()
            obj = self.s3_connector.s3.Object(bucket_name, key).get()['Body'].read()
            buffer = BytesIO(obj)

            if data_format == 'pandas':
                df = pd.read_csv(buffer)
            elif data_format == 'parquet':
                df = pd.read_parquet(buffer)
            else:
                raise ValueError("Unsupported data format. Choose 'pandas' or 'parquet'.")

            logger.info(f"Data loaded successfully from bucket '{bucket_name}', key '{key}'.")
            return df

        except Exception as e:
            logger.error(f"Error loading data from S3: {str(e)}")
            raise CloudQueryError(str(e))
        finally:
            self.s3_connector.close()
