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
from typing import Optional

import uvicorn

# Load environment variables for Gunicorn compatibility
from dotenv import load_dotenv
from fastapi import Body, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from logger import logger
from mongo_service import MongoService
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()


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
            
            # Skip decoding if path is empty or looks like a normal route
            if not path or '/' in path[:10]:  # If path starts with normal route structure
                response = await call_next(request)
                return response
            
            # Try to decode the path as base64
            try:
                decoded_bytes = self._decode_base64_rfc4648(path)
                decoded_path = decoded_bytes.decode('utf-8').strip()
                
                # Validate that decoded path contains route structure
                if decoded_path and ('/' in decoded_path or '?' in decoded_path):
                    # Split path and query string if present
                    if '?' in decoded_path:
                        new_path, query_string = decoded_path.split('?', 1)
                        # Update request scope
                        request.scope["path"] = f"/{new_path}"
                        request.scope["query_string"] = query_string.encode('utf-8')
                    else:
                        request.scope["path"] = f"/{decoded_path}"
                    
                    logger.debug(f"RFC 4648 Section 5 decoded: {path} -> {decoded_path}")
                    
            except (binascii.Error, UnicodeDecodeError, ValueError) as e:
                # If decoding fails, continue with original path
                logger.debug(f"Base64 decoding failed (expected for normal routes): {e}")
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

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

mongo = MongoService()

# -------------------- Models --------------------

class DocumentUpdate(BaseModel):
    data: dict = Field(..., description="Fields and values to update in the document")


class CreateDocument(BaseModel):
    data: dict = Field(..., description="New document to insert")


# -------------------- Database APIs --------------------

@app.get("/db", summary="List databases with pagination and filter", tags=["Database Management"])
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


@app.post("/db/{db}", summary="Create a new database", tags=["Database Management"])
def create_database(
    db: str,
    collection_name: str = Query(..., description="Name of the initial collection to create in the database")
):
    # Validate collection name
    if not collection_name or collection_name.strip() == "":
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")
    
    if collection_name.startswith("system."):
        raise HTTPException(status_code=400, detail="Collection name cannot start with 'system.'")
    
    if "$" in collection_name:
        raise HTTPException(status_code=400, detail="Collection name cannot contain '$' character")
    
    if len(collection_name) > 120:
        raise HTTPException(status_code=400, detail="Collection name cannot exceed 120 characters")
    
    try:
        mongo.create_database(db, collection_name.strip())
        return {"message": f"Database '{db}' created successfully with collection '{collection_name.strip()}'"}
    except Exception as e:
        logger.error(f"Failed to create database '{db}' with collection '{collection_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create database")


@app.delete("/db/{db}", summary="Delete a database", tags=["Database Management"])
def delete_database(db: str):
    try:
        mongo.delete_database(db)
        return {"message": f"Database '{db}' deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete database '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete database")


# -------------------- Collection APIs --------------------

@app.get("/db/{db}/col", summary="List collections with pagination and filter", tags=["Collection Management"])
def list_collections(
    db: str,
    search: Optional[str] = Query(None, description="Search collection name contains"),
    sort: Optional[str] = Query("asc", pattern="^(asc|desc)$", description="Sort direction"),
    sort_field: Optional[str] = Query(None, description="(Unused for now) Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of collections per page (max 100)")
):
    try:
        return mongo.list_collections(db, search, sort, page, page_size, sort_field, sort_order)
    except Exception as e:
        logger.error(f"Failed to list collections for DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list collections")


@app.post("/db/{db}/col/{col}", summary="Create a new collection", tags=["Collection Management"])
def create_collection(db: str, col: str):
    try:
        mongo.create_collection(db, col)
        return {"message": f"Collection '{col}' created successfully in DB '{db}'"}
    except Exception as e:
        logger.error(f"Failed to create collection '{col}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create collection")

@app.delete("/db/{db}/col/{col}", summary="Delete a collection", tags=["Collection Management"])
def delete_collection(db: str, col: str):
    try:
        mongo.delete_collection(db, col)
        return {"message": f"Collection '{col}' deleted successfully from DB '{db}'"}
    except Exception as e:
        logger.error(f"Failed to delete collection '{col}' from DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete collection '{col}' from DB '{db}'")


# -------------------- Document APIs --------------------

@app.post("/db/{db}/col/{col}/doc", summary="Create a new document", tags=["Document Management"])
def create_document(db: str, col: str, payload: CreateDocument):
    try:
        # Filter out _id field from payload if present
        filtered_data = {k: v for k, v in payload.data.items() if k != "_id"}
        
        inserted_id = mongo.insert_document(db, col, filtered_data)
        return {"message": f"Document inserted with ID: {inserted_id}"}
    except Exception as e:
        logger.error(f"Failed to insert document into {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to insert document")


@app.post("/db/{db}/col/{col}/doc/query", summary="Query documents", tags=["Document Management"])
def query_documents(
    db: str,
    col: str,
    body: dict = Body(default={}, description="MongoDB filter query as JSON"),
    sort_field: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of documents per page")
):
    try:
        filter = body.get("filter", {})
        return mongo.query_collection(db, col, filter, sort_field, sort_order, page, page_size)
    except ValueError as e:
        logger.error(f"Invalid request format for query: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid request format")
    except Exception as e:
        logger.error(f"Failed to query documents in {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to query documents")


@app.get("/db/{db}/col/{col}/doc/{doc_id}", summary="Get document by ID", tags=["Document Management"])
def get_document(db: str, col: str, doc_id: str):
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


@app.put("/db/{db}/col/{col}/doc/{doc_id}", summary="Update document by ID", tags=["Document Management"])
def update_document(db: str, col: str, doc_id: str, update: DocumentUpdate):
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


@app.delete("/db/{db}/col/{col}/doc/{doc_id}", summary="Delete document by ID", tags=["Document Management"])
def delete_document(db: str, col: str, doc_id: str):
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


@app.get("/db/{db}/col/{col}/export", summary="Export collection", tags=["Data Import/Export"])
def export_collection(db: str, col: str):
    try:
        return {"documents": mongo.export_collection(db, col)}
    except Exception as e:
        logger.error(f"Failed to export collection {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export collection")


@app.post("/db/{db}/col/{col}/import", summary="Import documents from JSON file into a collection", tags=["Data Import/Export"])
def import_documents(
    db: str, 
    col: str, 
    file: UploadFile = File(..., description="JSON file containing documents to import")
):
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

@app.get("/db/{db}/gridfs/buckets", summary="List all GridFS buckets in a database", tags=["GridFS File Storage"])
def list_gridfs_buckets(
    db: str,
    search: Optional[str] = Query(None, description="Search for bucket names containing this string"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of buckets per page")
):
    try:
        return mongo.list_gridfs_buckets(db, search, page, page_size)
    except Exception as e:
        logger.error(f"Failed to list GridFS buckets in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list GridFS buckets")


@app.post("/db/{db}/gridfs/{bucket_name}/upload", summary="Upload a file to a specific GridFS bucket", tags=["GridFS File Storage"])
def upload_file_to_bucket(
    db: str,
    bucket_name: str,
    file: UploadFile = File(...),
    metadata: str = Form(default="{}", description="JSON metadata for the file")
):
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


@app.get("/db/{db}/gridfs/{bucket_name}/files", summary="List files in a specific GridFS bucket", tags=["GridFS File Storage"])
def list_files_in_bucket(
    db: str,
    bucket_name: str,
    search: Optional[str] = Query(None, description="Search for files containing this string in filename"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of files per page")
):
    try:
        return mongo.list_files_in_bucket(db, bucket_name, search, page, page_size)
    except Exception as e:
        logger.error(f"Failed to list GridFS files in bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list files")


@app.get("/db/{db}/gridfs/{bucket_name}/file/{file_id}", summary="Get file metadata from a specific bucket", tags=["GridFS File Storage"])
def get_file_metadata_from_bucket(db: str, bucket_name: str, file_id: str):
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


@app.get("/db/{db}/gridfs/{bucket_name}/file/{file_id}/download", summary="Download file by ID from a specific bucket", tags=["GridFS File Storage"])
def download_file_from_bucket(db: str, bucket_name: str, file_id: str):
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


@app.get("/db/{db}/gridfs/{bucket_name}/filename/{filename}/download", summary="Download latest file by filename from a specific bucket", tags=["GridFS File Storage"])
def download_file_by_name_from_bucket(db: str, bucket_name: str, filename: str):
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


@app.delete("/db/{db}/gridfs/{bucket_name}/file/{file_id}", summary="Delete file by ID from a specific bucket", tags=["GridFS File Storage"])
def delete_file_from_bucket(db: str, bucket_name: str, file_id: str):
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


@app.delete("/db/{db}/gridfs/{bucket_name}/filename/{filename}", summary="Delete all files by filename from a specific bucket", tags=["GridFS File Storage"])
def delete_files_by_name_from_bucket(db: str, bucket_name: str, filename: str):
    try:
        deleted_count = mongo.delete_files_by_name_from_bucket(db, bucket_name, filename)
        if deleted_count == 0:
            raise HTTPException(status_code=404, detail="No files found with that filename")
        return {"message": f"Deleted {deleted_count} files named '{filename}' from bucket '{bucket_name}'"}
    except Exception as e:
        logger.error(f"Failed to delete files named '{filename}' from bucket '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete files")


@app.delete("/db/{db}/gridfs/{bucket_name}", summary="Delete an entire GridFS bucket", tags=["GridFS File Storage"])
def delete_bucket(db: str, bucket_name: str):
    try:
        mongo.delete_bucket(db, bucket_name)
        return {"message": f"Bucket '{bucket_name}' deleted successfully from DB '{db}'"}
    except Exception as e:
        logger.error(f"Failed to delete bucket '{bucket_name}' from DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete bucket")



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