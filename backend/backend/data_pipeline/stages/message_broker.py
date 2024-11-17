class MessageBroker:
    """
    Message broker that handles sending updates about the data flow in the pipeline.
    It provides real-time messages to the user about the current status of the data.
    """

    def send_message(self, message: str):
        """
        Sends a message to the user about the data flow status.

        Args:
            message (str): The message to be sent to the user.
        """
        print(f"Message: {message}")

    def ask_user(self, prompt: str, choices: list) -> str:
        """
        Asks the user for a decision and returns their response.

        Args:
            prompt (str): The question to ask the user.
            choices (list): A list of choices for the user to select from.

        Returns:
            str: The user's response.
        """
        print(f"{prompt} Options: {', '.join(choices)}")
        # Simulate user input for now, replace with real input gathering in production
        return choices[0]  # Always select the first choice for testing purposes
