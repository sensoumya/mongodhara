# SPDX-License-Identifier: MIT
import base64
import binascii
import logging
import os
import re
import time

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import ENABLE_OPAQUE_IDS
from app.core.exceptions import InvalidOpaqueIDError
from app.core.logger import logger


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Custom access logging middleware that preserves encrypted paths in logs
    when not in DEBUG mode (for security).
    
    In DEBUG mode: Shows decrypted paths (for development troubleshooting)
    In production (INFO+): Shows original encrypted paths (security best practice)
    """
    
    async def dispatch(self, request: Request, call_next):
        # Store original path in request.state BEFORE any other middleware processes it
        if not hasattr(request.state, "original_path"):
            request.state.original_path = request.url.path
            request.state.original_query = request.url.query
        
        # Get stored original values (in case previous middleware already stored them)
        original_path = request.state.original_path
        original_query = request.state.original_query
        full_url = f"{original_path}?{original_query}" if original_query else original_path
        
        client = request.client
        client_host = f"{client.host}:{client.port}" if client else "unknown"
        method = request.method
        
        # Start timer
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log based on log level
        if logger.isEnabledFor(logging.DEBUG):
            # DEBUG mode: Log with decrypted path (from request.scope which may be modified)
            final_path = request.scope.get("path", original_path)
            final_query = request.scope.get("query_string", b"").decode("utf-8")
            final_url = f"{final_path}?{final_query}" if final_query else final_path
            logger.debug(
                f'{client_host} - "{method} {final_url} HTTP/1.1" '
                f'{response.status_code} (decrypted path, {process_time:.3f}s)'
            )
        else:
            # Production (INFO+): Log with original encrypted path for security
            logger.info(
                f'{client_host} - "{method} {full_url} HTTP/1.1" {response.status_code}'
            )
        
        return response


class OpaqueIDDecodingMiddleware(BaseHTTPMiddleware):
    """
    Decode and validate opaque IDs in path parameters.
    
    Security properties:
    1. Validates opaque ID integrity (AES-GCM authentication)
    2. Validates decoded value format (injection prevention)
    3. Fails fast on invalid input (before auth/authz)
    
    Only decrypts when ENABLE_OPAQUE_IDS=true
    """
    
    # Map path patterns to parameter types (order matters - process left to right)
    OPAQUE_PATTERNS = [
        (r'/v1/db/([^/]+)', 'database'),           # Database name
        (r'/col/([^/]+)', 'collection'),           # Collection name
        (r'/gridfs/([^/]+)', 'bucket'),            # Bucket name (GridFS)
        (r'/indexes/([^/]+)', 'index'),            # Index name
    ]
    
    # Known route segments that are NOT opaque IDs
    SKIP_SEGMENTS = {
        'col', 'doc', 'stats', 'export', 'import',
        'gridfs', 'upload', 'files', 'file', 'download',
        'indexes', 'text', 'query', 'permissions', 'check',
        'admin', 'groups', 'users'
    }
    
    async def dispatch(self, request: Request, call_next):
        # Only process if opaque IDs are enabled
        if not ENABLE_OPAQUE_IDS:
            return await call_next(request)
        
        # Skip health check and docs
        # Use the path from request.scope which may have been modified by PathDecodingMiddleware
        path = request.scope.get("path", request.url.path)
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"OpaqueIDDecodingMiddleware processing path: {path}")
        
        if path in ['/health', '/docs', '/redoc', '/openapi.json']:
            return await call_next(request)
        
        try:
            decoded_params = {}  # Track what we decoded for logging
            modified_path = path
            
            # Process each pattern in order
            for pattern, param_type in self.OPAQUE_PATTERNS:
                matches = list(re.finditer(pattern, modified_path))
                
                if logger.isEnabledFor(logging.DEBUG) and matches:
                    logger.debug(f"Pattern '{pattern}' found {len(matches)} match(es) in path: {modified_path}")
                
                for match in matches:
                    opaque_value = match.group(1)
                    
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Processing potential {param_type}: {opaque_value[:30]}...")
                    
                    # Skip known route segments
                    if opaque_value in self.SKIP_SEGMENTS:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Skipping known route segment: {opaque_value}")
                        continue
                    
                    # Skip if looks like MongoDB ObjectId (24 hex chars)
                    if param_type not in ['user_email', 'group_name'] and re.match(r'^[0-9a-fA-F]{24}$', opaque_value):
                        continue
                    
                    # STEP 1: Decode (validates integrity via AES-GCM)
                    try:
                        from app.services.opaque_id_service import decode_opaque_id
                        decoded_value = decode_opaque_id(opaque_value)
                    except InvalidOpaqueIDError:
                        logger.warning(f"Invalid opaque ID for {param_type}: {opaque_value[:20]}...")
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Invalid or tampered opaque ID"}
                        )
                    except Exception as e:
                        logger.error(f"Failed to decode opaque ID for {param_type}: {e}")
                        return JSONResponse(
                            status_code=400,
                            content={"detail": "Invalid opaque ID format"}
                        )
                    
                    # STEP 2: Validate format (prevent injection)
                    try:
                        self._validate_decoded_value(decoded_value, param_type)
                    except HTTPException as e:
                        # Don't log decoded value in production (security)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.warning(f"Validation failed for decoded {param_type}: {decoded_value}")
                        else:
                            logger.warning(f"Validation failed for {param_type}")
                        return JSONResponse(
                            status_code=e.status_code,
                            content={"detail": e.detail}
                        )
                    
                    # STEP 3: Replace in path (only first occurrence for this match)
                    old_segment = f'/{opaque_value}'
                    new_segment = f'/{decoded_value}'
                    modified_path = modified_path.replace(old_segment, new_segment, 1)
                    
                    decoded_params[param_type] = decoded_value
                    # Only log detailed decryption in DEBUG mode
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Decoded {param_type}: {opaque_value[:15]}... -> {decoded_value[:30]}")
            
            # Update request path if we decoded anything
            if decoded_params:
                request.scope["path"] = modified_path
                # Store decoded params for debugging/logging
                request.state.decoded_opaque_params = decoded_params
                # Only log decryption summary in DEBUG mode
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Decoded {len(decoded_params)} opaque ID(s) in path")
        
        except Exception as e:
            logger.error(f"Error in opaque ID middleware: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error processing request"}
            )
        
        # Continue to next middleware/handler
        return await call_next(request)
    
    def _validate_decoded_value(self, value: str, param_type: str):
        """Validate decoded value to prevent injection attacks"""
        from app.core.validators import (
            validate_collection_name_for_access,
            validate_database_name_for_access,
            validate_email_format,
            validate_index_name,
        )
        
        if param_type == "database":
            validate_database_name_for_access(value)
        elif param_type == "collection":
            validate_collection_name_for_access(value)
        elif param_type == "bucket":
            # Buckets follow collection naming rules
            validate_collection_name_for_access(value)
        elif param_type == "index":
            validate_index_name(value)
        elif param_type == "user_email":
            validate_email_format(value)
        elif param_type == "group_name":
            # Group names should follow similar rules to collection names
            # but allow more characters for descriptive names
            if not value or len(value) > 255:
                raise HTTPException(status_code=400, detail="Invalid group name length")
            if ".." in value or "\\" in value or value.startswith("$"):
                raise HTTPException(status_code=400, detail="Invalid characters in group name")
        else:
            # Generic validation for unknown types
            if not value or len(value) > 255:
                raise HTTPException(status_code=400, detail="Invalid parameter length")
            if ".." in value or "\\" in value:
                raise HTTPException(status_code=400, detail="Invalid characters in parameter")


class PathDecodingMiddleware(BaseHTTPMiddleware):
    """Middleware to decode paths before routing (supports both opaque IDs and base64)"""

    def _decode_base64_rfc4648(self, data: str) -> bytes:
        """Decode base64 string according to RFC 4648 Section 5 (URL-safe)"""
        # Add padding if needed - RFC 4648 Section 5 allows missing padding
        missing_padding = len(data) % 4
        if missing_padding:
            data += "=" * (4 - missing_padding)

        # Try URL-safe decoding first (RFC 4648 Section 5)
        # This handles - and _ characters instead of + and /
        try:    
            # time.sleep(1)   # to simulate real world delay
            return base64.urlsafe_b64decode(data)
        except (binascii.Error, ValueError):
            # Fallback to standard base64 if URL-safe fails
            return base64.b64decode(data)

    async def dispatch(self, request: Request, call_next):
        try:
            logger.debug(f"PathDecodingMiddleware: Incoming path: {request.url.path}")
            
            # Get root_path from app config or environment
            root_path = os.getenv("BASE_PATH", "")
            # Normalize root_path: ensure it starts with /, remove trailing /
            if root_path == "/":
                root_path = ""
            elif root_path:
                if not root_path.startswith("/"):
                    root_path = "/" + root_path
                if root_path.endswith("/"):
                    root_path = root_path[:-1]

            logger.debug(f"PathDecodingMiddleware: root_path='{root_path}'")

            # Enterprise security: When BASE_PATH is configured, reject direct access
            # Only allow requests that come through the expected base path
            if root_path and not request.url.path.startswith(root_path):
                from fastapi.responses import JSONResponse
                logger.debug("PathDecodingMiddleware: Rejecting - path doesn't start with BASE_PATH")
                return JSONResponse(
                    status_code=404,
                    content={"detail": "Not found"}
                )

            # Get the full path
            full_path = request.url.path

            # Remove root_path from the start if present
            if root_path and full_path.startswith(root_path):
                path_after_root = full_path[len(root_path) :].lstrip("/")
            else:
                path_after_root = full_path.lstrip("/")

            logger.debug(f"PathDecodingMiddleware: path_after_root='{path_after_root}'")

            # Skip decoding for docs, openapi.json, health check, and paths that already look like normal routes
            if (
                not path_after_root
                or path_after_root in ["docs", "openapi.json", "redoc"]
                or path_after_root.startswith(("docs/", "openapi.json", "redoc/"))
            ):
                logger.debug("PathDecodingMiddleware: Skipping - docs/health check")
                response = await call_next(request)
                return response

            # Check if path after root_path starts with version pattern (v1/, v2/, v3/, etc.)
            version_match = re.match(r"^(v\d+)/", path_after_root)
            logger.debug(f"PathDecodingMiddleware: version_match={version_match}")
            if version_match:
                version_prefix = version_match.group(1)  # e.g., 'v1', 'v2'
                encoded_part = path_after_root[len(version_prefix) + 1 :]

                if not encoded_part:
                    response = await call_next(request)
                    return response

                # Skip decoding for known API endpoints
                # Only try to decode if it looks like an encoded string
                if (
                    len(encoded_part) < 4  # Too short to be encoded
                    or encoded_part in ["permissions", "databases", "collections", "documents", "gridfs", "indexes"]  # Known endpoints
                ):
                    response = await call_next(request)
                    return response

                # Try to decode the remaining path
                try:
                    # Always use base64 decoding
                    decoded_bytes = self._decode_base64_rfc4648(encoded_part)
                    decoded_path = decoded_bytes.decode("utf-8").strip()
                    logger.debug(f"Base64 decoded: {encoded_part[:30]}... -> {decoded_path[:50]}")

                    # Validate that decoded path contains route structure
                    if decoded_path and ("/" in decoded_path or "?" in decoded_path):
                        # Split path and query string if present
                        if "?" in decoded_path:
                            new_path, query_string = decoded_path.split("?", 1)
                            # Join root_path, version_prefix, and new_path cleanly
                            joined_path = "/".join(
                                filter(
                                    None,
                                    [
                                        root_path.strip("/"),
                                        version_prefix,
                                        new_path.strip("/"),
                                    ],
                                )
                            )
                            request.scope["path"] = f"/{joined_path}"
                            request.scope["query_string"] = query_string.encode("utf-8")
                            logger.debug(f"Updated path to: /{joined_path}?{query_string}")
                        else:
                            joined_path = "/".join(
                                filter(
                                    None,
                                    [
                                        root_path.strip("/"),
                                        version_prefix,
                                        decoded_path.strip("/"),
                                    ],
                                )
                            )
                            request.scope["path"] = f"/{joined_path}"
                            logger.debug(f"Updated path to: /{joined_path}")
                    else:
                        logger.debug(f"Decoded path '{decoded_path}' doesn't look like a valid route - skipping")

                except (ValueError, binascii.Error, UnicodeDecodeError) as e:
                    # If decoding fails, log warning and continue with original path
                    # This allows OpaqueIDDecodingMiddleware to potentially handle it
                    logger.debug(f"Base64 decoding failed for {version_prefix} path: {e} - continuing with original path")

        except HTTPException:
            # Re-raise HTTP exceptions (like 400 Bad Request)
            raise
        except Exception as e:
            logger.error(f"Error in path decoding middleware: {e}")
            # Continue with original path if any error occurs

        response = await call_next(request)
        return response
