# MongoDhārā Backend (FastAPI)

High-performance REST API for MongoDB management: databases, collections, documents, indexes, GridFS, and RBAC permissions.

---

## Quick Start

### Development (hot reload)

1. Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

2. Run locally:

```bash
./run_local.sh   # invokes python app/main.py with reload
```

Or directly:

```bash
python app/main.py
```

3. Access documentation:

- **OpenAPI UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Production (Gunicorn + Uvicorn workers)

```bash
cd backend
gunicorn -c gunicorn.conf.py app.main:app
```

Custom example:

```bash
gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers $(python -c 'import multiprocessing;print(multiprocessing.cpu_count()*2+1)') \
  --bind 0.0.0.0:8000 \
  --log-level info
```

---

## Architecture Overview

Layered design:

1. **Entry**: `app/main.py` builds FastAPI app, sets middleware, routes, conditional permission routes.
2. **Middleware**: `app/core/middleware.py` (order matters) handles CORS → base64 path decoding → opaque ID decryption → access logging.
3. **Services**: `app/services/*.py` contain Mongo interactions (one `MongoClient` per process via `BaseMongoService`). Opaque IDs appended when `ENABLE_OPAQUE_IDS=true`.
4. **Routes**: `app/api/v1/routes/*` map HTTP verbs to service methods; validation/permission dependencies; consistent response envelopes.
5. **AuthZ**: `app/dependencies/auth.py` reads authentication headers (configurable via `AUTH_EMAIL_HEADER`), checks RBAC via `PermissionService` (stored in `mongodhara.user_permissions`).
6. **Config**: `app/core/config.py` centralizes env-driven feature flags (opaque IDs, authz, audit logging, GridFS limits).

**Opaque ID flow** (when enabled): client receives `opaque_id` in list endpoints → sends it back in path → `OpaqueIDDecodingMiddleware` decrypts/validates → downstream sees real names.

---

## Environment Variables (.env)

| Name                     | Purpose                                     | Default                   |
| ------------------------ | ------------------------------------------- | ------------------------- |
| MONGO_URI                | MongoDB connection string                   | mongodb://localhost:27017 |
| BASE_PATH                | Optional root path (for reverse proxy)      | ""                        |
| LOG_LEVEL                | Logging level for Gunicorn/Uvicorn & app    | info                      |
| ENVIRONMENT              | deployment environment tag                  | production                |
| ENABLE_OPAQUE_IDS        | AES-GCM opaque IDs for path params          | false                     |
| OPAQUE_ID_ENCRYPTION_KEY | Base64 128-bit key (required if above true) | (none)                    |
| ENABLE_AUTHZ             | Enable RBAC permission enforcement          | false                     |
| AUTH_EMAIL_HEADER        | Header name for authenticated user email    | X-Auth-Request-Email      |
| ENABLE_AUDIT_LOGGING     | Enable audit logging to MongoDB             | false                     |
| GRIDFS_CHUNK_SIZE        | Stream chunk size bytes                     | 1048576                   |
| GRIDFS_MAX_FILE_SIZE     | Max upload size bytes                       | 104857600                 |
| GRIDFS_TIMEOUT           | GridFS operation timeout seconds            | 300                       |

**Generate encryption key**:

```bash
python -c "import os,base64;print(base64.b64encode(os.urandom(16)).decode())"
```

---

## Middleware Order (outer → inner)

1. CORS (`CORSMiddleware`)
2. `PathDecodingMiddleware` (legacy base64 support)
3. `OpaqueIDDecodingMiddleware` (AES-GCM decrypt & validate)
4. `AccessLogMiddleware` (logs original encrypted path in non-DEBUG)

Changing order can break decoding/logging semantics—keep as-is.

---

## API Endpoints (prefix `/v1`)

| Domain        | Examples                                                                                                                    |
| ------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Databases     | `GET /v1/db` list; `GET /v1/db/{db}/stats`; `DELETE /v1/db/{db}`                                                            |
| Collections   | `GET /v1/db/{db}/col`; `POST /v1/db/col`; `DELETE /v1/db/{db}/col/{col}`; `GET /v1/db/{db}/col/{col}/stats`                 |
| Documents     | `POST /v1/db/{db}/col/{col}/doc`; `POST /v1/db/{db}/col/{col}/doc/query`; CRUD by id; export/import                         |
| Indexes       | `GET /v1/db/{db}/col/{col}/indexes`; create/drop; text index; stats                                                         |
| GridFS        | bucket list `/gridfs`; bucket stats; upload (multipart streaming); list files; file metadata/download/delete; delete bucket |
| Permissions\* | CRUD `/permissions`; check `/permissions/check` (_only when `ENABLE_AUTHZ=true`)_                                           |

Responses commonly wrap: database, collection/bucket, data, pagination, plus `opaque_id` fields when enabled.

---

## RBAC Model

Stored in `mongodhara.user_permissions` collection. Document shape:

```json
{
  "user_email": "admin@company.com",
  "role": "admin",
  "permissions": [
    {
      "database": "prod_*",
      "operations": ["read", "write", "delete", "admin"]
    },
    {
      "database": "staging_*",
      "operations": ["read", "write"]
    }
  ]
}
```

**Operations checked**: `read` | `write` | `delete` | `admin`. Wildcards (`*`) supported. Admin role grants all.

**Header required** (when authz enabled): Configured via `AUTH_EMAIL_HEADER` environment variable (defaults to `X-Auth-Request-Email`).  
This allows compatibility with different authentication proxies (oauth2-proxy, Authelia, Traefik Forward Auth, etc.).

---

## Opaque IDs

Encryption: AES-GCM (nonce 12 bytes + ciphertext) → urlsafe base64.  
**Service**: `app/services/opaque_id_service.py` (singleton). Added in list endpoints as `opaque_id`. Middleware decrypts early; logs retain encrypted path unless DEBUG.  
Fallback path base64 decoding (legacy) handled separately for backward compat.

---

## GridFS Streaming

Large uploads/downloads chunked (default 1MB) to avoid memory spikes. Tune via `GRIDFS_CHUNK_SIZE`. Validation of bucket names uses same rules as collections.

---

## Index Management Patterns

Use `index_service.create_index(db, col, keys, options)`; text indexes via `.../indexes/text` (fields as query params). Stats use `$indexStats` fallback to list.

---

## Testing

`pytest.ini` config sets coverage, markers, env (`ENABLE_AUTHZ=true` in tests). Run:

```bash
cd backend
pytest
```

Tests expect authz enabled; supply header matching `AUTH_EMAIL_HEADER` configuration (default `X-Auth-Request-Email`) when hitting protected endpoints.

---

## Logging

`AccessLogMiddleware` replaces default Gunicorn/Uvicorn access logs. Set `LOG_LEVEL=debug` to see decrypted paths; higher levels show encrypted/original for security.

---

## Health & API Documentation

**Health**: `GET /health` returns service + version.

**Docs**:

- `/docs` — OpenAPI Swagger UI
- `/redoc` — ReDoc documentation
- `/openapi.json` — OpenAPI schema (includes security scheme when authz enabled)

---

## Audit Logging

When `ENABLE_AUDIT_LOGGING=true`, all significant operations are logged to `mongodhara.audit_logs` collection for compliance and monitoring.

### Logged Operations

- Database: create, delete
- Collection: create, delete
- Permissions: create, update, delete
- Future: documents, indexes, GridFS

### Log Structure

```json
{
  "_id": "ObjectId",
  "user_email": "admin@company.com",
  "operation": "create_collection",
  "resource": {
    "type": "collection",
    "database": "db_name",
    "name": "col_name"
  },
  "details": {},
  "timestamp": "2025-10-20T12:00:00Z",
  "status": "success",
  "ip": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "error_message": null
}
```

### Indexes

- `timestamp` (TTL 365 days)
- `user_email`, `operation`, `(timestamp, user_email)`

### Query Examples

```javascript
// Recent operations by user
db.audit_logs
  .find({ user_email: "admin@company.com" })
  .sort({ timestamp: -1 })
  .limit(10);

// Failed operations
db.audit_logs.find({ status: "failure" });

// Operations in last 24h
db.audit_logs.find({
  timestamp: { $gte: new Date(Date.now() - 24 * 60 * 60 * 1000) },
});
```

### Security

- **System Database Protection**: All write operations (create/delete databases, collections, documents, indexes, GridFS files/buckets, import data) are blocked on system databases: `admin`, `local`, `config`, `mongodhara`.
- Logs exclude sensitive data (e.g., full document contents).
- Access restricted to admin users.
- Optional encryption for high compliance.

---

## Common Gotchas

1. Enabling `ENABLE_OPAQUE_IDS` without providing a valid 128-bit key → startup `ValueError`.
2. Uploading large GridFS file with insufficient `GRIDFS_MAX_FILE_SIZE` → 413 error.
3. Missing auth header (configured via `AUTH_EMAIL_HEADER`) when `ENABLE_AUTHZ=true` → 401 before route logic.
4. Attempt to drop `_id_` index → 400 (explicit guard).
5. Page size >100 on document queries → validation error.
6. Different authentication proxies use different header names - configure via `AUTH_EMAIL_HEADER` to match your setup.

---

## Extending

Add new domain: create `service` module → route file under `api/v1/routes` → include in `setup_routes` in `app/main.py`. Follow response envelope pattern & add opaque IDs where listing resources.

---

## Project Structure

```
backend/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── gunicorn.conf.py            # Gunicorn configuration
├── pytest.ini                  # Test configuration
├── run_local.sh                # Local dev script
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── api/
│   │   └── v1/
│   │       ├── routes/         # Endpoint implementations
│   │       └── __init__.py
│   ├── core/
│   │   ├── config.py           # Environment & config
│   │   ├── middleware.py       # CORS, auth, logging
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── logger.py           # Logging setup
│   │   └── validators.py       # Validation utilities
│   ├── services/
│   │   ├── base.py             # BaseMongoService
│   │   ├── database.py         # Database operations
│   │   ├── collection.py       # Collection operations
│   │   ├── document.py         # Document CRUD
│   │   ├── index.py            # Index management
│   │   ├── gridfs.py           # GridFS file handling
│   │   ├── audit_service.py    # Audit logging
│   │   ├── opaque_id_service.py# Opaque ID encryption
│   │   ├── permission_service.py
│   │   └── __init__.py
│   └── dependencies/
│       ├── auth.py             # Authentication & authz
│       └── models/
│           ├── permission.py   # Permission models
│           └── responses.py    # Response envelopes
└── tests/
    ├── conftest.py             # Pytest fixtures
    ├── test_api_gateway.py
    ├── test_api_gateway_opaque.py
    └── test_api_gateway_comprehensive.py
```

---

## Development Workflow

1. **Clone & setup**:

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure environment** (`.env` file or export):

   ```bash
   export MONGO_URI=mongodb://localhost:27017
   export ENABLE_AUTHZ=false  # disable for local dev if desired
   ```

3. **Run tests**:

   ```bash
   pytest
   ```

4. **Start local server**:

   ```bash
   ./run_local.sh
   ```

5. **Make changes**, test, push.

---

## Deployment Notes

- Use `gunicorn.conf.py` as base config in production
- Ensure `MONGO_URI` points to replica set or cluster for HA
- Set `ENVIRONMENT=production` for compliance/audit features
- Configure reverse proxy (nginx, Traefik) with `BASE_PATH` if needed
- Supply `OPAQUE_ID_ENCRYPTION_KEY` only if `ENABLE_OPAQUE_IDS=true`
- Enable `ENABLE_AUTHZ` and supply `AUTH_EMAIL_HEADER` for RBAC
- Enable `ENABLE_AUDIT_LOGGING` for compliance requirements
- Monitor logs and audit_logs collection regularly

---

**Last updated**: 2025-11-08  
**Status**: Aligns with current implementation; update if new features or services are introduced.
