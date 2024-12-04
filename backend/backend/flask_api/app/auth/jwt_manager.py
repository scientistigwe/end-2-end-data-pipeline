# app/auth/jwt_manager.py
from flask_jwt_extended import JWTManager, create_access_token, create_refresh_token
from datetime import timedelta
from typing import Dict, Any


class JWTTokenManager:
    def __init__(self, app=None):
        self.jwt = JWTManager()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        # Configure JWT settings
        app.config['JWT_SECRET_KEY'] = app.config['SECRET_KEY']
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
        app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)

        self.jwt.init_app(app)

        # Register JWT callbacks
        @self.jwt.user_claims_loader
        def add_claims_to_access_token(user: Dict[str, Any]) -> Dict[str, Any]:
            return {
                'roles': user.get('roles', []),
                'permissions': user.get('permissions', [])
            }

        @self.jwt.user_identity_loader
        def user_identity_lookup(user: Dict[str, Any]) -> str:
            return user['id']










# Example updated route with security and documentation
# app/blueprints/pipeline/routes.py

