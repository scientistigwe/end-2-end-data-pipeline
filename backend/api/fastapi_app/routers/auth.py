# api/fastapi_app/routers/auth.py

from fastapi import APIRouter, Depends, HTTPException, Response, Request, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from jose import jwt
from config.database import get_db_session
from api.fastapi_app.middleware.auth_middleware import get_current_user, get_optional_user
from api.fastapi_app.middleware.auth_middleware import auth_middleware
from core.services.auth.auth_service import AuthService
from api.fastapi_app.schemas.auth import (
    LoginRequestSchema,
    LoginResponseSchema,
    RegistrationRequestSchema,
    RegistrationResponseSchema,
    TokenResponseSchema,
    PasswordResetRequestSchema,
    PasswordResetResponseSchema,
    ChangePasswordRequestSchema,
    ChangePasswordResponseSchema,
    UserProfileSchema,
    UpdateProfileRequestSchema,
    UpdateProfileResponseSchema,
    EmailVerificationRequestSchema,
    EmailVerificationResponseSchema,
    MFASetupRequestSchema,
    MFASetupResponseSchema,
    MFAVerifyRequestSchema,
    MFAVerifyResponseSchema,
    SessionRequestSchema,
    SessionResponseSchema
)

from ..middleware.auth_middleware import auth_settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=LoginResponseSchema)
async def login(
        request: Request,
        response: Response,
        credentials: LoginRequestSchema,
        db: AsyncSession = Depends(get_db_session)
):
    try:
        auth_service = AuthService(db)
        user = await auth_service.authenticate_user(
            email=credentials.email,
            password=credentials.password
        )

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid credentials"
            )

        # Create user data for token
        user_data = {
            'id': str(user.id),
            'email': user.email,
            'roles': [user.role] if hasattr(user, 'role') else [],
            'permissions': getattr(user, 'permissions', [])
        }

        # Create tokens
        tokens = await auth_service.create_tokens(user_data)

        # Set cookies
        response.set_cookie(
            'access_token',
            tokens["access_token"],
            httponly=True,
            secure=False, # Set to True in production
            samesite='lax',
            max_age=3600  # 1 hour
        )

        response.set_cookie(
            'refresh_token',
            tokens["refresh_token"],
            httponly=True,
            secure=False, # Set to True in production
            samesite='lax',
            path='/api/v1/auth/refresh',
            max_age=86400 * 30  # 30 days
        )

        # Add a debug header to indicate cookies were set
        response.headers['X-Auth-Cookie-Set'] = 'true'

        # Set a valid datetime for session_expires
        session_expires = datetime.utcnow() + timedelta(seconds=3600)  # 1 hour

        # Create complete user object with all required fields
        user_obj = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "role": user.role,
            "status": getattr(user, 'status', 'active'),
            "permissions": user_data.get('permissions', []),
            "timezone": getattr(user, 'timezone', 'UTC'),
            "locale": getattr(user, 'locale', 'en-US'),
            # Add other required fields, with defaults for missing ones
            "email_verified": getattr(user, 'email_verified', False),
            "profile_image": getattr(user, 'profile_image', None),
            "phone_number": getattr(user, 'phone_number', None),
            "department": getattr(user, 'department', None),
            "preferences": getattr(user, 'preferences', {}),
            "metadata": getattr(user, 'metadata', {}),
            "security_level": getattr(user, 'security_level', 'standard')
        }

        return LoginResponseSchema(
            user=user_obj,
            tokens=tokens,
            mfa_required=False,
            session_expires=session_expires,
            permitted_actions=user_data.get('permissions', [])
        )

    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.get("/profile", response_model=UserProfileSchema)
async def get_profile(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Get user profile"""
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(current_user['id'])

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Handle metadata properly - convert to dict if it's not already
        metadata = getattr(user, 'meta_data', {})
        if metadata and not isinstance(metadata, dict):
            # If it's a MetaData object or something else, convert to dict
            # This handles the case where metadata might be an ORM object
            try:
                metadata = dict(metadata)
            except (TypeError, ValueError):
                metadata = {}

        # Get security_level as an integer with default value 1
        security_level = 1  # Default security level
        try:
            if hasattr(user, 'security_level'):
                if isinstance(user.security_level, int):
                    security_level = user.security_level
                elif isinstance(user.security_level, str) and user.security_level.isdigit():
                    security_level = int(user.security_level)
        except (TypeError, ValueError):
            pass  # Keep the default if conversion fails

        # Create the user profile dictionary
        user_profile = {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
            "role": user.role,
            "status": getattr(user, 'status', 'active'),
            "permissions": current_user.get('permissions', []),
            "email_verified": getattr(user, 'email_verified', False),
            "profile_image": getattr(user, 'profile_image', None),
            "phone_number": getattr(user, 'phone_number', None),
            "department": getattr(user, 'department', None),
            "timezone": getattr(user, 'timezone', 'UTC'),
            "locale": getattr(user, 'locale', 'en-US'),
            "preferences": getattr(user, 'preferences', {}) or {},
            "metadata": metadata,
            "security_level": security_level  # Now this is an integer
        }

        return UserProfileSchema(**user_profile)

    except Exception as e:
        logger.error(f"Profile fetch error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch profile")

@router.put("/profile", response_model=UpdateProfileResponseSchema)
async def update_profile(
        profile_data: UpdateProfileRequestSchema,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Update user profile"""
    try:
        auth_service = AuthService(db)
        updated_user = await auth_service.update_user_profile(
            current_user['id'],
            profile_data.dict()
        )
        return UpdateProfileResponseSchema.from_orm(updated_user)

    except Exception as e:
        logger.error(f"Profile update error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update profile")


@router.post("/register", response_model=RegistrationResponseSchema)
async def register(
        registration_data: RegistrationRequestSchema,
        response: Response,
        db: AsyncSession = Depends(get_db_session)
):
    """Register new user"""
    try:
        auth_service = AuthService(db)

        # Check if email exists
        existing_user = await auth_service.get_user_by_email(registration_data.email)
        if existing_user:
            raise HTTPException(status_code=409, detail="Email already registered")

        user = await auth_service.register_user(registration_data.dict())

        # Create tokens
        user_data = {
            'id': str(user.id),
            'email': user.email,
            'roles': [user.role] if hasattr(user, 'role') else [],
            'permissions': getattr(user, 'permissions', [])
        }

        tokens = await auth_service.create_tokens(user_data)

        # Set cookies
        response.set_cookie(
            'access_token',
            tokens['access_token'],
            httponly=True,
            secure=True,
            samesite='lax'
        )

        return {
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "role": user.role,
                "permissions": user_data['permissions']
            },
            "tokens": tokens,
            "verification_email_sent": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Registration failed")


@router.get("/cookie-check")
async def cookie_check(request: Request):
    """Check if cookies are being properly sent by the client"""
    cookies = request.cookies
    headers = dict(request.headers)

    return {
        "cookies_received": cookies,
        "has_access_token": "access_token" in cookies,
        "auth_header": headers.get("authorization"),
        "origin": headers.get("origin"),
        "referer": headers.get("referer")
    }


@router.get("/debug-auth", response_model=dict)
async def debug_auth(request: Request):
    """Debug endpoint to check authentication state"""
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    auth_header = request.headers.get("authorization")

    # Try to decode token if present
    token_content = None
    if access_token:
        try:
            token_content = jwt.decode(
                access_token,
                auth_settings.JWT_SECRET_KEY,
                algorithms=[auth_settings.JWT_ALGORITHM]
            )
        except Exception as e:
            token_content = {"error": str(e)}

    return {
        "has_access_token": bool(access_token),
        "has_refresh_token": bool(refresh_token),
        "has_auth_header": bool(auth_header),
        "cookies": dict(request.cookies),
        "token_content": token_content
    }

# Password Management Endpoints
@router.post("/password/forgot", response_model=dict)
async def forgot_password(
        request: PasswordResetRequestSchema,
        db: AsyncSession = Depends(get_db_session)
):
    """Initiate password reset process"""
    try:
        auth_service = AuthService(db)
        await auth_service.initiate_password_reset(request.email)
        return {"message": "Password reset instructions sent"}
    except Exception as e:
        logger.error(f"Password reset initiation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate password reset")


@router.post("/password/reset", response_model=PasswordResetResponseSchema)
async def reset_password(
        request: PasswordResetRequestSchema,
        db: AsyncSession = Depends(get_db_session)
):
    """Reset password using reset token"""
    try:
        auth_service = AuthService(db)
        reset_result = await auth_service.reset_password(
            request.token,
            request.new_password
        )
        return reset_result
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Password reset failed")


@router.post("/password/change", response_model=ChangePasswordResponseSchema)
async def change_password(
        request: ChangePasswordRequestSchema,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Change password for authenticated user"""
    try:
        auth_service = AuthService(db)
        change_result = await auth_service.change_password(
            current_user['id'],
            request.current_password,
            request.new_password
        )
        return change_result
    except Exception as e:
        logger.error(f"Password change error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Password change failed")


# Email Verification Endpoints
@router.post("/email/verify", response_model=EmailVerificationResponseSchema)
async def verify_email(
        request: EmailVerificationRequestSchema,
        db: AsyncSession = Depends(get_db_session)
):
    """Verify email address"""
    try:
        auth_service = AuthService(db)
        verification = await auth_service.verify_email(request.token)
        return verification
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Email verification failed")


@router.post("/email/verify/resend", response_model=dict)
async def resend_verification(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Resend email verification link"""
    try:
        auth_service = AuthService(db)
        await auth_service.resend_verification_email(current_user['id'])
        return {"message": "Verification email resent successfully"}
    except Exception as e:
        logger.error(f"Verification email resend error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to resend verification email")


# MFA Endpoints
@router.post("/mfa/setup", response_model=MFASetupResponseSchema)
async def setup_mfa(
        request: MFASetupRequestSchema,
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Set up multi-factor authentication"""
    try:
        auth_service = AuthService(db)
        setup_data = await auth_service.setup_mfa(
            current_user['id'],
            request.mfa_type
        )
        return setup_data
    except Exception as e:
        logger.error(f"MFA setup error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="MFA setup failed")


@router.post("/mfa/verify", response_model=MFAVerifyResponseSchema)
async def verify_mfa(
        request: MFAVerifyRequestSchema,
        db: AsyncSession = Depends(get_db_session)
):
    """Verify MFA code and complete authentication"""
    try:
        auth_service = AuthService(db)
        verification = await auth_service.verify_mfa(
            request.temp_token,
            request.code
        )

        if not verification['verified']:
            raise HTTPException(status_code=401, detail="Invalid MFA code")

        return verification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MFA verification error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="MFA verification failed")


# Session Management Endpoints
@router.post("/session/validate", response_model=dict)
async def validate_session(
        current_user: dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
):
    """Validate current user session"""
    try:
        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(current_user['id'])
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")

        return {
            "valid": True,
            "user_id": str(current_user['id'])
        }
    except Exception as e:
        logger.error(f"Session validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Session validation failed")


@router.get("/permissions", response_model=dict)
async def get_permissions(
        current_user: dict = Depends(get_current_user)
):
    """Get current user permissions"""
    try:
        return {
            "permissions": current_user.get('permissions', []),
            "roles": current_user.get('roles', [])
        }
    except Exception as e:
        logger.error(f"Permissions fetch error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch permissions")


# Refresh Token Endpoint
@router.post("/refresh", response_model=TokenResponseSchema)
async def refresh_token(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_db_session)
):
    """Refresh access token using refresh token"""
    try:
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            raise HTTPException(status_code=401, detail="No refresh token provided")

        auth_service = AuthService(db)
        tokens = await auth_service.refresh_token(refresh_token)

        # Set new cookies
        response.set_cookie(
            'access_token',
            tokens['access_token'],
            httponly=True,
            secure=not request.app.debug,
            samesite='lax',
            max_age=3600
        )

        return tokens
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Token refresh failed")


# Debug Endpoint
@router.get("/debug", response_model=dict)
async def debug_auth(request: Request):
    """Debug endpoint to check authentication state"""
    try:
        return {
            "has_access_token": bool(request.cookies.get("access_token")),
            "has_refresh_token": bool(request.cookies.get("refresh_token")),
            "cookies": dict(request.cookies),
            "headers": dict(request.headers)
        }
    except Exception as e:
        logger.error(f"Debug endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Debug check failed")


@router.post("/logout")
async def logout(
        response: Response,
        current_user: dict = Depends(get_current_user)
):
    """Logout user"""
    try:
        # Clear cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token', path='/api/v1/auth/refresh')

        return {"message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Logout failed")

def register_auth_exception_handlers(app: FastAPI):
    """Register exception handlers for auth routes

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Internal server error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "status_code": 500
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Internal server error: {str(exc)}", exc_info=True)
        return {
            "error": True,
            "message": "Internal server error",
            "status_code": 500
        }