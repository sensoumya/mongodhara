from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.config import ENABLE_OPAQUE_IDS
from app.core.logger import logger
from app.core.validators import (
    validate_collection_name_for_access,
    validate_database_name_for_access,
    validate_database_name_for_write,
)
from app.dependencies.auth import require_read_db, require_write_db
from app.dependencies.models.responses import (
    IndexCreateResponse,
    IndexDropResponse,
    IndexInfoResponse,
    IndexStatsResponse,
    TextIndexCreateResponse,
)
from app.services.index import index_service as mongo
from app.services.opaque_id_service import encode_opaque_id

router = APIRouter()


class IndexSpecModel(BaseModel):
    """Model for index specification"""
    keys: Dict[str, int]  # e.g., {"name": 1, "age": -1}
    options: Optional[Dict] = None  # e.g., {"unique": True, "sparse": True}


@router.get(
    "/db/{db}/col/{col}/indexes",
    summary="List all indexes for a collection",
    tags=["Index Management"],
    # response_model=IndexListResponse,
)
async def list_indexes(db: str, col: str, _=Depends(require_read_db("db"))):
    """List all indexes for a specific collection"""
    validate_database_name_for_access(db)
    validate_collection_name_for_access(col)

    try:
        indexes = await mongo.list_indexes(db, col)
        return {
            "database": {
                "name": db,
                "opaque_id": encode_opaque_id(db) if ENABLE_OPAQUE_IDS else None
            },
            "collection": {
                "name": col,
                "opaque_id": encode_opaque_id(col) if ENABLE_OPAQUE_IDS else None
            },
            "indexes": indexes,
            "total": len(indexes)
        }
        logger.warning(f"Invalid opaque ID in index list request for {db}.{col}: {e}")
        raise HTTPException(status_code=400, detail="Invalid opaque ID")
    except Exception as e:
        logger.error(f"Failed to list indexes for {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list indexes")


@router.post(
    "/db/{db}/col/{col}/indexes",
    summary="Create an index on a collection",
    tags=["Index Management"],
    response_model=IndexCreateResponse,
)
async def create_index(db: str, col: str, index_spec: IndexSpecModel, _=Depends(require_write_db("db"))):
    """Create an index on a collection"""
    validate_database_name_for_write(db)
    validate_collection_name_for_access(col)

    try:
        index_name = await mongo.create_index(db, col, index_spec.keys, index_spec.options)
        return {
            "message": f"Index created successfully on {db}.{col}",
            "index_name": index_name,
            "keys": index_spec.keys,
            "options": index_spec.options or {}
        }
        logger.warning(f"Invalid opaque ID in index create request for {db}.{col}: {e}")
        raise HTTPException(status_code=400, detail="Invalid opaque ID")
    except Exception as e:
        logger.error(f"Failed to create index on {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create index")


@router.delete(
    "/db/{db}/col/{col}/indexes/{index_name}",
    summary="Drop an index from a collection", 
    tags=["Index Management"],
    response_model=IndexDropResponse,
)
async def drop_index(db: str, col: str, index_name: str, _=Depends(require_write_db("db"))):
    """Drop a specific index from a collection"""
    validate_database_name_for_write(db)
    validate_collection_name_for_access(col)

    # Prevent dropping the default _id index
    if index_name == "_id_":
        raise HTTPException(
            status_code=400, 
            detail="Cannot drop the default _id index"
        )

    try:
        await mongo.drop_index(db, col, index_name)
        return {
            "message": f"Index '{index_name}' dropped successfully from {db}.{col}",
            "index_name": index_name
        }
        logger.warning(f"Invalid opaque ID in index drop request for {db}.{col}: {e}")
        raise HTTPException(status_code=400, detail="Invalid opaque ID")
    except Exception as e:
        logger.error(f"Failed to drop index '{index_name}' from {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to drop index")


@router.get(
    "/db/{db}/col/{col}/indexes/{index_name}",
    summary="Get details of a specific index",
    tags=["Index Management"],
    response_model=IndexInfoResponse,
)
async def get_index_info(db: str, col: str, index_name: str, _=Depends(require_read_db("db"))):
    """Get detailed information about a specific index"""
    validate_database_name_for_access(db)
    validate_collection_name_for_access(col)

    try:
        index_info = await mongo.get_index_info(db, col, index_name)
        if not index_info:
            raise HTTPException(status_code=404, detail=f"Index '{index_name}' not found")
        
        return {
            "database": {
                "name": db,
                "opaque_id": encode_opaque_id(db) if ENABLE_OPAQUE_IDS else None
            },
            "collection": {
                "name": col,
                "opaque_id": encode_opaque_id(col) if ENABLE_OPAQUE_IDS else None
            },
            "index_name": index_name,
            "index_info": index_info
        }
    except HTTPException:
        raise
        logger.warning(f"Invalid opaque ID in index info request for {db}.{col}: {e}")
        raise HTTPException(status_code=400, detail="Invalid opaque ID")
    except Exception as e:
        logger.error(f"Failed to get index info for '{index_name}' in {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get index information")


@router.post(
    "/db/{db}/col/{col}/indexes/text",
    summary="Create a text index for full-text search",
    tags=["Index Management"],
    response_model=TextIndexCreateResponse,
)
async def create_text_index(
    db: str, 
    col: str,
    fields: List[str] = Query(..., description="Fields to include in text index"),
    language: str = Query("english", description="Text index language"),
    name: Optional[str] = Query(None, description="Custom index name"),
    _=Depends(require_write_db("db"))
):
    """Create a text index for full-text search capabilities"""
    validate_database_name_for_write(db)
    validate_collection_name_for_access(col)

    try:
        # Build text index specification
        text_spec = {field: "text" for field in fields}
        options = {"default_language": language}
        if name:
            options["name"] = name

        result = await mongo.create_text_index(db, col, fields, name, language)
        return {
            "message": f"Text index created successfully on {db}.{col}",
            "index_name": result["index_name"],
            "fields": fields,
            "language": language
        }
        logger.warning(f"Invalid opaque ID in text index create request for {db}.{col}: {e}")
        raise HTTPException(status_code=400, detail="Invalid opaque ID")
    except Exception as e:
        logger.error(f"Failed to create text index on {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create text index")


@router.get(
    "/db/{db}/col/{col}/indexes/stats",
    summary="Get index usage statistics",
    tags=["Index Management"],
    response_model=IndexStatsResponse,
)
async def get_index_stats(db: str, col: str, _=Depends(require_read_db("db"))):
    """Get index usage statistics for a collection"""
    validate_database_name_for_access(db)
    validate_collection_name_for_access(col)

    try:
        stats = await mongo.get_index_stats(db, col)
        return {
            "database": {
                "name": db,
                "opaque_id": encode_opaque_id(db) if ENABLE_OPAQUE_IDS else None
            },
            "collection": {
                "name": col,
                "opaque_id": encode_opaque_id(col) if ENABLE_OPAQUE_IDS else None
            },
            "index_stats": stats
        }
        logger.warning(f"Invalid opaque ID in index stats request for {db}.{col}: {e}")
        raise HTTPException(status_code=400, detail="Invalid opaque ID")
    except Exception as e:
        logger.error(f"Failed to get index stats for {db}.{col}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get index statistics")