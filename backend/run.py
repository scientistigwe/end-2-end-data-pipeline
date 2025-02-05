# run.py
from dotenv import load_dotenv
import logging
import asyncio
from api import create_app
import sys
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

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


async def async_main():
    """Main asynchronous entrypoint"""
    try:
        logger.info("Starting development server...")
        app = await init_app()

        # Configure Hypercorn
        config = Config()
        config.bind = ["0.0.0.0:5000"]
        config.use_reloader = False
        config.worker_class = "asyncio"

        await serve(app, config)

    except Exception as e:
        logger.error("Failed to start development server", exc_info=True)
        raise


def run_app():
    """Entry point for running the application"""
    try:
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        asyncio.run(async_main())

    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error("Application runtime error", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    run_app()