# main.py
# FastAPI application for MongoDB management
# 
# Development: python main.py
# Production: gunicorn -c gunicorn.conf.py main:app
# Or use: ./run_server.sh

import base64
import binascii
import io
import json
import re
from typing import Optional

import uvicorn

# Load environment variables for Gunicorn compatibility
from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Body,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pymongo.errors import CollectionInvalid, OperationFailure
from starlette.middleware.base import BaseHTTPMiddleware

from logger import logger
from mongo_service import DatabaseExistsError, MongoService

load_dotenv()

# -------------------- Validation Functions --------------------

def validate_database_name_for_create(db_name: str) -> None:
    """Validate MongoDB database name for CREATE operations - strict MongoDB naming conventions."""
    if not db_name or db_name.strip() == "":
        raise HTTPException(status_code=400, detail="Database name cannot be empty")
    
    db_name = db_name.strip()
    
    # Check length (MongoDB limit is 64 bytes for database names)
    if len(db_name.encode('utf-8')) > 64:
        raise HTTPException(status_code=400, detail="Database name cannot exceed 64 bytes when UTF-8 encoded")
    
    # Check for invalid characters
    invalid_chars = ['/', '\\', '.', ' ', '"', '*', '<', '>', ':', '|', '?', '$']
    for char in invalid_chars:
        if char in db_name:
            raise HTTPException(status_code=400, detail=f"Database name cannot contain '{char}' character")
    
    # Check for reserved names (case-insensitive)
    reserved_names = ['admin', 'local', 'config']
    if db_name.lower() in reserved_names:
        raise HTTPException(status_code=400, detail=f"'{db_name}' is a reserved database name")
    
    # Database names are case-insensitive, but let's enforce lowercase for consistency
    if db_name != db_name.lower():
        raise HTTPException(status_code=400, detail="Database name should be lowercase")


def validate_database_name_for_access(db_name: str) -> None:
    """Validate MongoDB database name for READ/ACCESS operations - permissive for existing data."""
    if not db_name or db_name.strip() == "":
        raise HTTPException(status_code=400, detail="Database name cannot be empty")
    
    # Only check if it's not empty - allow existing databases with any naming


def validate_collection_name_for_create(col_name: str) -> None:
    """Validate MongoDB collection name for CREATE operations - strict MongoDB naming conventions."""
    if not col_name or col_name.strip() == "":
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")
    
    col_name = col_name.strip()
    
    # Check length (MongoDB doesn't have a strict limit, but 120 is reasonable)
    if len(col_name.encode('utf-8')) > 120:
        raise HTTPException(status_code=400, detail="Collection name cannot exceed 120 bytes when UTF-8 encoded")
    
    # Cannot start with 'system.' (reserved for MongoDB internal collections)
    if col_name.startswith("system."):
        raise HTTPException(status_code=400, detail="Collection name cannot start with 'system.' (reserved prefix)")
    
    # Cannot contain '$' character
    if "$" in col_name:
        raise HTTPException(status_code=400, detail="Collection name cannot contain '$' character")
    
    # Cannot contain null character
    if "\x00" in col_name:
        raise HTTPException(status_code=400, detail="Collection name cannot contain null character")
    
    # Cannot be empty string after stripping
    if not col_name:
        raise HTTPException(status_code=400, detail="Collection name cannot be empty or only whitespace")


def validate_collection_name_for_access(col_name: str) -> None:
    """Validate MongoDB collection name for READ/ACCESS operations - permissive for existing data."""
    if not col_name or col_name.strip() == "":
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")
    
    # Only check if it's not empty - allow existing collections with any naming


class PathDecodingMiddleware(BaseHTTPMiddleware):
    """Middleware to decode base64-encoded paths before routing (RFC 4648 Section 5 compliant)"""
    
    def _decode_base64_rfc4648(self, data: str) -> bytes:
        """Decode base64 string according to RFC 4648 Section 5 (URL-safe)"""
        # Add padding if needed - RFC 4648 Section 5 allows missing padding
        missing_padding = len(data) % 4
        if missing_padding:
            data += '=' * (4 - missing_padding)
        
        # Try URL-safe decoding first (RFC 4648 Section 5)
        # This handles - and _ characters instead of + and /
        try:
            return base64.urlsafe_b64decode(data)
        except (binascii.Error, ValueError):
            # Fallback to standard base64 if URL-safe fails
            return base64.b64decode(data)
    
    async def dispatch(self, request: Request, call_next):
        try:
            # Get the path without leading slash
            path = request.url.path.lstrip('/')
            
            # Skip decoding for docs, openapi.json, health check, and paths that already look like normal routes
            if not path or path in ['docs', 'openapi.json', 'redoc'] or path.startswith(('docs/', 'openapi.json', 'redoc/')):
                response = await call_next(request)
                return response
            
            # Check if path starts with version pattern (v1/, v2/, v3/, etc.) - handle versioned encoded paths
            version_match = re.match(r'^(v\d+)/', path)
            if version_match:
                version_prefix = version_match.group(1)  # e.g., 'v1', 'v2'
                encoded_part = path[len(version_prefix) + 1:]  # Remove 'v1/' or 'v2/' prefix
                
                if not encoded_part:
                    response = await call_next(request)
                    return response
                
                # Skip if the remaining path looks like a normal route (contains '/')
                if '/' in encoded_part[:15]:  # Check first 15 chars for route structure
                    response = await call_next(request)
                    return response
                    
                # Try to decode the remaining path as base64
                try:
                    decoded_bytes = self._decode_base64_rfc4648(encoded_part)
                    decoded_path = decoded_bytes.decode('utf-8').strip()
                    
                    # Validate that decoded path contains route structure
                    if decoded_path and ('/' in decoded_path or '?' in decoded_path):
                        # Split path and query string if present
                        if '?' in decoded_path:
                            new_path, query_string = decoded_path.split('?', 1)
                            # Update request scope with version prefix
                            request.scope["path"] = f"/{version_prefix}/{new_path}"
                            request.scope["query_string"] = query_string.encode('utf-8')
                        else:
                            request.scope["path"] = f"/{version_prefix}/{decoded_path}"
                        
                        logger.debug(f"RFC 4648 Section 5 decoded {version_prefix} path: {path} -> {version_prefix}/{decoded_path}")
                        
                except (binascii.Error, UnicodeDecodeError, ValueError) as e:
                    # If decoding fails, continue with original path
                    logger.debug(f"Base64 decoding failed for {version_prefix} path (expected for normal routes): {e}")
                    pass
                    
        except Exception as e:
            logger.error(f"Error in path decoding middleware: {e}")
            # Continue with original path if any error occurs
            pass
        
        response = await call_next(request)
        return response


app = FastAPI(
    title="MongoDB Management API",
    version="2.0.0",
    description="Refactored API for MongoDB with compact routes, security, and CRUD support.",
    openapi_tags=[
        {
            "name": "Database Management",
            "description": "Operations for managing MongoDB databases - create, list, and delete databases"
        },
        {
            "name": "Collection Management", 
            "description": "Operations for managing collections within databases - create, list, and delete collections"
        },
        {
            "name": "Document Management",
            "description": "CRUD operations for documents within collections - create, read, update, delete, and query documents"
        },
        {
            "name": "Data Import/Export",
            "description": "Import and export data to/from collections in various formats"
        },
        {
            "name": "GridFS File Storage",
            "description": "File storage operations using MongoDB GridFS - upload, download, list, and delete files"
        }
    ]
)

# Add path decoding middleware first (before CORS)
app.add_middleware(PathDecodingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
v1_router = APIRouter(prefix="/v1", tags=["v1"])

mongo = MongoService()

# -------------------- Models --------------------

class DocumentUpdate(BaseModel):
    data: dict = Field(..., description="Fields and values to update in the document")


class CreateDocument(BaseModel):
    data: dict = Field(..., description="New document to insert")


# -------------------- Database APIs --------------------

@v1_router.get("/db", summary="List databases with pagination and filter", tags=["Database Management"])
def list_databases(
    search: Optional[str] = Query(None, description="Search databases whose name contains this string"),
    sort: Optional[str] = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    sort_field: Optional[str] = Query(None, description="(Unused for now) Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of databases per page (max 100)")
):
    try:
        return mongo.list_databases(search, sort, page, page_size, sort_field, sort_order)
    except Exception as e:
        logger.error(f"Failed to list databases: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list databases")


@v1_router.post("/db/{db}", summary="Create a new database", tags=["Database Management"])
def create_database(
    db: str,
    collection_name: str = Query(..., description="Name of the initial collection to create in the database")
):
    # Validate database name for creation
    validate_database_name_for_create(db)
    
    # Validate collection name for creation
    validate_collection_name_for_create(collection_name)
    
    try:
        mongo.create_database(db, collection_name.strip())
        return {"message": f"Database '{db}' created successfully with collection '{collection_name.strip()}'"}
    except DatabaseExistsError as e:
        # Handle database already exists error specifically
        logger.error(f"Database '{db}' already exists: {e}")
        raise HTTPException(status_code=409, detail=f"Database '{db}' already exists")
    except CollectionInvalid as e:
        # Handle collection-specific validation errors
        logger.error(f"Collection validation error for '{collection_name}' in DB '{db}': {e}")
        raise HTTPException(status_code=400, detail=f"Invalid collection name '{collection_name}': {str(e)}")
    except OperationFailure as e:
        # Handle other MongoDB operation errors (database existence is handled by DatabaseExistsError)
        error_msg = str(e)
        if "invalid" in error_msg.lower() and "name" in error_msg.lower():
            logger.error(f"Invalid database name '{db}': {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid database name '{db}': {e.details.get('errmsg', str(e))}"
            )
        else:
            logger.error(f"MongoDB operation failed for database creation '{db}': {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Failed to create database '{db}': {e.details.get('errmsg', str(e))}"
            )
    except Exception as e:
        logger.error(f"Failed to create database '{db}' with collection '{collection_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create database")


@v1_router.delete("/db/{db}", summary="Delete a database", tags=["Database Management"])
def delete_database(db: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    try:
        mongo.delete_database(db)
        return {"message": f"Database '{db}' deleted successfully"}
    except OperationFailure as e:
        # Handle MongoDB specific errors with user-friendly messages
        error_msg = str(e)
        if "prohibited" in error_msg.lower():
            logger.error(f"Attempted to delete prohibited database '{db}': {e}")
            raise HTTPException(
                status_code=403, 
                detail=f"Cannot delete database '{db}': {e.details.get('errmsg', 'Operation prohibited')}"
            )
        elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"Database '{db}' not found: {e}")
            raise HTTPException(status_code=404, detail=f"Database '{db}' not found")
        else:
            logger.error(f"MongoDB operation failed for database '{db}': {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to delete database '{db}': {e.details.get('errmsg', str(e))}"
            )
    except Exception as e:
        logger.error(f"Failed to delete database '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete database")


# -------------------- Collection APIs --------------------

@v1_router.get("/db/{db}/col", summary="List collections with pagination and filter", tags=["Collection Management"])
def list_collections(
    db: str,
    search: Optional[str] = Query(None, description="Search collection name contains"),
    sort: Optional[str] = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    sort_field: Optional[str] = Query(None, description="(Unused for now) Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of collections per page (max 100)")
):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    try:
        return mongo.list_collections(db, search, sort, page, page_size, sort_field, sort_order)
    except Exception as e:
        logger.error(f"Failed to list collections for DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list collections")


@v1_router.post("/db/{db}/col/{col}", summary="Create a new collection", tags=["Collection Management"])
def create_collection(db: str, col: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for creation
    validate_collection_name_for_create(col)
    
    try:
        mongo.create_collection(db, col)
        return {"message": f"Collection '{col}' created successfully in DB '{db}'"}
    except CollectionInvalid as e:
        # Handle collection already exists or validation errors
        error_msg = str(e)
        if "already exists" in error_msg.lower():
            logger.error(f"Collection '{col}' already exists in DB '{db}': {e}")
            raise HTTPException(status_code=409, detail=f"Collection '{col}' already exists in database '{db}'")
        else:
            logger.error(f"Collection validation error for '{col}' in DB '{db}': {e}")
            raise HTTPException(status_code=400, detail=f"Invalid collection name '{col}': {str(e)}")
    except OperationFailure as e:
        # Handle MongoDB specific errors (collection existence is handled by CollectionInvalid)
        error_msg = str(e)
        if "database does not exist" in error_msg.lower() or "not found" in error_msg.lower():
            logger.error(f"Database '{db}' not found: {e}")
            raise HTTPException(status_code=404, detail=f"Database '{db}' not found")
        elif "invalid" in error_msg.lower() and "name" in error_msg.lower():
            logger.error(f"Invalid collection name '{col}': {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid collection name '{col}': {e.details.get('errmsg', str(e))}"
            )
        else:
            logger.error(f"MongoDB operation failed for collection creation '{col}' in DB '{db}': {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to create collection '{col}': {e.details.get('errmsg', str(e))}"
            )
    except Exception as e:
        logger.error(f"Failed to create collection '{col}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create collection")

@v1_router.delete("/db/{db}/col/{col}", summary="Delete a collection", tags=["Collection Management"])
def delete_collection(db: str, col: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for access
    validate_collection_name_for_access(col)
    
    try:
        mongo.delete_collection(db, col)
        return {"message": f"Collection '{col}' deleted successfully from DB '{db}'"}
    except OperationFailure as e:
        # Handle MongoDB specific errors
        error_msg = str(e)
        if "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
            logger.error(f"Collection '{col}' not found in DB '{db}': {e}")
            raise HTTPException(status_code=404, detail=f"Collection '{col}' not found in database '{db}'")
        elif "database does not exist" in error_msg.lower():
            logger.error(f"Database '{db}' not found: {e}")
            raise HTTPException(status_code=404, detail=f"Database '{db}' not found")
        else:
            logger.error(f"MongoDB operation failed for collection deletion '{col}' in DB '{db}': {e}")
            raise HTTPException(
                status_code=400, 
                detail=f"Failed to delete collection '{col}': {e.details.get('errmsg', str(e))}"
            )
    except Exception as e:
        logger.error(f"Failed to delete collection '{col}' from DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete collection '{col}' from DB '{db}'")


# -------------------- Document APIs --------------------

@v1_router.post("/db/{db}/col/{col}/doc", summary="Create a new document", tags=["Document Management"])
def create_document(db: str, col: str, payload: CreateDocument):
    # Validate database name for access (document creation in existing db)
    validate_database_name_for_access(db)
    
    # Validate collection name for access (document creation in existing collection)
    validate_collection_name_for_access(col)
    
    try:
        # Filter out _id field from payload if present
        filtered_data = {k: v for k, v in payload.data.items() if k != "_id"}
        
        inserted_id = mongo.insert_document(db, col, filtered_data)
        return {"message": f"Document inserted with ID: {inserted_id}"}
    except Exception as e:
        logger.error(f"Failed to insert document into {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to insert document")



@v1_router.post(
    "/db/{db}/col/{col}/doc/query",
    summary="Query documents (supports advanced MongoDB operators)",
    tags=["Document Management"],
    description="""
    Query documents in a collection using any valid MongoDB filter operators (e.g., $or, $and, $in, $gt, $lt, etc.).
    Example body:
    {
      "filter": {"$or": [{"age": {"$gt": 30}}, {"status": "active"}]}
    }
    """
)
def query_documents(
    db: str,
    col: str,
    body: dict = Body(default={}, description="MongoDB filter query as JSON. Supports all MongoDB operators."),
    sort_field: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of documents per page")
):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for access
    validate_collection_name_for_access(col)
    
    try:
        filter = body.get("filter", {})
        # filter is passed as-is to PyMongo, so all advanced operators are supported
        return mongo.query_collection(db, col, filter, sort_field, sort_order, page, page_size)
    except ValueError as e:
        logger.error(f"Invalid request format for query: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid request format")
    except Exception as e:
        logger.error(f"Failed to query documents in {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to query documents")


@v1_router.get("/db/{db}/col/{col}/doc/{doc_id}", summary="Get document by ID", tags=["Document Management"])
def get_document(db: str, col: str, doc_id: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for access
    validate_collection_name_for_access(col)
    
    try:
        doc = mongo.get_document(db, col, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        return doc
    except ValueError as e:
        logger.error(f"Invalid document ID '{doc_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Failed to retrieve document '{doc_id}' from {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@v1_router.put("/db/{db}/col/{col}/doc/{doc_id}", summary="Update document by ID", tags=["Document Management"])
def update_document(db: str, col: str, doc_id: str, update: DocumentUpdate):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for access
    validate_collection_name_for_access(col)
    
    try:
        # Filter out _id field from update data if present
        filtered_data = {k: v for k, v in update.data.items() if k != "_id"}
        
        modified = mongo.update_document(db, col, doc_id, filtered_data)
        if modified == 0:
            raise HTTPException(status_code=404, detail="Document not found or not modified")
        return {"message": f"Document with ID {doc_id} updated successfully"}
    except ValueError as e:
        logger.error(f"Invalid document ID '{doc_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Failed to update document '{doc_id}' in {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update document")


@v1_router.delete("/db/{db}/col/{col}/doc/{doc_id}", summary="Delete document by ID", tags=["Document Management"])
def delete_document(db: str, col: str, doc_id: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for access
    validate_collection_name_for_access(col)
    
    try:
        deleted = mongo.delete_document(db, col, doc_id)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": f"Document with ID {doc_id} deleted successfully"}
    except ValueError as e:
        logger.error(f"Invalid document ID '{doc_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Failed to delete document '{doc_id}' from {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete document")


@v1_router.get("/db/{db}/col/{col}/export", summary="Export collection", tags=["Data Import/Export"])
def export_collection(db: str, col: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for access
    validate_collection_name_for_access(col)
    
    try:
        return {"documents": mongo.export_collection(db, col)}
    except Exception as e:
        logger.error(f"Failed to export collection {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export collection")


@v1_router.post("/db/{db}/col/{col}/import", summary="Import documents from JSON file into a collection", tags=["Data Import/Export"])
def import_documents(
    db: str, 
    col: str, 
    file: UploadFile = File(..., description="JSON file containing documents to import")
):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate collection name for access
    validate_collection_name_for_access(col)
    
    try:
        # Validate file type
        if not file.filename or not file.filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")
        
        # Read and parse the JSON file
        file_content = file.file.read()
        try:
            json_data = json.loads(file_content.decode('utf-8'))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail="Invalid JSON format")
        
        # Handle different JSON structures - support both export format and direct array
        if isinstance(json_data, list):
            # Direct array of documents
            documents = json_data
        elif isinstance(json_data, dict) and 'documents' in json_data:
            # Export format with 'documents' key
            documents = json_data['documents']
        else:
            raise HTTPException(status_code=400, detail="JSON must be either an array of documents or contain a 'documents' key")
        
        if not isinstance(documents, list):
            raise HTTPException(status_code=400, detail="Documents must be a list")
        
        # Filter out _id field from all documents if present
        filtered_documents = []
        for doc in documents:
            if isinstance(doc, dict):
                filtered_doc = {k: v for k, v in doc.items() if k != "_id"}
                filtered_documents.append(filtered_doc)
            else:
                filtered_documents.append(doc)  # Keep non-dict items as-is
        
        inserted = mongo.import_documents(db, col, filtered_documents)
        return {"message": f"Imported {len(inserted)} documents successfully", "imported_count": len(inserted)}
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during import: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to import documents into {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to import documents")


# -------------------- GridFS Bucket APIs --------------------

@v1_router.get("/db/{db}/gridfs/buckets", summary="List all GridFS buckets in a database", tags=["GridFS File Storage"])
def list_gridfs_buckets(
    db: str,
    search: Optional[str] = Query(None, description="Search for bucket names containing this string"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of buckets per page")
):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    try:
        return mongo.list_gridfs_buckets(db, search, page, page_size)
    except Exception as e:
        logger.error(f"Failed to list GridFS buckets in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list GridFS buckets")


@v1_router.post("/db/{db}/gridfs/{bucket_name}/upload", summary="Upload a file to a specific GridFS bucket", tags=["GridFS File Storage"])
def upload_file_to_bucket(
    db: str,
    bucket_name: str,
    file: UploadFile = File(...),
    metadata: str = Form(default="{}", description="JSON metadata for the file")
):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access (use collection name validation as buckets are collections)
    validate_collection_name_for_access(bucket_name)
    
    try:
        metadata_dict = json.loads(metadata) if metadata != "{}" else {}
        
        file_content = file.file.read()
        file_id = mongo.upload_file_to_bucket(
            db, 
            bucket_name,
            file_content, 
            file.filename, 
            file.content_type,
            metadata_dict
        )
        
        return {
            "message": f"File '{file.filename}' uploaded successfully to bucket '{bucket_name}'",
            "file_id": file_id,
            "bucket_name": bucket_name
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON metadata")
    except Exception as e:
        logger.error(f"Failed to upload file to GridFS bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload file")


@v1_router.get("/db/{db}/gridfs/{bucket_name}/files", summary="List files in a specific GridFS bucket", tags=["GridFS File Storage"])
def list_files_in_bucket(
    db: str,
    bucket_name: str,
    search: Optional[str] = Query(None, description="Search for files containing this string in filename"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of files per page")
):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)
    
    try:
        return mongo.list_files_in_bucket(db, bucket_name, search, page, page_size)
    except Exception as e:
        logger.error(f"Failed to list GridFS files in bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list files")


@v1_router.get("/db/{db}/gridfs/{bucket_name}/file/{file_id}", summary="Get file metadata from a specific bucket", tags=["GridFS File Storage"])
def get_file_metadata_from_bucket(db: str, bucket_name: str, file_id: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)
    
    try:
        metadata = mongo.get_file_metadata_from_bucket(db, bucket_name, file_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")
        return metadata
    except ValueError as e:
        logger.error(f"Invalid file ID '{file_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid file ID")
    except Exception as e:
        logger.error(f"Failed to get file metadata for '{file_id}' in bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get file metadata")


@v1_router.get("/db/{db}/gridfs/{bucket_name}/file/{file_id}/download", summary="Download file by ID from a specific bucket", tags=["GridFS File Storage"])
def download_file_from_bucket(db: str, bucket_name: str, file_id: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)
    
    try:
        file_data = mongo.download_file_from_bucket(db, bucket_name, file_id)
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        return StreamingResponse(
            io.BytesIO(file_data['content']),
            media_type=file_data['content_type'] or 'application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={file_data['filename']}"
            }
        )
    except ValueError as e:
        logger.error(f"Invalid file ID '{file_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid file ID")
    except Exception as e:
        logger.error(f"Failed to download file '{file_id}' from bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download file")


@v1_router.get("/db/{db}/gridfs/{bucket_name}/filename/{filename}/download", summary="Download latest file by filename from a specific bucket", tags=["GridFS File Storage"])
def download_file_by_name_from_bucket(db: str, bucket_name: str, filename: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)
    
    try:
        file_data = mongo.download_file_by_name_from_bucket(db, bucket_name, filename)
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found")
        
        return StreamingResponse(
            io.BytesIO(file_data['content']),
            media_type=file_data['content_type'] or 'application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={file_data['filename']}"
            }
        )
    except Exception as e:
        logger.error(f"Failed to download file '{filename}' from bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download file")


@v1_router.delete("/db/{db}/gridfs/{bucket_name}/file/{file_id}", summary="Delete file by ID from a specific bucket", tags=["GridFS File Storage"])
def delete_file_from_bucket(db: str, bucket_name: str, file_id: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access (use collection name validation as buckets are collections)
    validate_collection_name_for_access(bucket_name)
    
    try:
        deleted = mongo.delete_file_from_bucket(db, bucket_name, file_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="File not found")
        return {"message": f"File with ID {file_id} deleted successfully from bucket '{bucket_name}'"}
    except ValueError as e:
        logger.error(f"Invalid file ID '{file_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid file ID")
    except Exception as e:
        logger.error(f"Failed to delete file '{file_id}' from bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete file")


@v1_router.delete("/db/{db}/gridfs/{bucket_name}/filename/{filename}", summary="Delete all files by filename from a specific bucket", tags=["GridFS File Storage"])
def delete_files_by_name_from_bucket(db: str, bucket_name: str, filename: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)
    
    try:
        deleted_count = mongo.delete_files_by_name_from_bucket(db, bucket_name, filename)
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="No files found with that filename")
        return {"message": f"Deleted {deleted_count} files named '{filename}' from bucket '{bucket_name}'"}
    except Exception as e:
        logger.error(f"Failed to delete files named '{filename}' from bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete files")


@v1_router.delete("/db/{db}/gridfs/{bucket_name}", summary="Delete an entire GridFS bucket", tags=["GridFS File Storage"])
def delete_bucket(db: str, bucket_name: str):
    # Validate database name for access
    validate_database_name_for_access(db)
    
    # Validate bucket name for access (use collection name validation as buckets are collections)
    validate_collection_name_for_access(bucket_name)
    
    try:
        mongo.delete_bucket(db, bucket_name)
        return {"message": f"Bucket '{bucket_name}' deleted successfully from DB '{db}'"}
    except Exception as e:
        logger.error(f"Failed to delete bucket '{bucket_name}' from DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete bucket")


# Include the v1 router after all endpoints are defined
app.include_router(v1_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_excludes=[
            ".env/",
            "venv/",
            "__pycache__/",
        ]
    )