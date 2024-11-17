import pandas_profiling
import pandas as pd

class DataQualityReport:
    """
    Generates a comprehensive data quality report using pandas profiling.
    """

    def generate_report(self, data: pd.DataFrame) -> str:
        """
        Generates a detailed data quality report using pandas profiling.

        Args:
            data (pd.DataFrame): The data to generate the report for.

        Returns:
            str: A HTML report as a string.
        """
        profile = pandas_profiling.ProfileReport(data)
        return profile.to_html()
