import logging
from api.app import create_app

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    logger.info("Initializing application...")
    app = create_app()
    logger.info("Application initialized successfully")
except Exception as e:
    logger.error(f"Failed to create application: {e}", exc_info=True)
    raise

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server...")
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise