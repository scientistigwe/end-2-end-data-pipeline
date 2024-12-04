# app/utils/response_builder.py
from typing import Any, Dict, Optional, Tuple, Union


class ResponseBuilder:
    @staticmethod
    def success(
            data: Optional[Dict[str, Any]] = None,
            message: Optional[str] = None,
            status_code: int = 200
    ) -> Tuple[Dict[str, Any], int]:
        response = {
            'success': True
        }
        if message:
            response['message'] = message
        if data is not None:
            response['data'] = data
        return response, status_code

    @staticmethod
    def error(
            message: str,
            details: Optional[Dict[str, Any]] = None,
            status_code: int = 400
    ) -> Tuple[Dict[str, Any], int]:
        response = {
            'success': False,
            'error': {
                'message': message
            }
        }
        if details:
            response['error']['details'] = details
        return response, status_code