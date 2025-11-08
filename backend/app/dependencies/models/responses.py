from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, RootModel


# Database Response Models
class DatabaseInfo(BaseModel):
    name: str
    opaque_id: Optional[str] = None


class DatabaseListItem(BaseModel):
    name: str
    opaque_id: Optional[str] = None


class DatabaseListResponse(BaseModel):
    databases: List[DatabaseListItem]
    total: int
    page: int
    page_size: int
    filtered_by_permissions: bool


class DatabaseStatsResponse(BaseModel):
    database: DatabaseInfo
    stats: Dict[str, Any]


# Collection Response Models
class CollectionInfo(BaseModel):
    name: str
    opaque_id: Optional[str] = None


class CollectionListItem(BaseModel):
    name: str
    opaque_id: Optional[str] = None


class CollectionListResponse(BaseModel):
    database: DatabaseInfo
    collections: List[CollectionListItem]
    total: int
    page: int
    page_size: int


class CollectionStats(BaseModel):
    documents_count: int
    total_size: int
    avg_document_size: float
    storage_size: int
    indexes_count: int
    index_size: int


class CollectionStatsResponse(BaseModel):
    database: DatabaseInfo
    collection: CollectionInfo
    stats: CollectionStats


# Document Response Models
class DocumentQueryResponse(BaseModel):
    database: DatabaseInfo
    collection: CollectionInfo
    data: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class DocumentExportResponse(BaseModel):
    documents: List[Dict[str, Any]]


class DocumentImportResponse(BaseModel):
    message: str
    imported_count: int


# Index Response Models
class IndexInfo(BaseModel):
    name: str
    key: Dict[str, Any]
    unique: bool = False
    sparse: bool = False
    background: bool = False
    partial_filter: Optional[Dict[str, Any]] = None
    expire_after: Optional[int] = None
    text_weights: Optional[Dict[str, Any]] = None
    text_default_language: Optional[str] = None
    version: Optional[int] = None
    size: Optional[int] = None
    opaque_id: Optional[str] = None


class IndexListResponse(BaseModel):
    database: DatabaseInfo
    collection: CollectionInfo
    indexes: List[IndexInfo]
    total: int


class IndexCreateResponse(BaseModel):
    message: str
    index_name: str
    keys: Dict[str, Any]
    options: Dict[str, Any]


class IndexDropResponse(BaseModel):
    message: str
    index_name: str


class IndexInfoResponse(BaseModel):
    database: DatabaseInfo
    collection: CollectionInfo
    index_name: str
    index_info: IndexInfo


class TextIndexCreateResponse(BaseModel):
    message: str
    index_name: str
    fields: List[str]
    language: str


class IndexStatsItem(BaseModel):
    name: str
    key: Dict[str, Any]
    accesses: int
    since: datetime


class IndexStatsResponse(BaseModel):
    database: DatabaseInfo
    collection: CollectionInfo
    index_stats: List[IndexStatsItem]


# GridFS Response Models
class BucketInfo(BaseModel):
    bucket_name: str
    opaque_id: Optional[str] = None


class GridFSBucketListItem(BaseModel):
    bucket_name: str
    opaque_id: Optional[str] = None


class GridFSBucketListResponse(BaseModel):
    database: DatabaseInfo
    buckets: List[GridFSBucketListItem]
    total: int
    page: int
    page_size: int


class GridFSBucketStats(BaseModel):
    files_count: int
    chunks_count: int
    total_data_size: int
    total_storage_size: int
    avg_chunk_size: float
    indexes_count: int
    index_size: int


class GridFSBucketStatsResponse(BaseModel):
    database: DatabaseInfo
    bucket: BucketInfo
    stats: GridFSBucketStats


class GridFSUploadResponse(BaseModel):
    message: str
    file_id: str
    bucket_name: str


class GridFSFileListResponse(BaseModel):
    database: DatabaseInfo
    bucket: BucketInfo
    data: List[Dict[str, Any]]
    total: int
    page: int
    page_size: int


class GridFSFileMetadataResponse(BaseModel):
    _id: str
    filename: Optional[str] = None
    contentType: Optional[str] = None
    length: Optional[int] = None
    uploadDate: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class GridFSDeleteResponse(BaseModel):
    message: str


class DatabaseStatsListResponse(RootModel[List[DatabaseStatsResponse]]):
    pass


# Generic Response Models
class MessageResponse(BaseModel):
    message: str