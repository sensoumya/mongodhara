from bson import ObjectId
from bson.errors import InvalidId

from app.core.config import ENABLE_OPAQUE_IDS
from app.core.logger import logger
from app.services.base import BaseMongoService
from app.services.opaque_id_service import encode_opaque_id


class DocumentService(BaseMongoService):
    """Service for document operations."""

    async def query_collection(
        self,
        db_name,
        col_name,
        filter=None,
        sort_field=None,
        sort_order=1,
        page=1,
        page_size=10,
    ):
        
        if page_size > 100:
            raise ValueError("Page size exceeds max limit of 100")

        logger.debug(
            f"DocumentService.query_collection: using db_name='{db_name}', col_name='{col_name}' | filter={filter} | page={page} | size={page_size}"
        )

        collection = self.client[db_name][col_name]
        query_filter = filter or {}

        # Convert _id from string to ObjectId if present
        if "_id" in query_filter and isinstance(query_filter["_id"], str):
            try:
                query_filter["_id"] = ObjectId(query_filter["_id"])
            except Exception:
                raise ValueError("Invalid ObjectId format for _id")

        # Use aggregation pipeline for better performance
        pipeline = [{"$match": query_filter}]
        
        if sort_field:
            pipeline.append({"$sort": {sort_field: sort_order}})
        
        # Use $facet to get count and data in single query
        pipeline.append({
            "$facet": {
                "total": [{"$count": "count"}],
                "data": [
                    {"$skip": (page - 1) * page_size},
                    {"$limit": page_size}
                ]
            }
        })

        result = await collection.aggregate(pipeline).to_list()
        
        if result:
            total = result[0]["total"][0]["count"] if result[0]["total"] else 0
            data = result[0]["data"]
            
            # Convert ObjectId to string
            for doc in data:
                doc["_id"] = str(doc["_id"])
        else:
            total = 0
            data = []

        response = {
            "database": {
                "name": db_name,
                "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
            },
            "collection": {
                "name": col_name,
                "opaque_id": encode_opaque_id(col_name) if ENABLE_OPAQUE_IDS else None
            },
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        return response

    async def insert_document(self, db_name, col_name, document: dict):
        logger.debug(f"Inserting document into {db_name}.{col_name}")
        result = await self.client[db_name][col_name].insert_one(document)
        return str(result.inserted_id)

    async def get_document(self, db_name, col_name, doc_id):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        doc = await self.client[db_name][col_name].find_one(
            {"_id": _id},
            session=None
        )

        data = []
        if doc:
            doc["_id"] = str(doc["_id"])
            data = [doc]

        return {
            "database": {
                "name": db_name,
                "opaque_id": encode_opaque_id(db_name) if ENABLE_OPAQUE_IDS else None
            },
            "collection": {
                "name": col_name,
                "opaque_id": encode_opaque_id(col_name) if ENABLE_OPAQUE_IDS else None
            },
            "data": data,
            "total": len(data),
            "page": 1,
            "page_size": 1
        }

    async def update_document(self, db_name, col_name, doc_id, update_data: dict):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        result = await self.client[db_name][col_name].replace_one(
            {"_id": _id}, 
            update_data
        )
        return result.modified_count

    async def delete_document(self, db_name, col_name, doc_id):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        result = await self.client[db_name][col_name].delete_one({"_id": _id})
        return result.deleted_count

    async def export_collection(self, db_name, col_name):
        logger.info(f"Exporting collection: {db_name}.{col_name}")
        
        # Use aggregation with projection to convert _id on MongoDB side
        pipeline = [
            {"$project": {
                "_id": {"$toString": "$_id"},
                "doc": "$$ROOT"
            }},
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$project": {"doc": 0}}
        ]
        
        # Stream results for memory efficiency
        exported = []
        async for doc in self.client[db_name][col_name].aggregate(pipeline, allowDiskUse=True):
            doc["_id"] = str(doc["_id"])
            exported.append(doc)
        
        return exported

    async def import_documents(self, db_name, col_name, documents: list):
        if len(documents) > 500:
            raise ValueError("Too many documents to import (max 500)")

        # Remove _id in list comprehension (more efficient)
        cleaned_documents = [
            {k: v for k, v in doc.items() if k != "_id"}
            for doc in documents
        ]

        result = await self.client[db_name][col_name].insert_many(
            cleaned_documents,
            ordered=False  # Faster bulk insert
        )
        return [str(_id) for _id in result.inserted_ids]


# Create a global instance
document_service = DocumentService()