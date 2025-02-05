# fastapi_app/utils/response_builder.py
from typing import Any, Dict, Optional, Tuple, Union


class ResponseBuilder:
    @staticmethod
    def success(
            data: Optional[Dict[str, Any]] = None,
            message: Optional[str] = None,
            status_code: int = 200
    ) -> Tuple[Dict[str, Any], int]:
        """Build a successful response"""
        response = {
            'success': True,
            'message': message or 'Operation successful',
            'data': data or {}
        }
        return response, status_code

    @staticmethod
    def error(
            message: str,
            details: Optional[Dict[str, Any]] = None,
            status_code: int = 400
    ) -> Tuple[Dict[str, Any], int]:
        """Build an error response"""
        response = {
            'success': False,
            'message': message,
            'error': {
                'message': message,
                'details': details or {}
            }
        }
        return response, status_code