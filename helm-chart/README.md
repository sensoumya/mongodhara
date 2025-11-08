# MongoDbara Helm Chart

Production-ready Helm chart for MongoDbara - MongoDB management interface with comprehensive ingress routing and security features.

## Quick Start

```bash
# Basic deployment with direct MongoDB URI
helm install mongodhara . \
  --set backend.mongoUri.value="mongodb://user:pass@host:27017/dbname"

# Production with MongoDB secret reference
helm install mongodhara . \
  --set backend.mongoUri.secretRef.enabled=true \
  --set backend.mongoUri.secretRef.secretName=mongo-credentials \
  --set backend.mongoUri.secretRef.key=MONGO_URI \
  --set ingress.host=mongodhara.company.com \
  --set ingress.tls.enabled=true \
  --set ingress.tls.secretName=mongodhara-tls

# Full-featured deployment with OAuth + RBAC
helm install mongodhara . \
  --set backend.mongoUri.secretRef.enabled=true \
  --set backend.mongoUri.secretRef.secretName=mongo-credentials \
  --set global.features.opaqueIds.enabled=true \
  --set global.features.opaqueIds.autoGenerateKey=true \
  --set global.features.authz.enabled=true \
  --set global.features.authz.initialAdminEmail=admin@company.com \
  --set ingress.auth.oauth.enabled=true \
  --set ingress.host=mongodhara.company.com
```

## Prerequisites

- Kubernetes 1.16+
- Helm 3.2.0+
- NGINX Ingress Controller (required for ingress resources)
- MongoDB instance (connection URI required)

## Architecture Overview

By default, this chart deploys:

**Kubernetes Resources:**

- 2 Deployments (frontend + backend)
- 2 Services (frontend + backend)
- 4 Ingress Resources (frontend, backend API, GridFS upload, GridFS download)
- 2 ServiceAccounts
- 1 Secret (for auto-generated encryption keys when opaque IDs enabled)

**Default Behavior:**

- Frontend and backend both enabled
- All 4 ingress resources enabled with optimized rate limiting
- TLS enabled (requires TLS secret)
- Health probes disabled (enable for production)
- HPA disabled (enable for production)
- OAuth disabled (enable for production)
- RBAC authorization disabled (enable for production)
- Opaque IDs enabled (auto-key generation disabled by default)
- Audit logging disabled (enable for compliance)

## Key Features

### Centralized Configuration

All feature configurations are consolidated under `global.features`:

- **Opaque IDs**: `global.features.opaqueIds.*` - Encrypt database/collection names and IDs
- **Authorization**: `global.features.authz.*` - RBAC system with roles, groups, and custom grants

This consolidation ensures:

- Single source of truth for feature enablement
- Environment variables auto-generated from global config
- Clear dependency validation (e.g., authz requires OAuth)

### Flexible MongoDB Configuration

Two options for MongoDB connection:

1. **Direct URI** (simple, not recommended for production):

   ```yaml
   backend:
     mongoUri:
       value: "mongodb://user:pass@host:27017/dbname"
   ```

2. **Secret Reference** (recommended for production):
   ```yaml
   backend:
     mongoUri:
       secretRef:
         enabled: true
         secretName: mongo-credentials
         key: MONGO_URI
   ```

### Separate Ingress Resources with Optimized Rate Limiting

The chart creates **4 separate ingress resources**, each with tailored rate limits and timeouts:

1. **Frontend Ingress** (`/mdhara`) - UI traffic

   - 100 req/sec, 6000/min
   - Shorter timeouts (60s)
   - CORS enabled

2. **Backend API Ingress** (`/mdhara/api`) - General API calls

   - 50 req/sec, 3000/min
   - Moderate timeouts (120s)

3. **GridFS Upload Ingress** - File uploads (plain text & base64 encoded paths)

   - **Strict limits**: 5 req/sec, 50/min (resource-intensive)
   - Long timeouts (600s)
   - 100MB body size limit
   - Proxy buffering disabled

4. **GridFS Download Ingress** - File downloads (plain text & base64 encoded paths)
   - **Moderate limits**: 15 req/sec, 150/min
   - Long timeouts (600s)
   - Range requests support

### Security Features

**Built-in (enabled by default):**

- OWASP-compliant security headers on all ingresses (XSS, CSP, HSTS, Frame-Options, etc.)
- Per-ingress rate limiting with connection limits
- TLS/HTTPS support
- System database write protection (blocks operations on `admin`, `local`, `config`, `mongodhara`)

**Optional (disabled by default, enable for production):**

- OAuth2 authentication at ingress layer (applies to all 4 ingresses)
- Backend RBAC authorization (`backend.authz.enabled`)
- Encrypted/opaque resource IDs (`backend.opaqueIds.enabled`)
- Audit logging to MongoDB (`global.features.auditLogging.enabled`)

### Scalability & Reliability

- Health probes (liveness/readiness) for backend pods
- Horizontal pod autoscaling (HPA) support for both frontend and backend
- Configurable resource requests/limits
- Default 100MB GridFS file size limit (via `GRIDFS_MAX_FILE_SIZE` env var)

## Installation

### 1. Create Required Secrets

```bash
# MongoDB connection
kubectl create secret generic mongodhara-secrets \
  --from-literal=MONGO_URI="mongodb://user:pass@mongo-host:27017/dbname"

# TLS certificate (if using custom domain)
kubectl create secret tls mongodhara-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

### 2. Install Chart

```bash
helm install mongodhara ./helm-chart
```

Or with custom values:

```bash
helm install mongodhara ./helm-chart -f my-values.yaml
```

## Configuration

### Essential Configuration

#### MongoDB Connection

**Option 1: Secret Reference (Recommended)**

```bash
# Create secret first
kubectl create secret generic mongo-credentials \
  --from-literal=MONGO_URI="mongodb://user:pass@mongo-host:27017/dbname"
```

```yaml
backend:
  mongoUri:
    secretRef:
      enabled: true
      secretName: mongo-credentials
      key: MONGO_URI
```

**Option 2: Direct Value (Not recommended for production)**

```yaml
backend:
  mongoUri:
    value: "mongodb://user:pass@host:27017/dbname"
```

#### Custom Domain & TLS

```yaml
ingress:
  host: "mongodhara.company.com"
  tls:
    enabled: true
    secretName: mongodhara-tls
```

### Optional Security Features

#### Enable Opaque IDs

Encrypts database/collection names and document IDs in URLs:

```yaml
global:
  features:
    opaqueIds:
      enabled: true
      autoGenerateKey: true # Auto-generates encryption key on install
```

#### Enable RBAC Authorization

**CRITICAL**: Authorization requires OAuth to be enabled. The deployment will fail with a validation error if `authz.enabled=true` without `oauth.enabled=true`.

```yaml
global:
  features:
    authz:
      enabled: true
      initialAdminEmail: "admin@company.com" # Creates initial admin user
      emailHeader: "X-Auth-Request-Email" # Header from OAuth proxy
      databaseCleanup:
        enabled: false # Set true to cleanup on uninstall
        dropDatabase: true # If true, drops entire DB; if false, drops only user_permissions
      existingDatabase:
        action: "skip" # Options: skip, warn, recreate (dangerous)

ingress:
  auth:
    oauth:
      enabled: true # REQUIRED for authz
      annotations:
        nginx.ingress.kubernetes.io/auth-url: "https://oauth.company.com/auth"
        nginx.ingress.kubernetes.io/auth-signin: "https://oauth.company.com/start"
        nginx.ingress.kubernetes.io/auth-response-headers: "X-Auth-Request-User,X-Auth-Request-Email,X-Auth-Request-Groups"
```

The `emailHeader` parameter configures the authentication header name to match your OAuth proxy (oauth2-proxy, Authelia, Traefik Forward Auth, etc.).

#### Enable Audit Logging

```yaml
global:
  features:
    auditLogging:
      enabled: true
```

Logs are stored in `mongodhara.audit_logs` collection with TTL indexes.

### Production Hardening Checklist

For production deployments, consider:

1. **TLS/Certificates**: Enable `ingress.tls` and use cert-manager for automatic renewal
2. **Authentication**: Enable OAuth at ingress and/or backend RBAC
3. **Secrets Management**: Store all credentials in Kubernetes Secrets, never in values.yaml
4. **Health Probes**: Enable liveness/readiness probes for backend pods
5. **Resource Limits**: Set CPU/memory requests and limits for predictable performance
6. **Network Policies**: Restrict network access to backend service and MongoDB
7. **Monitoring**: Configure Prometheus metrics scraping and log aggregation
8. **Audit Logging**: Enable for compliance requirements
9. **Backups**: Implement MongoDB backup strategy

### Resource Limits Example

```yaml
backend:
  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi
  probes:
    liveness:
      enabled: true
    readiness:
      enabled: true

frontend:
  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 200m
      memory: 256Mi
```

## Complete Values Example

```yaml
# my-values.yaml
backend:
  image:
    repository: myregistry/mongodhara-backend
    tag: "2.1.0"

  mongoUri:
    secretRef:
      enabled: true
      secretName: mongodhara-secrets
      key: MONGO_URI

  authz:
    enabled: true
    initialAdminEmail: "admin@company.com"

  opaqueIds:
    enabled: true

  auditLogging:
    enabled: true

  resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 500m
      memory: 512Mi

  probes:
    liveness:
      enabled: true
    readiness:
      enabled: true

frontend:
  image:
    repository: myregistry/mongodhara-frontend
    tag: "2.1.0"

  resources:
    requests:
      cpu: 50m
      memory: 64Mi
    limits:
      cpu: 200m
      memory: 256Mi

ingress:
  host: "mongodhara.company.com"
  className: "nginx"
  tls:
    enabled: true
    secretName: mongodhara-tls
  auth:
    oauth:
      enabled: false # Enable if using OAuth
```

Then install:

```bash
helm install mongodhara ./helm-chart -f my-values.yaml
```

## Configuration Parameters

### Global

| Parameter                 | Description            | Default |
| ------------------------- | ---------------------- | ------- |
| `global.imageRegistry`    | Global Docker registry | `""`    |
| `global.imagePullSecrets` | Image pull secrets     | `[]`    |

### Backend

| Parameter                               | Description                | Default                |
| --------------------------------------- | -------------------------- | ---------------------- |
| `backend.enabled`                       | Enable backend             | `true`                 |
| `backend.replicaCount`                  | Number of replicas         | `1`                    |
| `backend.image.repository`              | Image repository           | `mongodhara/backend`   |
| `backend.image.tag`                     | Image tag                  | `""` (chart version)   |
| `backend.mongoUri.secretRef.enabled`    | Use secret for MongoDB URI | `false`                |
| `backend.mongoUri.secretRef.secretName` | Secret name                | `""`                   |
| `backend.authz.enabled`                 | Enable RBAC                | `false`                |
| `backend.authz.emailHeader`             | Auth email header name     | `X-Auth-Request-Email` |
| `backend.opaqueIds.enabled`             | Enable opaque IDs          | `false`                |
| `backend.probes.liveness.enabled`       | Enable liveness probe      | `false`                |
| `backend.probes.readiness.enabled`      | Enable readiness probe     | `false`                |
| `backend.resources`                     | CPU/memory limits          | `{}`                   |

### Frontend

| Parameter                   | Description        | Default               |
| --------------------------- | ------------------ | --------------------- |
| `frontend.enabled`          | Enable frontend    | `true`                |
| `frontend.replicaCount`     | Number of replicas | `1`                   |
| `frontend.image.repository` | Image repository   | `mongodhara/frontend` |
| `frontend.image.tag`        | Image tag          | `""` (chart version)  |
| `frontend.resources`        | CPU/memory limits  | `{}`                  |

### Ingress

| Parameter                        | Description                                | Default                  |
| -------------------------------- | ------------------------------------------ | ------------------------ |
| `ingress.className`              | Ingress class (applies to all 4 ingresses) | `nginx`                  |
| `ingress.host`                   | Hostname (applies to all 4 ingresses)      | `mongodhara.company.com` |
| `ingress.tls.enabled`            | Enable TLS (applies to all 4 ingresses)    | `true`                   |
| `ingress.tls.secretName`         | TLS secret name                            | `mongodhara-tls`         |
| `ingress.frontend.enabled`       | Enable frontend ingress                    | `true`                   |
| `ingress.frontend.path`          | Frontend path                              | `/mdhara`                |
| `ingress.backend.enabled`        | Enable backend API ingress                 | `true`                   |
| `ingress.backend.path`           | Backend API path                           | `/mdhara/api`            |
| `ingress.gridfsUpload.enabled`   | Enable GridFS upload ingress               | `true`                   |
| `ingress.gridfsDownload.enabled` | Enable GridFS download ingress             | `true`                   |
| `ingress.auth.oauth.enabled`     | Enable OAuth (applies to all 4 ingresses)  | `false`                  |

See `values.yaml` for complete list of parameters including rate limiting and timeout annotations for each ingress.

## Upgrading

```bash
helm upgrade mongodhara ./helm-chart -f my-values.yaml
```

## Uninstalling

```bash
helm delete mongodhara
```

⚠️ **Note**: By default, the MongoDB database is NOT deleted. To cleanup:

- Set `backend.authz.databaseCleanup.enabled=true` before uninstall to drop the `mongodhara` database
- Or manually drop collections/database as needed

## Runtime Configuration

The frontend uses **SvelteKit public environment variables** for runtime configuration. This allows you to change configuration without rebuilding Docker images.

### How It Works

1. The `PUBLIC_AUTHZ_ENABLED` environment variable is automatically set based on `global.features.authz.enabled`
2. SvelteKit exposes this as `import.meta.env.PUBLIC_AUTHZ_ENABLED` in the frontend code
3. No runtime injection scripts needed - much simpler and more reliable

### Verifying Configuration

The authorization feature is controlled by the `PUBLIC_AUTHZ_ENABLED` environment variable:

- When `global.features.authz.enabled=true`: `PUBLIC_AUTHZ_ENABLED=true`
- When `global.features.authz.enabled=false`: `PUBLIC_AUTHZ_ENABLED=false`

### Changing Configuration

Simply update the Helm values and upgrade:

```bash
# Enable authorization
helm upgrade mongodhara . --set global.features.authz.enabled=true

# Disable authorization
helm upgrade mongodhara . --set global.features.authz.enabled=false
```

The pods will restart with the new configuration automatically.

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -l app.kubernetes.io/instance=mongodhara
```

### View Logs

```bash
# Backend
kubectl logs -f deployment/mongodhara-backend

# Frontend
kubectl logs -f deployment/mongodhara-frontend
```

### Port Forward for Local Testing

```bash
# Frontend (access at http://localhost:8080)
kubectl port-forward svc/mongodhara-mongodhara 8080:80

# Backend API (access at http://localhost:8000)
kubectl port-forward svc/mongodhara-mongodhara-services 8000:80
```

Note: Replace `mongodhara` with your release name if different.

### Common Issues

**Pods not starting**: Check MongoDB connection

```bash
kubectl logs deployment/mongodhara-mongodhara-services | grep -i mongo
```

**Ingress not working**: Verify NGINX ingress controller is running and check all 4 ingress resources

```bash
kubectl get ingress
kubectl describe ingress mongodhara-frontend
kubectl describe ingress mongodhara-backend
kubectl describe ingress mongodhara-gridfs-upload
kubectl describe ingress mongodhara-gridfs-download
```

**Rate limiting issues**: Check if requests are being throttled by inspecting ingress logs or adjust rate limits in `values.yaml` for specific ingress resources

**GridFS upload failures**: Check `gridfsUpload` ingress annotations for body size limits (default 100MB) and timeouts (default 600s)

**OAuth errors**: Check OAuth annotations in `ingress.auth.oauth.annotations` and ensure provider is accessible from cluster

## Support

- GitHub Issues: https://github.com/sensoumya/mongodhara/issues
- Documentation: https://github.com/sensoumya/mongodhara
