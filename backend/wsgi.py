import asyncio
import logging
from api.fastapi_app import create_app

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def initialize_application():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(create_app('production'))
    except Exception as e:
        logger.error("Failed to initialize application", exc_info=True)
        raise

application = initialize_application()