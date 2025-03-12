# api/fastapi_app/middleware/base.py

from typing import Any
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class BaseMiddleware(BaseHTTPMiddleware):
    """Base middleware class for all custom middlewares"""

    async def dispatch(
            self,
            request: Request,
            call_next: RequestResponseEndpoint
    ) -> Response:
        """Abstract method to be implemented by child classes"""
        raise NotImplementedError()