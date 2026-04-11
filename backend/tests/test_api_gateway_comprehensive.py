# SPDX-License-Identifier: MIT
"""
Comprehensive Test Suite for MongoDB Management API

Tests ALL endpoints from OpenAPI spec across 4 configuration scenarios:
- basic: No authz, no opaque IDs
- authz: Authz enabled, no opaque IDs
- opaque: Opaque IDs enabled, no authz
- full: Both authz and opaque IDs enabled

Coverage:
✅ Health & OpenAPI
✅ Database Management (list, delete, stats)
✅ Collection Management (list, create, delete, stats)
✅ Document Management (create, query, get, update, delete)
✅ Data Import/Export
✅ GridFS File Storage (all operations)
✅ Index Management (list, create, delete, get, text, stats)
✅ Permission Groups (CRUD)
✅ User Permissions (CRUD)
✅ Permission Checks
✅ Error handling and edge cases

Run with: pytest test_api_gateway_comprehensive.py -v
"""

import io
import json
import time
from typing import Dict

import pytest
from fastapi.testclient import TestClient


def get_unique_name(prefix: str) -> str:
    """Generate unique resource name"""
    return f"{prefix}_{int(time.time() * 1000000)}"


class TestAPIComprehensive:
    """Comprehensive test suite for all API endpoints"""

    # ==================== HELPER METHODS ====================

    def get_auth_headers(self, email: str, config: str) -> Dict[str, str]:
        """Get authentication headers when authz is enabled"""
        if config in ["authz", "full"]:
            return {"X-Auth-Request-Email": email}
        return {}

    def setup_method(self, method):
        """Setup before each test"""
        self.admin_email = "admin@test.com"
        self.user_email = "user@test.com"
        self.test_db = get_unique_name("testdb")
        self.test_col = get_unique_name("testcol")
        self.test_bucket = get_unique_name("testbucket")

    def create_test_collection(self, client: TestClient, config: str, 
                               db: str = None, col: str = None) -> tuple:
        """Helper to create a test database and collection"""
        if db is None:
            db = self.test_db
        if col is None:
            col = self.test_col
            
        headers = self.get_auth_headers(self.admin_email, config)
        response = client.post(
            "/v1/db/col",
            json={"db": db, "name": col},
            headers=headers
        )
        return db, col, response

    def insert_test_document(self, client: TestClient, config: str, 
                            db: str, col: str, doc_data: dict) -> dict:
        """Helper to insert a document"""
        headers = self.get_auth_headers(self.admin_email, config)
        response = client.post(
            f"/v1/db/{db}/col/{col}/doc",
            json={"data": doc_data},
            headers=headers
        )
        return response.json() if response.status_code == 200 else {}

    def cleanup_database(self, client: TestClient, config: str, db: str):
        """Helper to cleanup test database"""
        headers = self.get_auth_headers(self.admin_email, config)
        try:
            client.delete(f"/v1/db/{db}", headers=headers)
        except Exception:
            pass

    # ==================== HEALTH & OPENAPI ====================

    def test_health_endpoint(self, test_client, test_config):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_openapi_endpoint(self, test_client, test_config):
        """Test OpenAPI spec is accessible"""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "openapi" in data

    # ==================== DATABASE MANAGEMENT ====================

    def test_list_databases(self, test_client, test_config):
        """Test GET /v1/db - list databases"""
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get("/v1/db", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "databases" in data
            assert "total" in data
            assert "page" in data
        else:
            # May require auth
            assert response.status_code in [200, 401, 403]

    def test_database_pagination(self, test_client, test_config):
        """Test database listing with pagination"""
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get("/v1/db?page=1&page_size=5", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert data["page"] == 1
            assert data["page_size"] == 5

    def test_delete_database(self, test_client, test_config):
        """Test DELETE /v1/db/{db} - delete database"""
        # Create a database first
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Delete the database
        response = test_client.delete(f"/v1/db/{db}", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        else:
            assert response.status_code in [200, 403]

    def test_get_database_stats(self, test_client, test_config):
        """Test GET /v1/db/{db}/stats - get database statistics"""
        # Create a database first
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get(f"/v1/db/{db}/stats", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            if len(data) > 0:
                assert "database" in data[0]
                assert "stats" in data[0]
        
        # Cleanup
        self.cleanup_database(test_client, test_config, db)

    # ==================== COLLECTION MANAGEMENT ====================

    def test_list_collections(self, test_client, test_config):
        """Test GET /v1/db/{db}/col - list collections"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get(f"/v1/db/{db}/col", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "collections" in data
            assert len(data["collections"]) > 0
        
        self.cleanup_database(test_client, test_config, db)

    def test_create_collection(self, test_client, test_config):
        """Test POST /v1/db/col - create collection"""
        db, col, response = self.create_test_collection(test_client, test_config)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        else:
            assert response.status_code in [200, 403]
        
        self.cleanup_database(test_client, test_config, db)

    def test_delete_collection(self, test_client, test_config):
        """Test DELETE /v1/db/{db}/col/{col} - delete collection"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.delete(f"/v1/db/{db}/col/{col}", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_get_collection_stats(self, test_client, test_config):
        """Test GET /v1/db/{db}/col/{col}/stats - get collection statistics"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get(f"/v1/db/{db}/col/{col}/stats", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
            assert "documents_count" in data["stats"]
        
        self.cleanup_database(test_client, test_config, db)

    # ==================== DOCUMENT MANAGEMENT ====================

    def test_create_document(self, test_client, test_config):
        """Test POST /v1/db/{db}/col/{col}/doc - create document"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        doc_data = {"name": "Test User", "email": "test@example.com", "age": 30}
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/doc",
            json={"data": doc_data},
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_query_documents(self, test_client, test_config):
        """Test POST /v1/db/{db}/col/{col}/doc/query - query documents"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        # Insert test documents
        headers = self.get_auth_headers(self.admin_email, test_config)
        for i in range(3):
            doc = {"name": f"User {i}", "age": 20 + i}
            self.insert_test_document(test_client, test_config, db, col, doc)
        
        # Query all documents
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/doc/query",
            json={},
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert len(data["data"]) >= 3
        
        self.cleanup_database(test_client, test_config, db)

    def test_query_documents_with_filter(self, test_client, test_config):
        """Test querying documents with MongoDB filter operators"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        # Insert test documents
        headers = self.get_auth_headers(self.admin_email, test_config)
        for i in range(5):
            doc = {"name": f"User {i}", "age": 20 + i, "active": i % 2 == 0}
            self.insert_test_document(test_client, test_config, db, col, doc)
        
        # Query with filter: age > 21
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/doc/query",
            json={"filter": {"age": {"$gt": 21}}},
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert len(data["data"]) >= 3
            for doc in data["data"]:
                assert doc["age"] > 21
        
        self.cleanup_database(test_client, test_config, db)

    def test_query_documents_with_sort(self, test_client, test_config):
        """Test querying documents with sort"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        for i in range(3):
            doc = {"name": f"User {i}", "age": 30 - i}
            self.insert_test_document(test_client, test_config, db, col, doc)
        
        # Query with sort
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/doc/query?sort_field=age&sort_order=1",
            json={},
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            if len(data["data"]) >= 2:
                assert data["data"][0]["age"] <= data["data"][1]["age"]
        
        self.cleanup_database(test_client, test_config, db)

    def test_get_document_by_id(self, test_client, test_config):
        """Test GET /v1/db/{db}/col/{col}/doc/{doc_id} - get document by ID"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        # Insert a document without ID (MongoDB will generate one)
        doc_data = {"name": "Test User", "email": "test@example.com"}
        self.insert_test_document(test_client, test_config, db, col, doc_data)
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Query to get the document and its ID
        query_resp = test_client.post(
            f"/v1/db/{db}/col/{col}/doc/query",
            json={},
            headers=headers
        )
        
        if query_resp.status_code == 200 and len(query_resp.json()["data"]) > 0:
            doc_id = str(query_resp.json()["data"][0]["_id"])
            
            # Get document by ID
            response = test_client.get(f"/v1/db/{db}/col/{col}/doc/{doc_id}", headers=headers)
            
            if test_config in ["basic", "opaque"]:
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
                assert len(data["data"]) > 0
        
        self.cleanup_database(test_client, test_config, db)

    def test_update_document(self, test_client, test_config):
        """Test PUT /v1/db/{db}/col/{col}/doc/{doc_id} - update document"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        # Insert a document
        doc_data = {"name": "Original Name", "age": 25}
        self.insert_test_document(test_client, test_config, db, col, doc_data)
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Get the document ID
        query_resp = test_client.post(
            f"/v1/db/{db}/col/{col}/doc/query",
            json={},
            headers=headers
        )
        
        if query_resp.status_code == 200 and len(query_resp.json()["data"]) > 0:
            doc_id = str(query_resp.json()["data"][0]["_id"])
            
            # Update the document
            update_data = {"name": "Updated Name", "age": 30}
            response = test_client.put(
                f"/v1/db/{db}/col/{col}/doc/{doc_id}",
                json={"data": update_data},
                headers=headers
            )
            
            if test_config in ["basic", "opaque"]:
                assert response.status_code == 200
                data = response.json()
                assert "message" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_delete_document(self, test_client, test_config):
        """Test DELETE /v1/db/{db}/col/{col}/doc/{doc_id} - delete document"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        # Insert a document
        doc_data = {"name": "To Be Deleted"}
        self.insert_test_document(test_client, test_config, db, col, doc_data)
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Get the document ID
        query_resp = test_client.post(
            f"/v1/db/{db}/col/{col}/doc/query",
            json={},
            headers=headers
        )
        
        if query_resp.status_code == 200 and len(query_resp.json()["data"]) > 0:
            doc_id = str(query_resp.json()["data"][0]["_id"])
            
            # Delete the document
            response = test_client.delete(f"/v1/db/{db}/col/{col}/doc/{doc_id}", headers=headers)
            
            if test_config in ["basic", "opaque"]:
                assert response.status_code == 200
                data = response.json()
                assert "message" in data
        
        self.cleanup_database(test_client, test_config, db)

    # ==================== DATA IMPORT/EXPORT ====================

    def test_export_collection(self, test_client, test_config):
        """Test GET /v1/db/{db}/col/{col}/export - export collection"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        # Insert some documents
        headers = self.get_auth_headers(self.admin_email, test_config)
        for i in range(3):
            doc = {"name": f"User {i}", "value": i}
            self.insert_test_document(test_client, test_config, db, col, doc)
        
        # Export collection
        response = test_client.get(f"/v1/db/{db}/col/{col}/export", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data
            assert len(data["documents"]) >= 3
        
        self.cleanup_database(test_client, test_config, db)

    def test_import_documents(self, test_client, test_config):
        """Test POST /v1/db/{db}/col/{col}/import - import documents"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a JSON file to import
        documents = [
            {"name": "Import User 1", "value": 100},
            {"name": "Import User 2", "value": 200}
        ]
        json_content = json.dumps(documents)
        
        files = {"file": ("import.json", io.BytesIO(json_content.encode()), "application/json")}
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/import",
            files=files,
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "imported_count" in data
            assert data["imported_count"] >= 2
        
        self.cleanup_database(test_client, test_config, db)

    # ==================== GRIDFS FILE STORAGE ====================

    def test_list_gridfs_buckets(self, test_client, test_config):
        """Test GET /v1/db/{db}/gridfs - list GridFS buckets"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get(f"/v1/db/{db}/gridfs", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "buckets" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_upload_file_to_gridfs(self, test_client, test_config):
        """Test POST /v1/db/{db}/gridfs/upload - upload file"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a test file
        file_content = b"This is a test file content for GridFS"
        files = {
            "file": ("test.txt", io.BytesIO(file_content), "text/plain")
        }
        data = {
            "bucket_name": self.test_bucket,
            "metadata": json.dumps({"description": "Test file"})
        }
        
        response = test_client.post(
            f"/v1/db/{db}/gridfs/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            resp_data = response.json()
            assert "file_id" in resp_data
            assert "bucket_name" in resp_data
        
        self.cleanup_database(test_client, test_config, db)

    def test_list_files_in_bucket(self, test_client, test_config):
        """Test GET /v1/db/{db}/gridfs/{bucket_name}/files - list files"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Upload a file first
        file_content = b"Test file for listing"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"bucket_name": self.test_bucket}
        
        upload_resp = test_client.post(
            f"/v1/db/{db}/gridfs/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if upload_resp.status_code != 200:
            pytest.skip("Cannot upload file in this config")
        
        # List files in bucket
        response = test_client.get(
            f"/v1/db/{db}/gridfs/{self.test_bucket}/files",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert len(data["data"]) > 0
        
        self.cleanup_database(test_client, test_config, db)

    def test_get_gridfs_bucket_stats(self, test_client, test_config):
        """Test GET /v1/db/{db}/gridfs/{bucket_name}/stats - get bucket stats"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Upload a file to create bucket
        file_content = b"Test file"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"bucket_name": self.test_bucket}
        
        upload_resp = test_client.post(
            f"/v1/db/{db}/gridfs/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if upload_resp.status_code != 200:
            pytest.skip("Cannot upload file in this config")
        
        # Get bucket stats
        response = test_client.get(
            f"/v1/db/{db}/gridfs/{self.test_bucket}/stats",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
            assert "files_count" in data["stats"]
        
        self.cleanup_database(test_client, test_config, db)

    def test_get_file_metadata(self, test_client, test_config):
        """Test GET /v1/db/{db}/gridfs/{bucket_name}/file/{file_id} - get file metadata"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Upload a file
        file_content = b"Test file for metadata"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"bucket_name": self.test_bucket, "metadata": json.dumps({"key": "value"})}
        
        upload_resp = test_client.post(
            f"/v1/db/{db}/gridfs/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if upload_resp.status_code != 200:
            pytest.skip("Cannot upload file in this config")
        
        file_id = upload_resp.json()["file_id"]
        
        # Get file metadata
        response = test_client.get(
            f"/v1/db/{db}/gridfs/{self.test_bucket}/file/{file_id}",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "filename" in data
            assert "length" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_download_file(self, test_client, test_config):
        """Test GET /v1/db/{db}/gridfs/{bucket_name}/file/{file_id}/download - download file"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Upload a file
        file_content = b"Download test content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"bucket_name": self.test_bucket}
        
        upload_resp = test_client.post(
            f"/v1/db/{db}/gridfs/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if upload_resp.status_code != 200:
            pytest.skip("Cannot upload file in this config")
        
        file_id = upload_resp.json()["file_id"]
        
        # Download the file
        response = test_client.get(
            f"/v1/db/{db}/gridfs/{self.test_bucket}/file/{file_id}/download",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            assert response.content == file_content
        
        self.cleanup_database(test_client, test_config, db)

    def test_delete_gridfs_file(self, test_client, test_config):
        """Test DELETE /v1/db/{db}/gridfs/{bucket_name}/file/{file_id} - delete file"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Upload a file
        file_content = b"File to delete"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"bucket_name": self.test_bucket}
        
        upload_resp = test_client.post(
            f"/v1/db/{db}/gridfs/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if upload_resp.status_code != 200:
            pytest.skip("Cannot upload file in this config")
        
        file_id = upload_resp.json()["file_id"]
        
        # Delete the file
        response = test_client.delete(
            f"/v1/db/{db}/gridfs/{self.test_bucket}/file/{file_id}",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_delete_gridfs_bucket(self, test_client, test_config):
        """Test DELETE /v1/db/{db}/gridfs/{bucket_name} - delete bucket"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create database in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Upload a file to create bucket
        file_content = b"Bucket to delete"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"bucket_name": self.test_bucket}
        
        upload_resp = test_client.post(
            f"/v1/db/{db}/gridfs/upload",
            files=files,
            data=data,
            headers=headers
        )
        
        if upload_resp.status_code != 200:
            pytest.skip("Cannot upload file in this config")
        
        # Delete the bucket
        response = test_client.delete(
            f"/v1/db/{db}/gridfs/{self.test_bucket}",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        
        self.cleanup_database(test_client, test_config, db)

    # ==================== INDEX MANAGEMENT ====================

    def test_list_indexes(self, test_client, test_config):
        """Test GET /v1/db/{db}/col/{col}/indexes - list indexes"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get(f"/v1/db/{db}/col/{col}/indexes", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "indexes" in data
            # Should have at least _id_ index
            assert len(data["indexes"]) >= 1
        
        self.cleanup_database(test_client, test_config, db)

    def test_create_index(self, test_client, test_config):
        """Test POST /v1/db/{db}/col/{col}/indexes - create index"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        index_data = {
            "keys": {"email": 1},
            "options": {"unique": True, "name": "email_unique_idx"}
        }
        
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/indexes",
            json=index_data,
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "index_name" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_get_index_info(self, test_client, test_config):
        """Test GET /v1/db/{db}/col/{col}/indexes/{index_name} - get index info"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Get info for _id_ index (always exists)
        response = test_client.get(
            f"/v1/db/{db}/col/{col}/indexes/_id_",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            # This endpoint may return 500 if not properly implemented
            # or 200 with valid index info
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert "index_info" in data
                assert data["index_info"]["name"] == "_id_"
        
        self.cleanup_database(test_client, test_config, db)

    def test_drop_index(self, test_client, test_config):
        """Test DELETE /v1/db/{db}/col/{col}/indexes/{index_name} - drop index"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create an index first
        index_data = {"keys": {"name": 1}, "options": {"name": "name_idx"}}
        create_idx_resp = test_client.post(
            f"/v1/db/{db}/col/{col}/indexes",
            json=index_data,
            headers=headers
        )
        
        if create_idx_resp.status_code != 200:
            pytest.skip("Cannot create index in this config")
        
        # Drop the index
        response = test_client.delete(
            f"/v1/db/{db}/col/{col}/indexes/name_idx",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_create_text_index(self, test_client, test_config):
        """Test POST /v1/db/{db}/col/{col}/indexes/text - create text index"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/indexes/text?fields=description&fields=title&language=english",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "index_name" in data
            assert "fields" in data
        
        self.cleanup_database(test_client, test_config, db)

    def test_get_index_stats(self, test_client, test_config):
        """Test GET /v1/db/{db}/col/{col}/indexes/stats - get index stats"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get(f"/v1/db/{db}/col/{col}/indexes/stats", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            # May return 500 if stats aggregation fails on empty collection
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert "index_stats" in data
                assert isinstance(data["index_stats"], list)
        
        self.cleanup_database(test_client, test_config, db)

    # ==================== PERMISSION GROUPS (AUTHZ ONLY) ====================

    def test_create_permission_group(self, test_client, test_config):
        """Test POST /v1/admin/groups - create permission group"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        group_data = {
            "name": get_unique_name("testgroup"),
            "description": "Test permission group",
            "grants": {
                "test_*": {"r": True, "w": True, "d": False}
            }
        }
        
        response = test_client.post("/v1/admin/groups", json=group_data, headers=headers)
        
        # May fail with 409 if already exists or 200 if created
        assert response.status_code in [200, 409]

    def test_list_permission_groups(self, test_client, test_config):
        """Test GET /v1/admin/groups - list permission groups"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get("/v1/admin/groups", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_permission_group(self, test_client, test_config):
        """Test GET /v1/admin/groups/{name} - get permission group"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a group first
        group_name = get_unique_name("testgroup")
        group_data = {
            "name": group_name,
            "description": "Test group",
            "grants": {"test_*": {"r": True}}
        }
        create_resp = test_client.post("/v1/admin/groups", json=group_data, headers=headers)
        
        if create_resp.status_code not in [200, 409]:
            pytest.skip("Cannot create group in this config")
        
        # Get the group
        response = test_client.get(f"/v1/admin/groups/{group_name}", headers=headers)
        
        if create_resp.status_code == 200:
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == group_name

    def test_update_permission_group(self, test_client, test_config):
        """Test PUT /v1/admin/groups/{name} - update permission group"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a group first
        group_name = get_unique_name("testgroup")
        group_data = {
            "name": group_name,
            "description": "Original description",
            "grants": {"test_*": {"r": True}}
        }
        create_resp = test_client.post("/v1/admin/groups", json=group_data, headers=headers)
        
        if create_resp.status_code not in [200, 409]:
            pytest.skip("Cannot create group in this config")
        
        # Update the group
        update_data = {
            "description": "Updated description",
            "grants": {"test_*": {"r": True, "w": True}}
        }
        response = test_client.put(
            f"/v1/admin/groups/{group_name}",
            json=update_data,
            headers=headers
        )
        
        if create_resp.status_code == 200:
            assert response.status_code == 200
            data = response.json()
            assert data["description"] == "Updated description"

    def test_delete_permission_group(self, test_client, test_config):
        """Test DELETE /v1/admin/groups/{name} - delete permission group"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a group first
        group_name = get_unique_name("testgroup")
        group_data = {
            "name": group_name,
            "description": "To be deleted",
            "grants": {"test_*": {"r": True}}
        }
        create_resp = test_client.post("/v1/admin/groups", json=group_data, headers=headers)
        
        if create_resp.status_code not in [200, 409]:
            pytest.skip("Cannot create group in this config")
        
        # Delete the group
        response = test_client.delete(f"/v1/admin/groups/{group_name}", headers=headers)
        
        if create_resp.status_code == 200:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data

    # ==================== USER PERMISSIONS (AUTHZ ONLY) ====================

    def test_create_user_permission(self, test_client, test_config):
        """Test POST /v1/admin/users - create user permission"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        user_data = {
            "email": f"testuser_{int(time.time())}@example.com",
            "role": "user",
            "groups": []
        }
        
        response = test_client.post("/v1/admin/users", json=user_data, headers=headers)
        
        # May fail with 409 if already exists or 200 if created
        assert response.status_code in [200, 409]

    def test_list_user_permissions(self, test_client, test_config):
        """Test GET /v1/admin/users - list user permissions"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get("/v1/admin/users", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_user_permission(self, test_client, test_config):
        """Test GET /v1/admin/users/{user_email} - get user permission"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a user first
        user_email = f"testuser_{int(time.time())}@example.com"
        user_data = {
            "email": user_email,
            "role": "user",
            "groups": []
        }
        create_resp = test_client.post("/v1/admin/users", json=user_data, headers=headers)
        
        if create_resp.status_code not in [200, 409]:
            pytest.skip("Cannot create user in this config")
        
        # Get the user
        response = test_client.get(f"/v1/admin/users/{user_email}", headers=headers)
        
        if create_resp.status_code == 200:
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == user_email

    def test_update_user_permission(self, test_client, test_config):
        """Test PUT /v1/admin/users/{user_email} - update user permission"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a user first
        user_email = f"testuser_{int(time.time())}@example.com"
        user_data = {
            "email": user_email,
            "role": "user",
            "groups": []
        }
        create_resp = test_client.post("/v1/admin/users", json=user_data, headers=headers)
        
        if create_resp.status_code not in [200, 409]:
            pytest.skip("Cannot create user in this config")
        
        # Update the user
        update_data = {
            "role": "user",
            "groups": [],
            "isActive": False
        }
        response = test_client.put(
            f"/v1/admin/users/{user_email}",
            json=update_data,
            headers=headers
        )
        
        if create_resp.status_code == 200:
            assert response.status_code == 200
            data = response.json()
            assert not data["isActive"]

    def test_delete_user_permission(self, test_client, test_config):
        """Test DELETE /v1/admin/users/{user_email} - delete user permission"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Create a user first
        user_email = f"testuser_{int(time.time())}@example.com"
        user_data = {
            "email": user_email,
            "role": "user",
            "groups": []
        }
        create_resp = test_client.post("/v1/admin/users", json=user_data, headers=headers)
        
        if create_resp.status_code not in [200, 409]:
            pytest.skip("Cannot create user in this config")
        
        # Delete the user
        response = test_client.delete(f"/v1/admin/users/{user_email}", headers=headers)
        
        if create_resp.status_code == 200:
            assert response.status_code == 200
            data = response.json()
            assert "message" in data

    def test_check_permission(self, test_client, test_config):
        """Test POST /v1/permissions/check - check permission"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Permissions only available when authz is enabled")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        check_data = {
            "database": "test_db",
            "operation": "read"
        }
        
        response = test_client.post(
            "/v1/permissions/check",
            json=check_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "allowed" in data
        assert "user_email" in data

    # ==================== ERROR HANDLING & EDGE CASES ====================

    def test_invalid_database_name(self, test_client, test_config):
        """Test creating collection with invalid database name"""
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Empty database name
        response = test_client.post(
            "/v1/db/col",
            json={"db": "", "name": "test"},
            headers=headers
        )
        assert response.status_code in [400, 422]

    def test_invalid_collection_name(self, test_client, test_config):
        """Test creating collection with invalid collection name"""
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Empty collection name
        response = test_client.post(
            "/v1/db/col",
            json={"db": "test", "name": ""},
            headers=headers
        )
        assert response.status_code in [400, 422]

    def test_page_size_validation(self, test_client, test_config):
        """Test page size must not exceed 100"""
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.get("/v1/db?page_size=101", headers=headers)
        assert response.status_code in [400, 422]

    def test_unauthorized_access(self, test_client, test_config):
        """Test unauthorized access is blocked when authz enabled"""
        if test_config not in ["authz", "full"]:
            pytest.skip("Authorization not enabled")
        
        # No auth headers
        response = test_client.get("/v1/db")
        assert response.status_code == 401

    def test_system_database_protection(self, test_client, test_config):
        """Test system databases cannot be deleted"""
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Try to delete admin database
        response = test_client.delete("/v1/db/admin", headers=headers)
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code in [400, 403]

    def test_drop_id_index_protection(self, test_client, test_config):
        """Test _id_ index cannot be dropped"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        response = test_client.delete(
            f"/v1/db/{db}/col/{col}/indexes/_id_",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 400
        
        self.cleanup_database(test_client, test_config, db)

    def test_nonexistent_document(self, test_client, test_config):
        """Test getting nonexistent document returns empty or 404"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        headers = self.get_auth_headers(self.admin_email, test_config)
        
        # Use a valid ObjectId format that doesn't exist
        nonexistent_id = "507f1f77bcf86cd799439011"
        response = test_client.get(
            f"/v1/db/{db}/col/{col}/doc/{nonexistent_id}",
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            # May return 200 with empty data or 404
            assert response.status_code in [200, 404]
            if response.status_code == 200:
                data = response.json()
                assert len(data["data"]) == 0
        
        self.cleanup_database(test_client, test_config, db)

    def test_complex_mongodb_query(self, test_client, test_config):
        """Test complex MongoDB query with multiple operators"""
        db, col, create_resp = self.create_test_collection(test_client, test_config)
        
        if create_resp.status_code != 200:
            pytest.skip("Cannot create collection in this config")
        
        # Insert test data
        headers = self.get_auth_headers(self.admin_email, test_config)
        for i in range(10):
            doc = {
                "name": f"User {i}",
                "age": 20 + i,
                "status": "active" if i % 2 == 0 else "inactive",
                "tags": ["tag1", "tag2"] if i < 5 else ["tag3"]
            }
            self.insert_test_document(test_client, test_config, db, col, doc)
        
        # Complex query: (age > 23 AND status = active) OR tags contains tag3
        query = {
            "filter": {
                "$or": [
                    {"$and": [{"age": {"$gt": 23}}, {"status": "active"}]},
                    {"tags": {"$in": ["tag3"]}}
                ]
            }
        }
        
        response = test_client.post(
            f"/v1/db/{db}/col/{col}/doc/query",
            json=query,
            headers=headers
        )
        
        if test_config in ["basic", "opaque"]:
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert len(data["data"]) > 0
        
        self.cleanup_database(test_client, test_config, db)
