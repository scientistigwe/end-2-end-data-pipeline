# app/openapi/spectacular.py
from flask_spectacular import Spectacular, SpectacularAPIView, SpectacularSwaggerView
from flask import Blueprint


class APIDocumentation:
    def __init__(self, app=None):
        self.spec = Spectacular()
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        # Configure Spectacular
        app.config["SPECTACULAR_SETTINGS"] = {
            "TITLE": "Data Pipeline API",
            "DESCRIPTION": "API documentation for the Data Pipeline system",
            "VERSION": "1.0.0",
            "SERVE_INCLUDE_SCHEMA": False,
            "SWAGGER_UI_SETTINGS": {
                "persistAuthorization": True,
            },
            "SECURITY": [
                {
                    "Bearer": []
                }
            ]
        }

        # Initialize Spectacular
        self.spec.init_app(app)

        # Create documentation blueprint
        docs_bp = Blueprint('api_docs', __name__)

        # Add documentation routes
        docs_bp.add_url_rule(
            '/schema/',
            view_func=SpectacularAPIView.as_view('schema'),
        )
        docs_bp.add_url_rule(
            '/docs/',
            view_func=SpectacularSwaggerView.as_view(
                'swagger-ui',
                url='/api/schema/',
            ),
        )

        app.register_blueprint(docs_bp, url_prefix='/api')
