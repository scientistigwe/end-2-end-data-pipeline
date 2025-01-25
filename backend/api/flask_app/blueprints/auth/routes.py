# blueprints/auth/routes.py
from marshmallow import ValidationError
from flask import Blueprint, request, make_response, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token, get_jwt
from datetime import datetime, timedelta
from ...utils.response_builder import ResponseBuilder
from ...schemas.auth import (
    # Auth & Token Schemas
    LoginRequestSchema, LoginResponseSchema,
    RegistrationRequestSchema, RegistrationResponseSchema,
    TokenResponseSchema,
    # Password Management
    PasswordResetRequestSchema, PasswordResetResponseSchema,
    ChangePasswordRequestSchema, ChangePasswordResponseSchema,
    # Profile Management
    UserProfileSchema, UpdateProfileRequestSchema, UpdateProfileResponseSchema,
    # Email & Verification
    EmailVerificationRequestSchema, EmailVerificationResponseSchema,
    # MFA
    MFASetupRequestSchema, MFASetupResponseSchema,
    MFAVerifyRequestSchema, MFAVerifyResponseSchema,
    # Session Management
    SessionRequestSchema, SessionResponseSchema
)
from core.services.auth.auth_service import AuthService

import logging

logger = logging.getLogger(__name__)


def create_auth_blueprint(auth_service: AuthService, db_session):
    """Create authentication blueprint with comprehensive routes."""
    auth_bp = Blueprint('auth', __name__)

    def set_tokens_in_response(response, user_id: str, remember: bool = False):
        """Set authentication tokens in response cookies."""
        expiry = timedelta(days=30) if remember else None

        access_token = create_access_token(identity=str(user_id))
        refresh_token = create_refresh_token(identity=str(user_id))

        cookie_settings = {
            'httponly': True,
            'secure': current_app.config['JWT_COOKIE_SECURE'],
            'samesite': 'Lax' if current_app.debug else 'Strict',
            'expires': expiry
        }

        response.set_cookie('access_token', access_token, path='/', **cookie_settings)
        response.set_cookie('refresh_token', refresh_token, path='/api/v1/auth/refresh', **cookie_settings)

        return response

    def clear_auth_tokens(response):
        """Clear authentication tokens from cookies."""
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('refresh_token', path='/api/v1/auth/refresh')
        return response

    # Registration and Authentication Routes
    @auth_bp.route('/register', methods=['POST'])
    def register():
        """Register a new user."""
        try:
            schema = RegisterRequestSchema()
            data = schema.load(request.get_json())

            if auth_service.get_user_by_email(data['email']):
                return ResponseBuilder.error("Email already registered", status_code=409)

            user = auth_service.register_user(data)
            response_data = RegisterResponseSchema().dump({
                'user': user,
                'verification_email_sent': True
            })

            response = make_response(ResponseBuilder.success(response_data))
            return set_tokens_in_response(response, user.id)

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Registration failed", status_code=500)

    @auth_bp.route('/login', methods=['POST'])
    def login():
        """Authenticate user and issue tokens."""
        try:
            schema = LoginRequestSchema()
            data = schema.load(request.get_json())

            user = auth_service.authenticate_user(data['email'], data['password'])
            if not user:
                return ResponseBuilder.error("Invalid credentials", status_code=401)

            # Check MFA requirement
            if user.mfa_enabled and not data.get('mfa_code'):
                return ResponseBuilder.success({
                    'mfa_required': True,
                    'temp_token': auth_service.create_temp_mfa_token(user.id)
                })

            response_data = LoginResponseSchema().dump({
                'user': user,
                'logged_in_at': datetime.utcnow()
            })

            response = make_response(ResponseBuilder.success(response_data))
            return set_tokens_in_response(response, user.id, data.get('remember_me', False))

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Login failed", status_code=500)

    # Token Management Routes
    @auth_bp.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh_token():
        """Refresh access token using refresh token."""
        try:
            current_user_id = get_jwt_identity()
            response = make_response(ResponseBuilder.success({
                'message': 'Token refreshed successfully'
            }))

            access_token = create_access_token(identity=current_user_id)
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=current_app.config['JWT_COOKIE_SECURE'],
                samesite='Lax' if current_app.debug else 'Strict'
            )

            return response

        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Token refresh failed", status_code=500)

    @auth_bp.route('/logout', methods=['POST'])
    @jwt_required()
    def logout():
        """Log out user and invalidate tokens."""
        try:
            token_jti = get_jwt()['jti']
            auth_service.invalidate_token(token_jti)

            response = make_response(ResponseBuilder.success({
                'message': 'Logged out successfully'
            }))
            return clear_auth_tokens(response)

        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Logout failed", status_code=500)

    # MFA Routes
    @auth_bp.route('/mfa/setup', methods=['POST'])
    @jwt_required()
    def setup_mfa():
        """Set up multi-factor authentication."""
        try:
            schema = MFASetupRequestSchema()
            data = schema.load(request.get_json())

            setup_data = auth_service.setup_mfa(get_jwt_identity(), data['mfa_type'])
            return ResponseBuilder.success(MFASetupResponseSchema().dump(setup_data))

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"MFA setup error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("MFA setup failed", status_code=500)

    @auth_bp.route('/mfa/verify', methods=['POST'])
    def verify_mfa():
        """Verify MFA code and complete authentication."""
        try:
            schema = MFAVerifyRequestSchema()
            data = schema.load(request.get_json())

            verification = auth_service.verify_mfa(data['temp_token'], data['code'])
            if not verification['verified']:
                return ResponseBuilder.error("Invalid MFA code", status_code=401)

            response = make_response(ResponseBuilder.success(
                MFAVerifyResponseSchema().dump(verification)
            ))
            return set_tokens_in_response(response, verification['user_id'])

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"MFA verification error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("MFA verification failed", status_code=500)

    # Profile Management Routes
    @auth_bp.route('/profile', methods=['GET'])
    @jwt_required()
    def get_profile():
        """Get user profile information."""
        try:
            user = auth_service.get_user_by_id(get_jwt_identity())
            return ResponseBuilder.success({
                'profile': UserProfileSchema().dump(user)
            })

        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to fetch profile", status_code=500)

    @auth_bp.route('/profile', methods=['PUT'])
    @jwt_required()
    def update_profile():
        """Update user profile information."""
        try:
            schema = UpdateProfileRequestSchema()
            data = schema.load(request.get_json())

            updated_user = auth_service.update_profile(get_jwt_identity(), data)
            return ResponseBuilder.success(
                UpdateProfileResponseSchema().dump(updated_user)
            )

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Profile update error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to update profile", status_code=500)

    # Password Management Routes
    @auth_bp.route('/password/forgot', methods=['POST'])
    def forgot_password():
        """Initiate password reset process."""
        try:
            schema = PasswordResetRequestSchema()
            data = schema.load(request.get_json())

            auth_service.initiate_password_reset(data['email'])
            return ResponseBuilder.success({
                'message': 'Password reset instructions sent'
            })

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password reset initiation error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to initiate password reset", status_code=500)

    @auth_bp.route('/password/reset', methods=['POST'])
    def reset_password():
        """Reset password using reset token."""
        try:
            schema = PasswordResetRequestSchema()
            data = schema.load(request.get_json())

            reset_result = auth_service.reset_password(
                data['token'],
                data['new_password']
            )
            return ResponseBuilder.success(
                PasswordResetResponseSchema().dump(reset_result)
            )

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Password reset failed", status_code=500)

    @auth_bp.route('/password/change', methods=['POST'])
    @jwt_required()
    def change_password():
        """Change password for authenticated user."""
        try:
            schema = ChangePasswordRequestSchema()
            data = schema.load(request.get_json())

            change_result = auth_service.change_password(
                get_jwt_identity(),
                data['current_password'],
                data['new_password']
            )
            return ResponseBuilder.success(
                ChangePasswordResponseSchema().dump(change_result)
            )

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password change error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Password change failed", status_code=500)

    # Email Verification Routes
    @auth_bp.route('/email/verify', methods=['POST'])
    def verify_email():
        """Verify email address."""
        try:
            schema = EmailVerificationRequestSchema()
            data = schema.load(request.get_json())

            verification = auth_service.verify_email(data['token'])
            return ResponseBuilder.success(
                EmailVerificationResponseSchema().dump(verification)
            )

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Email verification error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Email verification failed", status_code=500)

    @auth_bp.route('/email/verify/resend', methods=['POST'])
    @jwt_required()
    def resend_verification():
        """Resend email verification link."""
        try:
            auth_service.resend_verification_email(get_jwt_identity())
            return ResponseBuilder.success({
                'message': 'Verification email resent successfully'
            })

        except Exception as e:
            logger.error(f"Verification email resend error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to resend verification email", status_code=500)

    # Error Handlers
    @auth_bp.errorhandler(400)
    def handle_bad_request(error):
        return ResponseBuilder.error("Bad request", status_code=400)

    @auth_bp.errorhandler(401)
    def handle_unauthorized(error):
        return ResponseBuilder.error("Unauthorized", status_code=401)

    @auth_bp.errorhandler(404)
    def handle_not_found(error):
        return ResponseBuilder.error("Resource not found", status_code=404)

    @auth_bp.errorhandler(500)
    def handle_server_error(error):
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        return ResponseBuilder.error("Internal server error", status_code=500)

    return auth_bp