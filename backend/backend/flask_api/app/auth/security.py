# app/auth/security.py
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_claims
from flask import jsonify


def role_required(roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt_claims()
            if not set(roles).intersection(set(claims.get('roles', []))):
                return jsonify({'msg': 'Insufficient permissions'}), 403
            return fn(*args, **kwargs)

        return decorator

    return wrapper


def permission_required(permissions):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt_claims()
            if not set(permissions).intersection(set(claims.get('permissions', []))):
                return jsonify({'msg': 'Insufficient permissions'}), 403
            return fn(*args, **kwargs)

        return decorator

    return wrapper
