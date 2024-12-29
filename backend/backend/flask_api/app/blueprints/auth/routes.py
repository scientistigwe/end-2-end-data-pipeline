# app/blueprints/auth/routes.py
from flask import Blueprint, request, g, current_app
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
    """Create auth blueprint with all routes.
    
    Args:
        auth_service: Instance of AuthService
        db_session: Database session
        
    Returns:
        Blueprint: Configured auth blueprint
    """
    auth_bp = Blueprint('auth', __name__)

    # Public Routes (No JWT Required)
    @auth_bp.route('/register', methods=['POST'])
    def register():
        """Register a new user."""
        try:
            schema = RegisterRequestSchema()
            data = schema.load(request.get_json())
            
            user = auth_service.register_user(data)
            
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            return ResponseBuilder.success({
                'message': 'User registered successfully',
                'tokens': TokenResponseSchema().dump({
                    'access_token': access_token,
                    'refresh_token': refresh_token
                }),
                'user': UserProfileResponseSchema().dump(user)
            })
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
            
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            auth_service.update_last_login(user.id)
            
            response_data = {
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'full_name': user.full_name,
                    'role': user.role,
                    'status': user.status,
                    'email_verified': user.email_verified,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                    'last_login': datetime.utcnow().isoformat()
                },
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'bearer'
                }
            }
            
            return ResponseBuilder.success(response_data)

        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Login failed", status_code=500)
        
    # Protected Routes (JWT Required)
    @auth_bp.route('/refresh', methods=['POST'])
    @jwt_required(refresh=True)
    def refresh():
        """Refresh access token."""
        try:
            current_user = get_jwt_identity()
            access_token = create_access_token(identity=current_user)
            
            return ResponseBuilder.success(
                TokenResponseSchema().dump({'access_token': access_token})
            )
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Token refresh failed", status_code=500)

    @auth_bp.route('/logout', methods=['POST'])
    def logout():
        """Logout user and invalidate tokens."""
        try:
            jti = get_jwt()['jti']
            auth_service.invalidate_token(jti)
            return ResponseBuilder.success({"message": "Successfully logged out"})
        except Exception as e:
            logger.error(f"Logout error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Logout failed", status_code=500)

    # Public Password Management Routes
    @auth_bp.route('/forgot-password', methods=['POST'])
    def forgot_password():
        """Initiate password reset process."""
        try:
            schema = PasswordResetRequestSchema()
            data = schema.load(request.get_json())
                
            result = auth_service.initiate_password_reset(data['email'])
            
            return ResponseBuilder.success(
                PasswordResetResponseSchema().dump(result)
            )
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password reset initiation error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to initiate password reset", status_code=500)

    @auth_bp.route('/reset-password', methods=['POST'])
    def reset_password():
        """Reset user's password using reset token."""
        try:
            schema = PasswordResetRequestSchema()
            data = schema.load(request.get_json())
            
            result = auth_service.reset_password(data['token'], data['new_password'])
            
            return ResponseBuilder.success(
                PasswordResetResponseSchema().dump(result)
            )
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Password reset failed", status_code=500)

    # Protected User Profile Routes
    @auth_bp.route('/profile', methods=['GET'])
    @jwt_required()
    def get_profile():
        """Get user's profile information."""
        try:
            current_user_id = get_jwt_identity()
            user = auth_service.get_user_profile(current_user_id)
            return ResponseBuilder.success(
                UserProfileResponseSchema().dump(user)
            )
        except Exception as e:
            logger.error(f"Profile fetch error: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to fetch profile", status_code=500)
        
    @auth_bp.route('/profile', methods=['PUT'])
    @jwt_required()
    def update_profile():
        """Update user's profile information."""
        schema = UserProfileResponseSchema()

        try:
            data = schema.load(request.get_json())
            current_user_id = get_jwt_identity()
            updated_user = auth_service.update_user_profile(current_user_id, data)
            return ResponseBuilder.success(schema.dump(updated_user))
        
        except ValidationError as validation_error:
            return ResponseBuilder.error(
                "Validation error",
                details=validation_error.messages,
                status_code=400
            )
        
        except Exception as generic_error:
            logger.error(
                f"Error updating profile: {str(generic_error)}", exc_info=True
            )
            return ResponseBuilder.error(
                "Failed to update profile",
                status_code=500
            )
        
    # Error handlers
    @auth_bp.errorhandler(401)
    def unauthorized_error(error):
        """Handle unauthorized access attempts."""
        return ResponseBuilder.error("Unauthorized", status_code=401)

    @auth_bp.errorhandler(403)
    def forbidden_error(error):
        """Handle forbidden access attempts."""
        return ResponseBuilder.error("Forbidden", status_code=403)

    @auth_bp.errorhandler(422)
    def validation_error(error):
        """Handle validation errors."""
        return ResponseBuilder.error("Validation Error", details=error.description, status_code=422)
        
    return auth_bp