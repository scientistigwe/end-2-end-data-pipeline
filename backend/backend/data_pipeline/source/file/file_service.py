# file_service.py
from .file_manager import FileManager
from backend.core.messaging.broker import MessageBroker

class FileService:
    def __init__(self):
        self.message_broker = MessageBroker()
        self.file_manager = FileManager(self.message_broker)

    @staticmethod
    def handle_file_upload(file_content, filename):
        """
        Service layer method to handle file uploads.
        Delegates actual processing to FileManager.
        """
        file_obj = type('FileObj', (), {
            'read': lambda *args: file_content,
            'filename': filename
        })()

        message_broker = MessageBroker()
        manager = FileManager(message_broker)
        return manager.process_file(file_obj)

    @staticmethod
    def get_file_metadata(file_content, filename):
        """
        Service layer method to get file metadata.
        Delegates to FileManager.
        """
        file_obj = type('FileObj', (), {
            'read': lambda *args: file_content,
            'filename': filename
        })()

        message_broker = MessageBroker()
        manager = FileManager(message_broker)
        return manager.get_metadata(file_obj)