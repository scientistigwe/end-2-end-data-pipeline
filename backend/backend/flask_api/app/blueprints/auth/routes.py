# app/blueprints/auth/routes.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from marshmallow import ValidationError
from ...schemas.auth import LoginSchema, RegisterSchema, TokenResponseSchema
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        schema = RegisterSchema()
        data = schema.load(request.get_json())
        # Implementation details
        return ResponseBuilder.success({"message": "User registered successfully"})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        schema = LoginSchema()
        data = schema.load(request.get_json())
        access_token = create_access_token(identity=user_id)
        refresh_token = create_refresh_token(identity=user_id)
        return ResponseBuilder.success({
            'access_token': access_token,
            'refresh_token': refresh_token
        })
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return ResponseBuilder.success({'access_token': access_token})

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Implementation for token invalidation
    return ResponseBuilder.success({"message": "Successfully logged out"})