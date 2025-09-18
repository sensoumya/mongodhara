# main.py
from typing import Optional

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from logger import logger
from mongo_service import MongoService
from pydantic import BaseModel, Field

app = FastAPI(
    title="MongoDB Management API",
    version="2.0.0",
    description="Refactored API for MongoDB with compact routes, security, and CRUD support."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mongo = MongoService()

# -------------------- Models --------------------

class DocumentUpdate(BaseModel):
    data: dict = Field(..., description="Fields and values to update in the document")


class ImportPayload(BaseModel):
    documents: list[dict] = Field(..., description="List of documents to import")


class CreateDocument(BaseModel):
    data: dict = Field(..., description="New document to insert")


# -------------------- Database APIs --------------------

@app.get("/db", summary="List databases with pagination and filter")
def list_databases(
    search: Optional[str] = Query(None, description="Search databases whose name contains this string"),
    sort: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
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


@app.post("/db/{db}", summary="Create a new database")
def create_database(db: str):
    try:
        mongo.create_database(db)
        return {"message": f"Database '{db}' created successfully"}
    except Exception as e:
        logger.error(f"Failed to create database '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create database")


@app.delete("/db/{db}", summary="Delete a database")
def delete_database(db: str):
    try:
        mongo.delete_database(db)
        return {"message": f"Database '{db}' deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete database '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete database")


# -------------------- Collection APIs --------------------

@app.get("/db/{db}/col", summary="List collections with pagination and filter")
def list_collections(
    db: str,
    search: Optional[str] = Query(None, description="Search collection name contains"),
    sort: Optional[str] = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
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


@app.post("/db/{db}/col/{col}", summary="Create a new collection")
def create_collection(db: str, col: str):
    try:
        mongo.create_collection(db, col)
        return {"message": f"Collection '{col}' created successfully in DB '{db}'"}
    except Exception as e:
        logger.error(f"Failed to create collection '{col}' in DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create collection")

@app.delete("/db/{db}/col/{col}", summary="Delete a collection")
def delete_collection(db: str, col: str):
    try:
        mongo.delete_collection(db, col)
        return {"message": f"Collection '{col}' deleted successfully from DB '{db}'"}
    except Exception as e:
        logger.error(f"Failed to delete collection '{col}' from DB '{db}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete collection '{col}' from DB '{db}'")


# -------------------- Document APIs --------------------

@app.post("/db/{db}/col/{col}/doc", summary="Create a new document")
def create_document(db: str, col: str, payload: CreateDocument):
    try:
        inserted_id = mongo.insert_document(db, col, payload.data)
        return {"message": f"Document inserted with ID: {inserted_id}"}
    except Exception as e:
        logger.error(f"Failed to insert document into {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to insert document")


@app.post("/db/{db}/col/{col}/doc/query", summary="Query documents")
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


@app.get("/db/{db}/col/{col}/doc/{doc_id}", summary="Get document by ID")
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


@app.put("/db/{db}/col/{col}/doc/{doc_id}", summary="Update document by ID")
def update_document(db: str, col: str, doc_id: str, update: DocumentUpdate):
    try:
        modified = mongo.update_document(db, col, doc_id, update.data)
        if modified == 0:
            raise HTTPException(status_code=404, detail="Document not found or not modified")
        return {"message": f"Document with ID {doc_id} updated successfully"}
    except ValueError as e:
        logger.error(f"Invalid document ID '{doc_id}': {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Failed to update document '{doc_id}' in {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update document")


@app.delete("/db/{db}/col/{col}/doc/{doc_id}", summary="Delete document by ID")
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


@app.get("/db/{db}/col/{col}/export", summary="Export collection")
def export_collection(db: str, col: str):
    try:
        return {"documents": mongo.export_collection(db, col)}
    except Exception as e:
        logger.error(f"Failed to export collection {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export collection")


@app.post("/db/{db}/col/{col}/import", summary="Import documents into a collection")
def import_documents(db: str, col: str, payload: ImportPayload):
    try:
        inserted = mongo.import_documents(db, col, payload.documents)
        return {"message": f"Imported {len(inserted)} documents successfully"}
    except ValueError as e:
        logger.error(f"Validation error during import: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Too many documents to import")
    except Exception as e:
        logger.error(f"Failed to import documents into {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to import documents")
