# blueprints/auth/routes.py
from marshmallow import ValidationError
from flask import Blueprint, request, make_response, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
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
from api.flask_app.auth.jwt_manager import JWTTokenManager

import logging

logger = logging.getLogger(__name__)


def create_auth_blueprint(auth_service: AuthService, db_session, jwt_manager: JWTTokenManager):
    """Create authentication blueprint with comprehensive routes."""
    auth_bp = Blueprint('auth', __name__)

    def set_tokens_in_response(response, user: dict, remember: bool = False):
        """Set authentication tokens in response cookies."""
        try:
            tokens = jwt_manager.create_tokens(user, fresh=True)

            cookie_settings = {
                'httponly': True,
                'secure': current_app.config['JWT_COOKIE_SECURE'],
                'samesite': 'Lax' if current_app.debug else 'Strict'
            }

            if remember:
                cookie_settings['expires'] = (
                        datetime.utcnow() + timedelta(days=30)
                ).timestamp()

            # Use the exact cookie names from JWT config
            response.set_cookie(
                'access_token_cookie',  # Changed from 'access_token'
                tokens['access_token'],
                path='/',
                **cookie_settings
            )
            response.set_cookie(
                'refresh_token_cookie',  # Changed from 'refresh_token'
                tokens['refresh_token'],
                path='/api/v1/auth/refresh',
                **cookie_settings
            )

            return response
        except Exception as e:
            logger.error(f"Error setting tokens: {str(e)}")
            raise

    def clear_auth_tokens(response):
        """Clear authentication tokens from cookies."""
        response.delete_cookie('access_token_cookie', path='/')  # Changed from 'access_token'
        response.delete_cookie('refresh_token_cookie', path='/api/v1/auth/refresh')  # Changed from 'refresh_token'
        return response

    @auth_bp.route('/register', methods=['POST'])
    def register():
        """Register a new user."""
        try:
            schema = RegistrationRequestSchema()
            data = schema.load(request.get_json())

            if auth_service.get_user_by_email(data['email']):
                return ResponseBuilder.error("Email already registered", status_code=409)

            user = auth_service.register_user(data)

            user_data = {
                'id': str(user.id),
                'email': user.email,
                'roles': [user.role] if hasattr(user, 'role') else [],
                'permissions': getattr(user, 'permissions', [])
            }

            response_data = RegistrationResponseSchema().dump({
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'status': user.status,
                    'role': user.role,
                    'is_active': user.is_active,
                    'email_verified': user.email_verified,
                    'created_at': user.created_at,
                    'updated_at': user.updated_at,
                    'last_login': user.last_login,
                    'profile_image': user.profile_image,
                    'department': user.department,
                    'timezone': user.timezone,
                    'locale': user.locale,
                    'preferences': user.preferences if hasattr(user, 'preferences') else {}
                },
                'verification_email_sent': True
            })

            response = make_response(ResponseBuilder.success(response_data))
            return set_tokens_in_response(response, user_data)

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Registration failed", status_code=500)

    @auth_bp.route('/login', methods=['POST'])
    def login():
        """User login route."""
        try:
            schema = LoginRequestSchema()
            data = schema.load(request.get_json())

            user = auth_service.authenticate_user(data['email'], data['password'])
            if not user:
                return ResponseBuilder.error("Invalid credentials", status_code=401)

            # Ensure base permissions are included
            base_permissions = [
                'profile:read',
                'profile:update',
                'auth:logout',
                'auth:refresh'
            ]

            # Get user's role-based permissions
            role_permissions = getattr(user, 'permissions', [])

            # Combine all permissions
            all_permissions = list(set(base_permissions + role_permissions))

            user_data = {
                'id': str(user.id),
                'email': user.email,
                'roles': [user.role] if hasattr(user, 'role') else [],
                'permissions': all_permissions
            }

            tokens = jwt_manager.create_tokens(user_data)

            login_data = {
                "user": {
                    "id": str(user.id),
                    "email": str(user.email),
                    "username": str(user.username),
                    "first_name": str(user.first_name) if user.first_name else "",
                    "last_name": str(user.last_name) if user.last_name else "",
                    "role": str(user.role),
                    "status": str(user.status),
                    "permissions": all_permissions,
                },
                "tokens": tokens,
                "mfa_required": False,
                "session_expires": datetime.utcnow() + timedelta(days=30 if data.get('rememberMe') else 1)
            }

            response = make_response(ResponseBuilder.success(login_data))
            return set_tokens_in_response(response, user_data, data.get('rememberMe', False))

        except ValidationError as e:
            logger.error(f"Login validation error: {e.messages}")
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Login failed", status_code=500)

    @auth_bp.route('/refresh', methods=['POST'])
    @jwt_manager.permission_required('auth:refresh')
    def refresh_token():
        """Refresh access token using refresh token."""
        try:
            current_user_id = get_jwt_identity()
            user = auth_service.get_user_by_id(current_user_id)

            user_data = {
                'id': str(user.id),
                'email': user.email,
                'roles': [user.role] if hasattr(user, 'role') else [],
                'permissions': getattr(user, 'permissions', [])
            }

            tokens = jwt_manager.create_tokens(user_data)
            response = make_response(ResponseBuilder.success({
                'message': 'Token refreshed successfully',
                'tokens': tokens
            }))

            return set_tokens_in_response(response, user_data)

        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Token refresh failed", status_code=500)

    @auth_bp.route('/logout', methods=['POST'])
    @jwt_manager.permission_required('auth:logout')
    def logout():
        """Log out user and invalidate tokens."""
        try:
            token_jti = get_jwt()['jti']
            jwt_manager.blacklist_token(token_jti)

            response = make_response(ResponseBuilder.success({
                'message': 'Logged out successfully'
            }))
            return clear_auth_tokens(response)

        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Logout failed", status_code=500)

    @auth_bp.route('/mfa/setup', methods=['POST'])
    @jwt_manager.permission_required('mfa:setup')
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

            user = auth_service.get_user_by_id(verification['user_id'])
            user_data = {
                'id': str(user.id),
                'email': user.email,
                'roles': [user.role] if hasattr(user, 'role') else [],
                'permissions': getattr(user, 'permissions', [])
            }

            response = make_response(ResponseBuilder.success(
                MFAVerifyResponseSchema().dump(verification)
            ))
            return set_tokens_in_response(response, user_data)

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"MFA verification error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("MFA verification failed", status_code=500)

    @auth_bp.route('/profile', methods=['GET'])
    @jwt_manager.permission_required('profile:read')  # This should match the permission in the token
    def get_profile():
        """Get user profile."""
        try:
            current_user_id = get_jwt_identity()
            user = auth_service.get_user_by_id(current_user_id)

            if not user:
                return ResponseBuilder.error("User not found", status_code=404)

            return ResponseBuilder.success({
                "user": {
                    "id": str(user.id),
                    "email": str(user.email),
                    "username": str(user.username),
                    "first_name": str(user.first_name) if user.first_name else "",
                    "last_name": str(user.last_name) if user.last_name else "",
                    "role": str(user.role),
                    "status": str(user.status),
                    "permissions": get_jwt().get('permissions', [])  # Include permissions in response
                }
            })

        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to fetch profile", status_code=500)

    @auth_bp.route('/debug', methods=['GET'])
    def debug_auth():
        """Debug endpoint to check authentication state."""
        try:
            access_token = request.cookies.get('access_token_cookie')
            refresh_token = request.cookies.get('refresh_token_cookie')

            return ResponseBuilder.success({
                'has_access_token': bool(access_token),
                'has_refresh_token': bool(refresh_token),
                'cookies': dict(request.cookies),
                'headers': dict(request.headers)
            })
        except Exception as e:
            logger.error(f"Debug endpoint error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Debug check failed", status_code=500)

    @auth_bp.route('/profile', methods=['PUT'])
    @jwt_manager.permission_required('profile:update')
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
    @jwt_manager.permission_required('password:change')
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
    @jwt_manager.permission_required('email:verify')
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

    @auth_bp.route('/session/validate', methods=['POST'])
    @jwt_manager.permission_required('session:validate')
    def validate_session():
                """Validate current user session."""
                try:
                    current_user_id = get_jwt_identity()
                    user = auth_service.get_user_by_id(current_user_id)

                    if not user:
                        return ResponseBuilder.error("Invalid session", status_code=401)

                    return ResponseBuilder.success({
                        'valid': True,
                        'user_id': str(current_user_id)
                    })

                except Exception as e:
                    logger.error(f"Session validation error: {str(e)}", exc_info=True)
                    return ResponseBuilder.error("Session validation failed", status_code=500)

    @auth_bp.route('/permissions', methods=['GET'])
    @jwt_manager.permission_required('permissions:read')
    def get_permissions():
                """Get current user permissions."""
                try:
                    claims = get_jwt()
                    return ResponseBuilder.success({
                        'permissions': claims.get('permissions', []),
                        'roles': claims.get('roles', [])
                    })
                except Exception as e:
                    logger.error(f"Permissions fetch error: {str(e)}", exc_info=True)
                    return ResponseBuilder.error("Failed to fetch permissions", status_code=500)

    # Error Handlers
    @auth_bp.errorhandler(400)
    def handle_bad_request(error):
                return ResponseBuilder.error("Bad request", status_code=400)

    @auth_bp.errorhandler(401)
    def handle_unauthorized(error):
                return ResponseBuilder.error("Unauthorized", status_code=401)

    @auth_bp.errorhandler(403)
    def handle_forbidden(error):
                return ResponseBuilder.error("Forbidden", status_code=403)

    @auth_bp.errorhandler(404)
    def handle_not_found(error):
                return ResponseBuilder.error("Resource not found", status_code=404)

    @auth_bp.errorhandler(500)
    def handle_server_error(error):
                logger.error(f"Internal server error: {str(error)}", exc_info=True)
                return ResponseBuilder.error("Internal server error", status_code=500)

    # Register after_request handler for CORS headers
    @auth_bp.after_request
    def after_request(response):
        """Add CORS headers to response."""
        origin = request.headers.get('Origin')
        if origin and origin in current_app.config['CORS_SETTINGS']['origins']:
            response.headers.update({
                'Access-Control-Allow-Origin': origin,
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-CSRF-TOKEN',
                'Access-Control-Expose-Headers': 'Set-Cookie'
            })
        return response

    @auth_bp.route('/profile', methods=['OPTIONS'])
    def handle_profile_options():
        """Handle OPTIONS request for profile endpoint."""
        response = jsonify({'message': 'OK'})
        return after_request(response)  # Apply CORS headers

    return auth_bp