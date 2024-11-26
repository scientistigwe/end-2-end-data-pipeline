"""Application Entry Point"""
import os
from backend.flask_api.app import create_app

def main():
    """
    Primary application initialization and execution.
    """
    # Determine environment
    env = os.getenv('FLASK_ENV', 'development').lower()

    # Create and run application
    app = create_app(env)

    # Run app based on environment
    if env == 'development':
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()