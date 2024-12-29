# app/middleware/auth_middleware.py
from functools import wraps
from flask import g, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from ..services.auth import AuthService

def auth_middleware():
    def middleware():
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # Get auth service and set current user in g
            auth_service = AuthService(g.db)
            g.current_user = auth_service.get_user_by_id(user_id)
            
        except Exception as e:
            # Let the error handlers deal with it
            pass

    return middleware

def jwt_required_with_user():
    """Custom decorator that combines jwt_required and sets current user"""
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # Get auth service and set current user in g
            auth_service = AuthService(g.db)
            g.current_user = auth_service.get_user_by_id(user_id)
            
            return fn(*args, **kwargs)
        return decorator
    return wrapper