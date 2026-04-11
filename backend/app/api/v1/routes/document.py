# SPDX-License-Identifier: MIT
import json
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.core.logger import logger
from app.core.validators import (
    validate_collection_name_for_access,
    validate_database_name_for_access,
    validate_database_name_for_write,
)
from app.dependencies.auth import require_delete_db, require_read_db, require_write_db
from app.dependencies.models.responses import (
    DocumentExportResponse,
    DocumentImportResponse,
    DocumentQueryResponse,
    MessageResponse,
)
from app.services.document import document_service as mongo

router = APIRouter()


class DocumentUpdate(BaseModel):
    data: dict = Field(..., description="Fields and values to update in the document")


class CreateDocument(BaseModel):
    data: dict = Field(..., description="New document to insert")



@router.post(
    "/db/{db}/col/{col}/doc",
    summary="Create a new document",
    tags=["Document Management"],
    response_model=MessageResponse,
)
async def create_document(db: str, col: str, payload: CreateDocument, user = Depends(require_write_db("db"))):  # RBAC: Require write permission
    # Validate database name for write operations (document creation is a write operation)
    validate_database_name_for_write(db)

    # Validate collection name for access (document creation in existing collection)
    validate_collection_name_for_access(col)

    try:
        # Filter out _id field from payload if present
        filtered_data = {k: v for k, v in payload.data.items() if k != "_id"}

        inserted_id = await mongo.insert_document(db, col, filtered_data)
        return {"message": f"Document inserted with ID: {inserted_id}"}
    except Exception as e:
        logger.error(f"Failed to insert document into {db}.{col}: {e}", exc_info=True)
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "duplicate" in error_msg.lower() or "e11000" in error_msg:
            raise HTTPException(status_code=409, detail="Document with duplicate key already exists")
        elif "invalid" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Invalid document data provided")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to create document in {db}.{col}")


@router.post(
    "/db/{db}/col/{col}/doc/query",
    summary="Query documents (supports advanced MongoDB operators)",
    tags=["Document Management"],
    description="""
    Query documents in a collection using any valid MongoDB filter operators (e.g., $or, $and, $in, $gt, $lt, etc.).
    Example body:
    {
      "filter": {"$or": [{"age": {"$gt": 30}}, {"status": "active"}]}
    }
    """,
    response_model=DocumentQueryResponse,
)
async def query_documents(
    db: str,
    col: str,
    body: dict = Body(
        default={},
        description="MongoDB filter query as JSON. Supports all MongoDB operators.",
    ),
    sort_field: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: int = Query(1, ge=-1, le=1, description="1=asc, -1=desc"),
    page: int = Query(1, gt=0, description="Page number"),
    page_size: int = Query(10, le=100, description="Number of documents per page"),
    user = Depends(require_read_db("db")),  # RBAC: Require read permission
):
    # Validate database name for access
    validate_database_name_for_access(db)

    # Validate collection name for access
    validate_collection_name_for_access(col)

    try:
        filter = body.get("filter", {})
        # filter is passed as-is to PyMongo, so all advanced operators are supported
        return await mongo.query_collection(
            db, col, filter, sort_field, sort_order, page, page_size
        )
    except ValueError as e:
        logger.error(f"Invalid request format for query: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid request format")
    except Exception as e:
        logger.error(f"Failed to query documents in {db}.{col}: {e}", exc_info=True)
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "invalid" in error_msg.lower() and "filter" in error_msg.lower():
            raise HTTPException(status_code=400, detail="Invalid query filter format")
        elif "timeout" in error_msg.lower():
            raise HTTPException(status_code=408, detail="Query timed out, please try with smaller page size")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to query documents in {db}.{col}")


@router.get(
    "/db/{db}/col/{col}/doc/{doc_id}",
    summary="Get document by ID",
    tags=["Document Management"],
    response_model=DocumentQueryResponse,
)
async def get_document(db: str, col: str, doc_id: str, user = Depends(require_read_db("db"))):  # RBAC: Require read permission
    # Validate database name for access
    validate_database_name_for_access(db)

    # Validate collection name for access
    validate_collection_name_for_access(col)

    try:
        result = await mongo.get_document(db, col, doc_id)
        if result["total"] == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return result
    except HTTPException:
        # Re-raise HTTP exceptions (like 404 from service)
        raise
    except ValueError as e:
        logger.error(f"Invalid document ID '{doc_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(
            f"Failed to retrieve document '{doc_id}' from {db}.{col}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve document")


@router.put(
    "/db/{db}/col/{col}/doc/{doc_id}",
    summary="Update document by ID",
    tags=["Document Management"],
    response_model=MessageResponse,
)
async def update_document(db: str, col: str, doc_id: str, update: DocumentUpdate, user = Depends(require_write_db("db"))):  # RBAC: Require write permission
    # Validate database name for write operations
    validate_database_name_for_write(db)

    # Validate collection name for access
    validate_collection_name_for_access(col)

    try:
        # Filter out _id field from update data if present
        filtered_data = {k: v for k, v in update.data.items() if k != "_id"}
        logger.debug(f"Updating document '{doc_id}' in {db}.{col} with data: {update.data}")

        modified = await mongo.update_document(db, col, doc_id, filtered_data)
        if modified == 0:
            raise HTTPException(
                status_code=404, detail="Document not found or not modified"
            )
        return {"message": f"Document with ID {doc_id} updated successfully"}
    except ValueError as e:
        logger.error(f"Invalid document ID '{doc_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(
            f"Failed to update document '{doc_id}' in {db}.{col}: {e}", exc_info=True
        )
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=f"Document with id '{doc_id}' not found")
        elif "invalid" in error_msg.lower() and "id" in error_msg.lower():
            raise HTTPException(status_code=400, detail=f"Invalid document ID format: {doc_id}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update document '{doc_id}'")


@router.delete(
    "/db/{db}/col/{col}/doc/{doc_id}",
    summary="Delete document by ID",
    tags=["Document Management"],
    response_model=MessageResponse,
)
async def delete_document(db: str, col: str, doc_id: str, user = Depends(require_delete_db("db"))):  # RBAC: Require delete permission
    # Validate database name for write operations
    validate_database_name_for_write(db)

    # Validate collection name for access
    validate_collection_name_for_access(col)

    try:
        deleted = await mongo.delete_document(db, col, doc_id)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"message": f"Document with ID {doc_id} deleted successfully"}
    except ValueError as e:
        logger.error(f"Invalid document ID '{doc_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(
            f"Failed to delete document '{doc_id}' from {db}.{col}: {e}", exc_info=True
        )
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "404" in error_msg or "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=f"Document with id '{doc_id}' not found")
        elif "invalid" in error_msg.lower() and "id" in error_msg.lower():
            raise HTTPException(status_code=400, detail=f"Invalid document ID format: {doc_id}")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete document '{doc_id}'")


@router.get(
    "/db/{db}/col/{col}/export",
    summary="Export collection",
    tags=["Data Import/Export"],
    response_model=DocumentExportResponse,
)
async def export_collection(db: str, col: str, user = Depends(require_read_db("db"))):  # RBAC: Require read permission
    # Validate database name for access
    validate_database_name_for_access(db)

    # Validate collection name for access
    validate_collection_name_for_access(col)

    try:
        return {"documents": await mongo.export_collection(db, col)}
    except Exception as e:
        logger.error(f"Failed to export collection {db}.{col}: {e}", exc_info=True)
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "timeout" in error_msg.lower():
            raise HTTPException(status_code=408, detail="Export timed out, collection may be too large")
        elif "memory" in error_msg.lower():
            raise HTTPException(status_code=413, detail="Collection too large to export")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to export collection {db}.{col}")


@router.post(
    "/db/{db}/col/{col}/import",
    summary="Import documents from JSON file into a collection",
    tags=["Data Import/Export"],
    response_model=DocumentImportResponse,
)
async def import_documents(
    db: str,
    col: str,
    file: UploadFile = File(
        ..., description="JSON file containing documents to import"
    ),
    user=Depends(require_write_db("db")),  # RBAC: Require write permission
):
    # Validate database name for write operations
    validate_database_name_for_write(db)

    # Validate collection name for access
    validate_collection_name_for_access(col)

    try:
        # Validate file type
        if not file.filename or not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")

        # Read and parse the JSON file
        file_content = file.file.read()
        try:
            json_data = json.loads(file_content.decode("utf-8"))
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

        # Log the structure for debugging
        logger.debug(f"Received JSON type: {type(json_data)}, keys: {json_data.keys() if isinstance(json_data, dict) else 'N/A'}")

        # Handle different JSON structures - support both export format and direct array
        if isinstance(json_data, list):
            # Direct array of documents
            documents = json_data
        elif isinstance(json_data, dict) and "documents" in json_data:
            # Export format with 'documents' key
            documents = json_data["documents"]
        else:
            raise HTTPException(
                status_code=400,
                detail="JSON must be either an array of documents, a single document object, or contain a 'documents' key",
            )

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

        inserted = await mongo.import_documents(db, col, filtered_documents)
        return {
            "message": f"Imported {len(inserted)} documents successfully",
            "imported_count": len(inserted),
        }
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during import: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to import documents into {db}.{col}: {e}", exc_info=True)
        # Provide more user-friendly error messages
        error_msg = str(e)
        if "duplicate" in error_msg.lower() or "e11000" in error_msg:
            raise HTTPException(status_code=409, detail="Some documents contain duplicate keys")
        elif "timeout" in error_msg.lower():
            raise HTTPException(status_code=408, detail="Import timed out, please reduce file size")
        elif "memory" in error_msg.lower():
            raise HTTPException(status_code=413, detail="Import file too large")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to import documents into {db}.{col}")