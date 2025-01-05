# app/blueprints/auth/routes.py
from flask import Blueprint, request, g, current_app, make_response, jsonify
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    create_access_token, 
    create_refresh_token,
    get_jwt
)
from marshmallow import ValidationError
from ...schemas.auth import (
    LoginRequestSchema,
    LoginResponseSchema,
    RegisterRequestSchema,
    RegisterResponseSchema,
    TokenResponseSchema,
    PasswordResetRequestSchema,
    PasswordResetResponseSchema,
    EmailVerificationRequestSchema,
    EmailVerificationResponseSchema,
    ChangePasswordRequestSchema,
    ChangePasswordResponseSchema,
    UserProfileResponseSchema
)
from ...services.auth import AuthService
from ...utils.response_builder import ResponseBuilder
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def create_auth_blueprint(auth_service: AuthService, db_session):
    """Create auth blueprint with all routes."""
    auth_bp = Blueprint('auth', __name__)

    # Public Routes (No JWT Required)
    @auth_bp.route('/register', methods=['POST'])
    def register():
        """Register a new user."""
        try:
            schema = RegisterRequestSchema()
            data = schema.load(request.get_json())
            
            # Check if user already exists
            if auth_service.get_user_by_email(data['email']):
                return ResponseBuilder.error("Email already registered", status_code=409)
            
            user = auth_service.register_user(data)
            tokens = create_auth_tokens(user.id)
            
            response = RegisterResponseSchema().dump({
                'user': user,
                'tokens': tokens,
                'registered_at': datetime.utcnow().isoformat()
            })
            
            return ResponseBuilder.success(response)
            
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Registration error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Registration failed", status_code=500)

    @auth_bp.route('/login', methods=['POST'])
    def login():
        """Authenticate user and return tokens."""
        try:
            schema = LoginRequestSchema()
            data = schema.load(request.get_json())
            
            user = auth_service.authenticate_user(data['email'], data['password'])
            if not user:
                return ResponseBuilder.error("Invalid credentials", status_code=401)
            
            if not user.is_active:
                return ResponseBuilder.error("Account is inactive", status_code=403)
                
            # Generate tokens
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            # Create response data with proper structure
            login_data = {
                'user': user,
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'bearer'
                },
                'logged_in_at': datetime.utcnow().isoformat()
            }
            
            # Dump through schema
            response_data = {
                'user': schema.dump(user),
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'bearer'
                },
                'logged_in_at': datetime.utcnow().isoformat()
            }

            response = make_response(
                jsonify(
                    ResponseBuilder.success(
                        data=response_data,
                        message="Login successful"
                    )[0]
                )
            )

            # Set cookies
            response.set_cookie(
                'access_token',
                access_token,
                httponly=True,
                secure=current_app.config['JWT_COOKIE_SECURE'],
                samesite=current_app.config['JWT_COOKIE_SAMESITE']
            )
            response.set_cookie(
                'refresh_token',
                refresh_token,
                httponly=True,
                secure=current_app.config['JWT_COOKIE_SECURE'],
                samesite=current_app.config['JWT_COOKIE_SAMESITE']
            )

            return response

        except ValidationError as e:
            return ResponseBuilder.error(
                message="Validation error", 
                details=e.messages, 
                status_code=400
            )
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return ResponseBuilder.error(
                message="Login failed",
                status_code=500
            )                
    def create_auth_tokens(user_id: str, response):
        """Helper function to create authentication tokens and set them as cookies.
        
        Args:
            user_id (str): The user's unique identifier
            response (flask.Response): Flask response object to set cookies on
            
        Returns:
            dict: Token information including type and any additional metadata
        """
        access_token = create_access_token(identity=str(user_id))
        refresh_token = create_refresh_token(identity=str(user_id))
        
        # Set tokens as HTTP-only cookies
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=current_app.config['JWT_COOKIE_SECURE'],
            samesite=current_app.config['JWT_COOKIE_SAMESITE']
        )
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=current_app.config['JWT_COOKIE_SECURE'],
            samesite=current_app.config['JWT_COOKIE_SAMESITE']
        )
        
        return {
            'token_type': 'bearer',
            'access_token': access_token,  # Optionally include if needed in response
            'refresh_token': refresh_token  # Optionally include if needed in response
        }

    @auth_bp.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        """Refresh access token."""
        try:
            current_user_id = get_jwt_identity()
            user = auth_service.get_user_by_id(current_user_id)
            
            if not user or not user.is_active:
                return ResponseBuilder.error("Invalid or inactive user", status_code=401)
            
            new_token = create_access_token(identity=current_user_id)
            response = TokenResponseSchema().dump({
                'access_token': new_token,
                'token_type': 'bearer',
                'refreshed_at': datetime.utcnow().isoformat()
            })
            
            return ResponseBuilder.success(response)
            
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Token refresh failed", status_code=500)

    @auth_bp.route('/logout', methods=['POST'])
    @jwt_required()
    def logout():
        """Logout user and invalidate tokens."""
        try:
            token_jti = get_jwt()['jti']
            current_user_id = get_jwt_identity()
            
            auth_service.invalidate_token(token_jti)
            
            return ResponseBuilder.success({
                "message": "Successfully logged out",
                "user_id": current_user_id,
                "logged_out_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Logout failed", status_code=500)

    @auth_bp.route('/forgot-password', methods=['POST'])
    def forgot_password():
        """Initiate password reset process."""
        try:
            schema = PasswordResetRequestSchema()
            data = schema.load(request.get_json())
            
            user = auth_service.get_user_by_email(data['email'])
            if not user:
                # Return success even if email doesn't exist for security
                return ResponseBuilder.success({
                    "message": "If your email is registered, you will receive reset instructions"
                })
            
            reset_token = auth_service.initiate_password_reset(data['email'])
            
            response = PasswordResetResponseSchema().dump({
                'email': data['email'],
                'reset_token': reset_token,
                'requested_at': datetime.utcnow().isoformat()
            })
            
            return ResponseBuilder.success(response)
            
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
            
            return ResponseBuilder.success({
                "message": "Password reset successful",
                "reset_at": datetime.utcnow().isoformat()
            })
            
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Password reset failed", status_code=500)

    @auth_bp.route('/profile', methods=['GET'])
    @jwt_required()
    def get_profile():
        """Get user's profile information."""
        try:
            current_user_id = get_jwt_identity()
            user = auth_service.get_user_profile(current_user_id)
            
            if not user:
                return ResponseBuilder.error("User not found", status_code=404)
            
            response = UserProfileResponseSchema().dump({
                'user': user,
                'fetched_at': datetime.utcnow().isoformat()
            })
            
            return ResponseBuilder.success(response)
            
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
            
            response = schema.dump({
                'user': updated_user,
                'updated_at': datetime.utcnow().isoformat()
            })
            
            return ResponseBuilder.success(response)
            
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
            
            return ResponseBuilder.success({
                "message": "Email verified successfully",
                "verified_at": datetime.utcnow().isoformat()
            })
            
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
            
            auth_service.change_password(
                current_user_id,
                data['current_password'],
                data['new_password']
            )
            
            return ResponseBuilder.success({
                "message": "Password changed successfully",
                "changed_at": datetime.utcnow().isoformat()
            })
            
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password change error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to change password", status_code=500)

    # Error handlers
    @auth_bp.errorhandler(401)
    def unauthorized_error(error):
        return ResponseBuilder.error("Unauthorized", status_code=401)

    @auth_bp.errorhandler(403)
    def forbidden_error(error):
        return ResponseBuilder.error("Forbidden", status_code=403)

    @auth_bp.errorhandler(404)
    def not_found_error(error):
        return ResponseBuilder.error("Resource not found", status_code=404)

    @auth_bp.errorhandler(422)
    def validation_error(error):
        return ResponseBuilder.error(
            "Validation Error", 
            details=error.description, 
            status_code=422
        )

    @auth_bp.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}", exc_info=True)
        return ResponseBuilder.error(
            "Internal server error",
            status_code=500
        )

    @auth_bp.route('/verify', methods=['POST'])
    def verify_account():
        """Verify user's account."""
        try:
            data = request.get_json()
            verification_token = data.get('token')
            
            if not verification_token:
                return ResponseBuilder.error("Verification token is required", status_code=400)
            
            user = auth_service.verify_account(verification_token)
            
            tokens = create_auth_tokens(user.id)
            
            return ResponseBuilder.success({
                'message': 'Account verified successfully',
                'user': UserProfileResponseSchema().dump(user),
                'tokens': tokens,
                'verified_at': datetime.utcnow().isoformat()
            })
            
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Account verification error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Account verification failed", status_code=500)
        
    return auth_bp