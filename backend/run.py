from dotenv import load_dotenv
import logging
from api import create_app

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables at startup
load_dotenv()

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        logger.info("Starting development server...")
        app = create_app('development')
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )
    except Exception as e:
        logger.error("Failed to start development server", exc_info=True)
        raise