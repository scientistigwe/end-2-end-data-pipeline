from message_broker import MessageBroker
from backend.backend.data_pipeline.analysis.data_quality_gauge import DataQualityGauge
from backend.backend.data_pipeline.analysis.data_quality_report import DataQualityReport
from backend.backend.data_pipeline.analysis.insight_report import InsightReport
import pandas as pd


class DataConductor:
    """
    Data conductor that processes the staged data, moves it through the pipeline,
    and handles user interactions for decisions at each stage.
    """

    def __init__(self, message_broker: MessageBroker,
                 quality_gauge: DataQualityGauge,
                 quality_report: DataQualityReport,
                 insight_report: InsightReport):
        """
        Initializes the DataConductor with the necessary components for data processing and communication.

        Args:
            message_broker (MessageBroker): The message broker instance that handles user communication.
            quality_gauge (DataQualityGauge): Data quality assessment.
            quality_report (DataQualityReport): Data quality report generator.
            insight_report (InsightReport): Data insight report generator.
        """
        self.message_broker = message_broker
        self.quality_gauge = quality_gauge
        self.quality_report = quality_report
        self.insight_report = insight_report

    def process_data(self, staging_id: str, data: pd.DataFrame, user_input: dict):
        """
        Processes the data through various pipeline stages.

        Args:
            staging_id (str): The ID of the staged data.
            data (pd.DataFrame): The actual data to process.
            user_input (dict): A dictionary containing user inputs at various stages.
        """
        print(f"Processing data for staging ID: {staging_id}")

        # Step 1: Data Quality Assessment
        self._data_quality_stage(data)

        # Step 2: Transformation based on recommendations
        self._transformation_stage(data)

        # Step 3: Insight Generation (based on user objectives)
        self._insight_generation(data, user_input)

        # Step 4: Loading Stage (final decision to load)
        self._loading_stage(data)

    def _data_quality_stage(self, data: pd.DataFrame):
        """
        Evaluate and communicate data quality issues to the user.

        Args:
            data (pd.DataFrame): The data to assess.
        """
        quality_metrics = self.quality_gauge.assess_data_quality(data)
        quality_report = self.quality_report.generate_report(data)

        self.message_broker.send_message("Data quality assessment completed.")
        self.message_broker.send_message(f"Data Quality Metrics: {quality_metrics}")

        self.message_broker.send_message("Please review the detailed data quality report.")
        self.message_broker.send_message(quality_report)

        # Ask user decision (e.g., continue or fix data)
        decision = self.message_broker.ask_user("Do you want to proceed with the data quality as is?",
                                                choices=["yes", "no"])

        if decision == "no":
            self._handle_data_quality_issues(data)

    def _handle_data_quality_issues(self, data: pd.DataFrame):
        """
        Handle issues based on data quality assessment (e.g., missing values, duplicates).

        Args:
            data (pd.DataFrame): The data to fix.
        """
        print("Handling data quality issues...")
        # Simple handling: Fill missing values, drop duplicates
        data.fillna(0, inplace=True)
        data.drop_duplicates(inplace=True)
        self.message_broker.send_message("Data quality issues addressed.")

    def _transformation_stage(self, data: pd.DataFrame):
        """
        Perform data transformation based on user input.

        Args:
            data (pd.DataFrame): The data to transform.
        """
        self.message_broker.send_message("Transformation stage started.")
        # Add transformations here (e.g., scaling, encoding)
        data *= 2  # Placeholder transformation

    def _insight_generation(self, data: pd.DataFrame, user_input: dict):
        """
        Generate insights based on the user's project objectives.

        Args:
            data (pd.DataFrame): The data to analyze.
            user_input (dict): User's project objectives.
        """
        objective = user_input.get("objective", "summary")
        insight = self.insight_report.generate_insight(data, objective)
        self.message_broker.send_message(f"Insight Report: {insight}")

    def _loading_stage(self, data: pd.DataFrame):
        """
        Load the processed data to its final destination.

        Args:
            data (pd.DataFrame): The processed data.
        """
        decision = self.message_broker.ask_user("Do you want to load the data to the final destination?",
                                                choices=["yes", "no"])

        if decision == "yes":
            print("Loading the data...")
            # Implement data loading logic (e.g., save to database)
            self.message_broker.send_message("Data successfully loaded.")
        else:
            self.message_broker.send_message("Data loading cancelled.")
