import logging

# Set global logging config
logging.basicConfig(
    level=logging.DEBUG,  # This is your app's base log level
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)

# App logger
logger = logging.getLogger("mongo-api")

# 🔇 Suppress overly verbose pymongo logs
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
