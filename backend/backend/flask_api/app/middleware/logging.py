# app/middleware/logging.py
import logging
import time
from flask import request, g


class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('request_logger')

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')

        # Start timer
        start_time = time.time()

        def custom_start_response(status, headers, exc_info=None):
            duration = time.time() - start_time
            status_code = int(status.split()[0])

            self.logger.info(
                f"Request: {method} {path} "
                f"Status: {status_code} "
                f"Duration: {duration:.2f}s"
            )
            return start_response(status, headers, exc_info)

        return self.app(environ, custom_start_response)


