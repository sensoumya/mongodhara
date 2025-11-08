import logging
import os

log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

logger = logging.getLogger("mongo-api")

# Log the configured log level
logger.info(f"Log level: {log_level_str}")

logging.getLogger("pymongo").setLevel(logging.INFO)
logging.getLogger("pymongo.topology").setLevel(logging.INFO)
