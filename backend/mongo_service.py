from bson import ObjectId
from bson.errors import InvalidId
from config import MONGO_URI
from logger import logger
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid


class MongoService:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)

    # --------- Database Operations ---------

    def list_databases(self, search=None, sort="asc", page=1, page_size=10, sort_field=None, sort_order=1):
        logger.debug("Listing databases with filter and pagination")
        dbs = self.client.list_database_names()

        if search:
            dbs = [db for db in dbs if search.lower() in db.lower()]

        dbs.sort(reverse=(sort == "desc"))
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "databases": dbs[start:end],
            "total": len(dbs),
            "page": page,
            "page_size": page_size
        }

    def create_database(self, db_name):
        logger.info(f"Creating database '{db_name}'")
        dummy_col = self.client[db_name]["_init"]
        dummy_col.insert_one({"init": True})

    def delete_database(self, db_name):
        logger.warning(f"Dropping database: {db_name}")
        self.client.drop_database(db_name)
        return True

    # --------- Collection Operations ---------

    def list_collections(self, db_name, search=None, sort="asc", page=1, page_size=10, sort_field=None, sort_order=1):
        try:
            logger.debug(f"Listing collections in DB: {db_name} with filter and pagination")
            collections = self.client[db_name].list_collection_names()

            # Filter out both MongoDB system collections and your custom _init collection
            collections = [c for c in collections if not c.startswith('system.') and c != '_init']

            if search:
                collections = [c for c in collections if search.lower() in c.lower()]

            collections.sort(reverse=(sort == "desc"))
            total = len(collections)
            start = (page - 1) * page_size
            end = start + page_size
            
            return {
                "collections": collections[start:end],
                "total": total,
                "page": page,
                "page_size": page_size
            }
        except Exception as e:
            logger.error(f"Error listing collections for DB '{db_name}': {e}", exc_info=True)
            raise

    def create_collection(self, db_name, col_name):
        logger.info(f"Creating collection '{col_name}' in DB '{db_name}'")
        db = self.client[db_name]
        if col_name in db.list_collection_names():
            raise CollectionInvalid(f"Collection '{col_name}' already exists in '{db_name}'")
        db.create_collection(col_name)

    # --------- Document Operations ---------

    def insert_document(self, db_name, col_name, document: dict):
        logger.debug(f"Inserting document into {db_name}.{col_name}")
        result = self.client[db_name][col_name].insert_one(document)
        return str(result.inserted_id)

    def query_collection(self, db_name, col_name, filter=None, sort_field=None, sort_order=1, page=1, page_size=10):
        if page_size > 100:
            raise ValueError("Page size exceeds max limit of 100")

        logger.debug(f"Querying {db_name}.{col_name} | filter={filter} | page={page} | size={page_size}")

        db = self.client[db_name]
        collection = db[col_name]
        query_filter = filter or {}

        # 👇 Convert _id from string to ObjectId if present
        if "_id" in query_filter and isinstance(query_filter["_id"], str):
            try:
                query_filter["_id"] = ObjectId(query_filter["_id"])
            except Exception:
                raise ValueError("Invalid ObjectId format for _id")

        total = collection.count_documents(query_filter)
        cursor = collection.find(query_filter)

        if sort_field:
            cursor = cursor.sort(sort_field, sort_order)

        cursor = cursor.skip((page - 1) * page_size).limit(page_size)

        data = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            data.append(doc)

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size
        }

    def get_document(self, db_name, col_name, doc_id):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        doc = self.client[db_name][col_name].find_one({"_id": _id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    def update_document(self, db_name, col_name, doc_id, update_data: dict):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        result = self.client[db_name][col_name].update_one(
            {"_id": _id},
            {"$set": update_data}
        )
        return result.modified_count

    def delete_document(self, db_name, col_name, doc_id):
        try:
            _id = ObjectId(doc_id)
        except InvalidId:
            raise ValueError("Invalid ObjectId")

        result = self.client[db_name][col_name].delete_one({"_id": _id})
        return result.deleted_count

    # --------- Bulk Operations ---------

    def export_collection(self, db_name, col_name):
        logger.info(f"Exporting collection: {db_name}.{col_name}")
        docs = self.client[db_name][col_name].find()
        exported = []
        for doc in docs:
            doc['_id'] = str(doc['_id'])
            exported.append(doc)
        return exported

    def import_documents(self, db_name, col_name, documents: list):
        if len(documents) > 500:
            raise ValueError("Too many documents to import (max 500)")

        for doc in documents:
            if '_id' in doc:
                try:
                    doc['_id'] = ObjectId(doc['_id'])
                except Exception:
                    del doc['_id']  # Let MongoDB assign one

        result = self.client[db_name][col_name].insert_many(documents)
        return [str(_id) for _id in result.inserted_ids]
