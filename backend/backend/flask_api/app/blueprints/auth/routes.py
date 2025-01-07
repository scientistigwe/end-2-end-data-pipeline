from flask import Blueprint, request, make_response, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token, get_jwt
from marshmallow import ValidationError
from datetime import datetime
from ...schemas.auth import (
    LoginRequestSchema,
    RegisterRequestSchema,
    PasswordResetRequestSchema,
    EmailVerificationRequestSchema,
    ChangePasswordRequestSchema,
    UserProfileResponseSchema
)
from ...services.auth import AuthService
from ...utils.response_builder import ResponseBuilder
import logging
from ...utils.route_registry import APIRoutes

refresh_path = APIRoutes.AUTH_REFRESH.value.path

logger = logging.getLogger(__name__)

def create_auth_blueprint(auth_service: AuthService, db_session):
    """Create auth blueprint with all routes."""
    auth_bp = Blueprint('auth', __name__)

    def set_tokens_as_cookies(response, user_id):
        """Helper function to set access and refresh tokens as HTTP-only cookies."""
        access_token = create_access_token(identity=str(user_id))
        refresh_token = create_refresh_token(identity=str(user_id))
        
        cookie_settings = {
            'httponly': True,
            'secure': False,  # Set to True in production with HTTPS
            'samesite': 'Lax',
            'path': '/',
            'domain': None  # Allow browser to handle domain
        }

        response.set_cookie('access_token', access_token, **cookie_settings)
        response.set_cookie('refresh_token', refresh_token, **cookie_settings)
        return response

    def clear_tokens_from_cookies(response):
        """Helper function to clear access and refresh tokens from cookies."""
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

    # Public Routes
    @auth_bp.route('/register', methods=['POST'])
    def register():
        """Register a new user."""
        try:
            schema = RegisterRequestSchema()
            data = schema.load(request.get_json())
            
            if auth_service.get_user_by_email(data['email']):
                return ResponseBuilder.error("Email already registered", status_code=409)
            
            user = auth_service.register_user(data)
            
            response = ResponseBuilder.success(
                data={"message": "Registration successful", "registered_at": datetime.utcnow().isoformat()}
            )
            return set_tokens_as_cookies(make_response(jsonify(response)), user.id)
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Registration failed", status_code=500)

    @auth_bp.route('/login', methods=['POST'])
    def login():
        try:
            schema = LoginRequestSchema()
            data = schema.load(request.get_json())
            
            user = auth_service.authenticate_user(data['email'], data['password'])
            if not user:
                return ResponseBuilder.error("Invalid credentials", status_code=401)
            
            # Create tokens
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            # Create response
            response = make_response(
                ResponseBuilder.success({
                    "message": "Login successful",
                    "user": UserProfileResponseSchema().dump(user),
                    "logged_in_at": datetime.utcnow().isoformat()
                })
            )
            
            # Set cookies with exact names
            cookie_settings = {
                'httponly': True,
                'secure': current_app.config['JWT_COOKIE_SECURE'],
                'samesite': current_app.config['JWT_COOKIE_SAMESITE']
            }
            
            # Set access token cookie
            response.set_cookie(
                current_app.config['JWT_ACCESS_COOKIE_NAME'],  # Will be 'access_token'
                value=access_token,
                max_age=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds(),
                path='/',
                **cookie_settings
            )
            
            # Set refresh token cookie
            response.set_cookie(
                current_app.config['JWT_REFRESH_COOKIE_NAME'],  # Will be 'refresh_token'
                value=refresh_token,
                max_age=current_app.config['JWT_REFRESH_TOKEN_EXPIRES'].total_seconds(),
                path='/api/v1/auth/refresh',
                **cookie_settings
            )
            
            return response
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Login failed", status_code=500)
        
    @auth_bp.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        """Refresh access token using refresh token."""
        try:
            current_user_id = get_jwt_identity()
            
            response = ResponseBuilder.success({
                "message": "Token refreshed",
                "refreshed_at": datetime.utcnow().isoformat()
            })
            
            # Create response with new access token
            response = make_response(jsonify(response))
            
            # Set new access token cookie
            access_token = create_access_token(identity=current_user_id)
            response.set_cookie(
                'access_token',
                value=access_token,
                max_age=current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds(),
                secure=current_app.config['JWT_COOKIE_SECURE'],
                httponly=True,
                path='/',
                samesite='Lax' if current_app.debug else 'Strict'
            )
            
            return response
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to refresh token", status_code=500)
        
    @auth_bp.route('/logout', methods=['POST'])
    @jwt_required()
    def logout():
        """Logout user and clear tokens."""
        try:
            token_jti = get_jwt()['jti']
            auth_service.invalidate_token(token_jti)
            response = ResponseBuilder.success({"message": "Logout successful", "logged_out_at": datetime.utcnow().isoformat()})
            return clear_tokens_from_cookies(make_response(jsonify(response)))
        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Logout failed", status_code=500)

    @auth_bp.route('/forgot-password', methods=['POST'])
    def forgot_password():
        """Initiate password reset process."""
        try:
            schema = PasswordResetRequestSchema()
            data = schema.load(request.get_json())
            auth_service.initiate_password_reset(data['email'])
            return ResponseBuilder.success({"message": "Password reset instructions sent"})
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password reset initiation error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to initiate password reset", status_code=500)

    @auth_bp.route('/reset-password', methods=['POST'])
    def reset_password():
        """Reset user's password using reset token."""
        try:
            data = request.get_json()
            auth_service.reset_password(data['token'], data['new_password'])
            return ResponseBuilder.success({"message": "Password reset successful"})
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Password reset failed", status_code=500)

    @auth_bp.route('/profile', methods=['GET'])
    @jwt_required()
    def get_profile():
        """Get user's profile information."""
        try:
            current_user_id = get_jwt_identity()
            user = auth_service.get_user_by_id(current_user_id)
            
            if not user:
                return ResponseBuilder.error("User not found", status_code=404)
            
            return ResponseBuilder.success({
                "user": UserProfileResponseSchema().dump(user)
            })
        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to fetch profile", status_code=500)
        
    @auth_bp.route('/profile', methods=['PUT'])
    @jwt_required()
    def update_profile():
        """Update user's profile information."""
        try:
            current_user_id = get_jwt_identity()
            schema = UserProfileResponseSchema()
            data = schema.load(request.get_json())
            updated_user = auth_service.update_user_profile(current_user_id, data)
            return ResponseBuilder.success({"user": schema.dump(updated_user), "updated_at": datetime.utcnow().isoformat()})
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to update profile", status_code=500)

    @auth_bp.route('/verify-email', methods=['POST'])
    def verify_email():
        """Verify user's email address."""
        try:
            schema = EmailVerificationRequestSchema()
            data = schema.load(request.get_json())
            auth_service.verify_email(data['token'])
            return ResponseBuilder.success({"message": "Email verified successfully"})
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Email verification error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Email verification failed", status_code=500)

    @auth_bp.route('/change-password', methods=['POST'])
    @jwt_required()
    def change_password():
        """Change user's password."""
        try:
            current_user_id = get_jwt_identity()
            schema = ChangePasswordRequestSchema()
            data = schema.load(request.get_json())
            auth_service.change_password(current_user_id, data['current_password'], data['new_password'])
            return ResponseBuilder.success({"message": "Password changed successfully"})
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password change error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to change password", status_code=500)

    return auth_bp
