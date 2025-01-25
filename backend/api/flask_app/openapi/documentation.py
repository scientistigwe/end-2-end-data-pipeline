# flask_app/openapi/documentation.py
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec.extension import FlaskApiSpec
from flask import Blueprint, jsonify
from flask_apispec import doc, use_kwargs, marshal_with
from marshmallow import Schema


class APIDocumentation:
    def __init__(self, app=None):
        self.spec = None
        self.docs = None
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        # Configure APISpec with marshmallow plugin
        app.config.update({
            'APISPEC_SPEC': APISpec(
                title='Data Pipeline API',
                version='1.0.0',
                openapi_version='3.0.2',
                plugins=[MarshmallowPlugin()],
                info={
                    'description': 'API documentation for the Data Pipeline system',
                    'contact': {'email': 'your-email@example.com'}
                },
                security=[{'Bearer': []}],
                servers=[
                    {
                        'url': '/api/v1',
                        'description': 'Development server'
                    }
                ]
            ),
            'APISPEC_SWAGGER_URL': '/swagger/',  # URI to access API Doc JSON
            'APISPEC_SWAGGER_UI_URL': '/docs/'  # URI to access UI of API Doc
        })

        # Initialize FlaskApiSpec
        self.docs = FlaskApiSpec(app)

        # Create documentation blueprint
        docs_bp = Blueprint('api_docs', __name__)

        # Add a simple endpoint to redirect to docs
        @docs_bp.route('/')
        def api_docs():
            return jsonify({
                'message': 'API Documentation',
                'swagger_url': '/api/docs/',
                'swagger_json': '/api/swagger/'
            })

        app.register_blueprint(docs_bp, url_prefix='/api')

        # Store APISpec instance for later use
        self.spec = app.config['APISPEC_SPEC']


# Example schemas for documentation
class ErrorSchema(Schema):
    message = fields.String(description="Error message")
    code = fields.Integer(description="Error code")


class SuccessSchema(Schema):
    message = fields.String(description="Success message")
    data = fields.Dict(description="Response data")


# Example of how to document a route
"""
from flask_apispec import doc, use_kwargs, marshal_with

@doc(
    tags=['Pipeline'],
    description='Get the status of all active pipelines',
    security=[{"Bearer": []}]
)
@marshal_with(SuccessSchema, code=200)
@marshal_with(ErrorSchema, code=401)
@marshal_with(ErrorSchema, code=500)
def get_pipeline_status():
    pass
"""

# Security schemes definition
security_schemes = {
    "Bearer": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter JWT Bearer token"
    }
}


# Helper function to register views with APISpec
def register_swagger_views(docs, app):
    """
    Register views with APISpec for documentation.
    Should be called after all routes are registered.
    """
    with app.app_context():
        # Add security schemes
        docs.spec.components.security_scheme("Bearer", security_schemes["Bearer"])

        # Register views - example:
        # docs.register(get_pipeline_status, blueprint='pipeline_bp')


# Example middleware to add CORS headers for documentation
def add_documentation_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response