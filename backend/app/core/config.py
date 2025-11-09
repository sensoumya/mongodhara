import os

from dotenv import load_dotenv

from app.core.logger import logger

# Load environment variables from .env file
load_dotenv()

# Environment variables (matching your K8s deployment)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
BASE_PATH = os.getenv("BASE_PATH", "")

# Additional configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

# Opaque ID configuration
ENABLE_OPAQUE_IDS = os.getenv("ENABLE_OPAQUE_IDS", "false").lower() in ("true", "1", "yes", "on")

# Opaque ID encryption key (base64 encoded 128-bit key) - required when encryption is enabled
OPAQUE_ID_ENCRYPTION_KEY = os.getenv("OPAQUE_ID_ENCRYPTION_KEY", "")
if ENABLE_OPAQUE_IDS and not OPAQUE_ID_ENCRYPTION_KEY:
    raise ValueError("OPAQUE_ID_ENCRYPTION_KEY environment variable is required when ENABLE_OPAQUE_IDS is true")

# Authorization configuration
ENABLE_AUTHZ = os.getenv("ENABLE_AUTHZ", "false").lower() in ("true", "1", "yes", "on")

# OAuth/Authentication header configuration
AUTH_EMAIL_HEADER = os.getenv("AUTH_EMAIL_HEADER", "X-Auth-Request-Email")

# Audit logging configuration
ENABLE_AUDIT_LOGGING = os.getenv("ENABLE_AUDIT_LOGGING", "false").lower() in ("true", "1", "yes", "on")

# GridFS configuration
GRIDFS_CHUNK_SIZE = int(os.getenv("GRIDFS_CHUNK_SIZE", "1048576"))  # 1MB default
GRIDFS_MAX_FILE_SIZE = int(os.getenv("GRIDFS_MAX_FILE_SIZE", "104857600"))  # 100MB default
GRIDFS_TIMEOUT = int(os.getenv("GRIDFS_TIMEOUT", "300"))  # 5 minutes default

# Log configuration values
logger.info(f"Opaque ID encryption enabled: {ENABLE_OPAQUE_IDS}")
logger.info(f"Authorization enabled: {ENABLE_AUTHZ}")
if ENABLE_AUTHZ:
    logger.debug(f"Auth email header: {AUTH_EMAIL_HEADER}")
logger.info(f"Audit logging enabled: {ENABLE_AUDIT_LOGGING}")
logger.info(f"GridFS chunk size: {GRIDFS_CHUNK_SIZE / 1048576:.1f} MB")
logger.info(f"GridFS max file size: {GRIDFS_MAX_FILE_SIZE / 1048576:.1f} MB")
logger.info(f"GridFS timeout: {GRIDFS_TIMEOUT} seconds")
