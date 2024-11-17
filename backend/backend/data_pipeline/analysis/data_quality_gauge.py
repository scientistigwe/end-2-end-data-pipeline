import pandas as pd

class DataQualityGauge:
    """
    Data quality gauge that evaluates the quality of the data based on various metrics such as
    missing values, duplicates, and others.
    """

    def assess_data_quality(self, data: pd.DataFrame) -> dict:
        """
        Assesses the quality of the data.

        Args:
            data (pd.DataFrame): The data to assess.

        Returns:
            dict: A dictionary with quality metrics such as missing values and duplicates.
        """
        quality_metrics = {
            'null_values': data.isnull().sum().to_dict(),
            'duplicate_count': data.duplicated().sum()
        }
        return quality_metrics
