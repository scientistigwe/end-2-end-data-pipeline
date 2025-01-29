# run.py
from dotenv import load_dotenv
import logging
import asyncio
from api import create_app

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables at startup
load_dotenv()

logger = logging.getLogger(__name__)


async def init_app():
    """Initialize the Flask application asynchronously"""
    try:
        app = await create_app('development')
        return app
    except Exception as e:
        logger.error("Failed to initialize application", exc_info=True)
        raise


def run_app():
    """Run the Flask application with proper async handling"""
    try:
        logger.info("Starting development server...")

        # Setup event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Initialize the app
        app = loop.run_until_complete(init_app())

        # Run Flask application
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=True,
            use_reloader=True
        )

    except Exception as e:
        logger.error("Failed to start development server", exc_info=True)
        raise
    finally:
        loop.close()


if __name__ == '__main__':
    run_app()