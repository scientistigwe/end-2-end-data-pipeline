import os
from flask_cors import CORS
from backend.backend.flask_api.app import create_app

def create_flask_app():
    # Set the environment for the Flask app (default to 'development')
    env = os.getenv('FLASK_ENV', 'development')
    flask_app = create_app(env)

    # Enable CORS for all routes (allowing all origins by default)
    CORS(flask_app, supports_credentials=True, resources={
        r"/file-system/*": {
            "origins": ["http://localhost:3000","http://localhost:3001"],  # Add your React app's origin
            "methods": ["POST", "OPTIONS", "GET"],
            "allow_headers": ["Content-Type"],
        }
    })

    return flask_app

if __name__ == '__main__':
    flask_app = create_flask_app()
    flask_app.run(debug=True)
