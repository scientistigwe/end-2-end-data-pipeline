# app/main.py
"""Application Entry Point"""
import os
import logging
from dotenv import load_dotenv
from backend.flask_api.app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Primary application initialization and execution."""
    try:
        # Load environment variables
        load_dotenv()

        # Determine environment
        env = os.getenv('FLASK_ENV', 'development').lower()
        port = int(os.getenv('PORT', 5000))
        host = os.getenv('HOST', '0.0.0.0')

        # Create application
        app = create_app(env)

        # Configure server
        debug = env == 'development'
        logger.info(f"Starting server in {env} mode")

        # Run application
        app.run(host=host, port=port, debug=debug)

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main()