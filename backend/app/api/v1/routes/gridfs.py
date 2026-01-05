import json
from typing import Optional

from bson import ObjectId
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from app.core.config import GRIDFS_CHUNK_SIZE, GRIDFS_MAX_FILE_SIZE
from app.core.logger import logger
from app.core.validators import (
    validate_collection_name_for_access,
    validate_database_name_for_access,
    validate_database_name_for_write,
)
from app.dependencies.auth import (
    require_admin_db,
    require_delete_db,
    require_read_db,
    require_write_db,
)
from app.dependencies.models.responses import (
    GridFSBucketListResponse,
    GridFSBucketStatsResponse,
    GridFSDeleteResponse,
    GridFSFileListResponse,
    GridFSFileMetadataResponse,
    GridFSUploadResponse,
    MessageResponse,
)
from app.services.gridfs import gridfs_service as mongo

router = APIRouter()

@router.get(
    "/db/{db}/gridfs",
    summary="List all GridFS buckets in a database",
    tags=["GridFS File Storage"],
    response_model=GridFSBucketListResponse,
)
async def list_gridfs_buckets(
    db: str,
    search: Optional[str] = Query(
        None, description="Search for bucket names containing this string"
    ),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of buckets per page"),
    user = Depends(require_read_db("db")),  # RBAC: Require read permission
):
    # Validate database name for access
    validate_database_name_for_access(db)

    try:
        return await mongo.list_gridfs_buckets(db, search, page, page_size)
    except Exception as e:
        logger.error(f"Failed to list GridFS buckets in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list GridFS buckets")


@router.get(
    "/db/{db}/gridfs/{bucket_name}/stats",
    summary="Get detailed statistics for a specific GridFS bucket",
    tags=["GridFS File Storage"],
    response_model=GridFSBucketStatsResponse,
)
async def get_gridfs_bucket_stats(db: str, bucket_name: str, user = Depends(require_read_db("db"))):  # RBAC: Require read permission
    # Validate database name for access
    validate_database_name_for_access(db)

    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)

    try:
        return await mongo.get_gridfs_bucket_stats(db, bucket_name)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get GridFS bucket stats for '{bucket_name}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get GridFS bucket stats for '{bucket_name}'")


@router.post(
    "/db/{db}/gridfs/upload",
    summary=f"Upload a file to a specific GridFS bucket (optimized for large files up to {GRIDFS_MAX_FILE_SIZE // (1024*1024)}MB)",
    tags=["GridFS File Storage"],
    response_model=GridFSUploadResponse,
)
async def upload_file_to_bucket(
    db: str,
    bucket_name: str = Form(..., description="Name of the GridFS bucket"),
    file: UploadFile = File(...),
    metadata: str = Form(default="{}", description="JSON metadata for the file"),
    user = Depends(require_write_db("db")),  # RBAC: Require write permission
):
    """
    Upload a file to GridFS bucket with streaming optimization for large files.
    Memory efficient - processes file in chunks without loading entire file into RAM.
    Supports files up to {GRIDFS_MAX_FILE_SIZE // (1024*1024)}MB with configurable chunk size.
    """
    # Validate database name for write operations
    validate_database_name_for_write(db)

    # Validate bucket name for access (use collection name validation as buckets are collections)
    validate_collection_name_for_access(bucket_name)

    # Validate file size
    if hasattr(file, 'size') and file.size > GRIDFS_MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {GRIDFS_MAX_FILE_SIZE // (1024*1024)}MB"
        )

    try:
        metadata_dict = json.loads(metadata) if metadata != "{}" else {}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON metadata")

    try:
        # Log the upload start
        logger.info(
            f"Starting streaming upload of '{file.filename}' to GridFS bucket '{bucket_name}' in DB '{db}'"
        )

        # Use streaming upload instead of loading entire file into memory
        file_id = await stream_upload_to_gridfs(
            db=db,
            bucket_name=bucket_name,
            file_stream=file.file,
            filename=file.filename,
            content_type=file.content_type,
            metadata=metadata_dict,
        )

        logger.info(
            f"Successfully uploaded '{file.filename}' to bucket '{bucket_name}' with ID: {file_id}"
        )

        return {
            "message": f"File '{file.filename}' uploaded successfully to bucket '{bucket_name}'",
            "file_id": file_id,
            "bucket_name": bucket_name,
        }
    except Exception as e:
        logger.error(
            f"Failed to upload file to GridFS bucket '{bucket_name}' in DB '{db}': {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


async def stream_upload_to_gridfs(
    db: str,
    bucket_name: str,
    file_stream,
    filename: str,
    content_type: str = None,
    metadata: dict = None,
) -> str:
    """
    Stream upload file to GridFS without loading entire file into memory.
    Uses configurable chunk size for optimal balance of memory usage and performance.
    """
    import asyncio

    # Use configurable chunk size
    CHUNK_SIZE = GRIDFS_CHUNK_SIZE
    
    # Get GridFS handle
    gridfs_db = mongo.client[db]
    fs = AsyncIOMotorGridFSBucket(gridfs_db, bucket_name)
    
    # Create GridFS file for streaming write
    stream_metadata = metadata or {}
    stream = fs.open_upload_stream(
        filename=filename,
        metadata=stream_metadata,
    )

    try:
        total_written = 0

        # Stream file in chunks to avoid memory issues
        while True:
            # Read chunk asynchronously to avoid blocking
            chunk = await asyncio.get_event_loop().run_in_executor(
                None, file_stream.read, CHUNK_SIZE
            )

            if not chunk:
                break

            # Write chunk to GridFS
            await stream.write(chunk)

            total_written += len(chunk)

            # Log progress for large files (every 5MB)
            if total_written % (5 * 1024 * 1024) == 0:
                logger.debug(f"Upload progress: {total_written // (1024 * 1024)}MB written")

        # Close and finalize the GridFS file
        await stream.close()

        # Update the files collection to set contentType at root level
        if content_type:
            files_collection = gridfs_db[f"{bucket_name}.files"]
            await files_collection.update_one(
                {"_id": stream._id},
                {"$set": {"contentType": content_type}}
            )

        logger.info(f"Streaming upload completed. Total bytes written: {total_written}")
        return str(stream._id)
        
    except Exception as e:
        # Cleanup on error - delete partially uploaded file
        try:
            if hasattr(stream, '_id') and stream._id:
                await fs.delete(stream._id)
        except Exception:
            pass  # Best effort cleanup
        raise e


# Removed GET listing endpoint in favor of POST JSON filter at /files/query


@router.post(
    "/db/{db}/gridfs/{bucket_name}/files/query",
    summary="Query GridFS files (supports Mongo-style JSON filter)",
    tags=["GridFS File Storage"],
    response_model=GridFSFileListResponse,
)
async def query_files_in_bucket(
    db: str,
    bucket_name: str,
    body: dict = Body(
        default={},
        description="MongoDB filter query as JSON for GridFS .files collection",
    ),
    sort_field: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of files per page"),
    user = Depends(require_read_db("db")),
):
    validate_database_name_for_access(db)
    validate_collection_name_for_access(bucket_name)

    try:
        filter = body.get("filter", {})
        return await mongo.query_files_in_bucket(
            db, bucket_name, filter, sort_field, sort_order, page, page_size
        )
    except ValueError as e:
        logger.error(f"Invalid request format for GridFS query: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid request format")
    except Exception as e:
        logger.error(
            "Failed to query GridFS files in bucket '%s' in DB '%s': %s",
            bucket_name,
            db,
            str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to query files in {bucket_name}")


@router.get(
    "/db/{db}/gridfs/{bucket_name}/file/{file_id}",
    summary="Get file metadata from a specific bucket",
    tags=["GridFS File Storage"],
    response_model=GridFSFileMetadataResponse,
)
async def get_file_metadata_from_bucket(db: str, bucket_name: str, file_id: str, user = Depends(require_read_db("db"))):  # RBAC: Require read permission
    # Validate database name for access
    validate_database_name_for_access(db)

    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)

    try:
        metadata = await mongo.get_file_metadata_from_bucket(db, bucket_name, file_id)
        if not metadata:
            raise HTTPException(status_code=404, detail="File not found")
        return metadata
    except ValueError as e:
        logger.error(f"Invalid file ID '{file_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid file ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get file metadata for '{file_id}' in bucket '{bucket_name}' in DB '{db}': {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to get file metadata")


@router.get(
    "/db/{db}/gridfs/{bucket_name}/file/{file_id}/download",
    summary="Download file by ID from a specific bucket (streaming optimized)",
    tags=["GridFS File Storage"],
)
async def download_file_from_bucket(db: str, bucket_name: str, file_id: str, user = Depends(require_read_db("db"))):  # RBAC: Require read permission
    # Validate database name for access
    validate_database_name_for_access(db)

    # Validate bucket name for access
    validate_collection_name_for_access(bucket_name)

    try:
        # First get file metadata to check if file exists
        file_metadata = await mongo.get_file_metadata_from_bucket(db, bucket_name, file_id)
        if not file_metadata:
            raise HTTPException(status_code=404, detail="File not found")

        # For large files, use streaming download to avoid memory issues
        async def generate_file_stream():
            try:
                gridfs_db = mongo.client[db]
                fs = AsyncIOMotorGridFSBucket(gridfs_db, bucket_name)
                
                # Get GridFS file handle - await it for Motor
                stream = await fs.open_download_stream(ObjectId(file_id))
                
                # Stream file in configurable chunks for better performance
                chunk_size = GRIDFS_CHUNK_SIZE
                while True:
                    # Read chunk
                    chunk = await stream.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
            except Exception as e:
                logger.error(f"Error streaming file {file_id}: {e}")
                raise

        content_type = file_metadata.get("contentType") or "application/octet-stream"
        filename = file_metadata.get("filename") or "download"
        
        return StreamingResponse(
            generate_file_stream(),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "private, max-age=3600",
                "ETag": f'"{file_id}"',
            }
        )

    except ValueError as e:
        logger.error(f"Invalid file ID '{file_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid file ID")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to download file '{file_id}' from bucket '{bucket_name}' in DB '{db}': {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to download file")


@router.delete(
    "/db/{db}/gridfs/{bucket_name}/file/{file_id}",
    summary="Delete file by ID from a specific bucket",
    tags=["GridFS File Storage"],
    response_model=GridFSDeleteResponse,
)
async def delete_file_from_bucket(db: str, bucket_name: str, file_id: str, user = Depends(require_delete_db("db"))):  # RBAC: Require delete permission
    # Validate database name for write operations
    validate_database_name_for_write(db)

    # Validate bucket name for access (use collection name validation as buckets are collections)
    validate_collection_name_for_access(bucket_name)

    try:
        deleted = await mongo.delete_file_from_bucket(db, bucket_name, file_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"File with id '{file_id}' doesn't exist in bucket '{bucket_name}'")
        return {
            "message": f"File with ID {file_id} deleted successfully from bucket '{bucket_name}'"
        }
    except ValueError as e:
        error_msg = str(e)
        if "invalid" in error_msg.lower() and "id" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Invalid file ID")
        elif "invalid" in error_msg.lower() and "bucket" in error_msg.lower():
            raise HTTPException(status_code=400, detail=f"Invalid GridFS bucket '{bucket_name}'")
        elif "error checking" in error_msg.lower():
            raise HTTPException(status_code=500, detail=f"Error accessing bucket '{bucket_name}'")
        else:
            raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        logger.error(
            f"Failed to delete file '{file_id}' from bucket '{bucket_name}' in DB '{db}': {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete file '{file_id}' from bucket '{bucket_name}'")


@router.delete(
    "/db/{db}/gridfs/{bucket_name}",
    summary="Delete an entire GridFS bucket",
    tags=["GridFS File Storage"],
    response_model=GridFSDeleteResponse,
)
async def delete_bucket(db: str, bucket_name: str, user = Depends(require_admin_db("db"))):  # RBAC: Require admin permission
    # Validate database name for write operations
    validate_database_name_for_write(db)

    # Validate bucket name for access (use collection name validation as buckets are collections)
    validate_collection_name_for_access(bucket_name)

    try:
        await mongo.delete_bucket(db, bucket_name)
        return {
            "message": f"Bucket '{bucket_name}' deleted successfully from DB '{db}'"
        }
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found in database '{db}'")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"Failed to delete bucket '{bucket_name}' from DB '{db}': {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete bucket '{bucket_name}' from database '{db}'")

