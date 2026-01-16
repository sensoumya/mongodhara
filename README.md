![Mongo Dhārā Logo](./media/logo.png)

---

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CodeQL](https://github.com/sensoumya/mongodhara/actions/workflows/codeql.yml/badge.svg)](https://github.com/sensoumya/mongodhara/actions/workflows/codeql.yml)
[![Trivy Security Scan](https://github.com/sensoumya/mongodhara/actions/workflows/trivy.yml/badge.svg)](https://github.com/sensoumya/mongodhara/actions/workflows/trivy.yml)
[![Dependabot Updates](https://github.com/sensoumya/mongodhara/actions/workflows/dependabot/dependabot-updates/badge.svg)](https://github.com/sensoumya/mongodhara/actions/workflows/dependabot/dependabot-updates)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117+-009688.svg)](https://fastapi.tiangolo.com/)
[![Svelte](https://img.shields.io/badge/Svelte-5.0+-ff3e00.svg)](https://svelte.dev/)

_MongoDB management made elegant, fast, and intuitive._

**mongoDhārā** is a blazing-fast web UI for MongoDB — built with Svelte & FastAPI.  
Manage databases, collections, documents, and GridFS visually with zero overhead.

---

## 📖 Table of Contents

- [💡 Why mongoDhārā?](#-why-mongodhārā)
- [✨ Key Features](#-key-features)
- [🚀 Quick Start](#-quick-start)
- [🧑‍💻 Local Development](#-local-development)
- [� Docker Images](#-docker-images)
- [🔧 Configuration](#-configuration)
- [🛡️ Security](#️-security)
- [🤝 Contributing](#-contributing)
- [⚖️ Legal Notice](#️-legal-notice)
- [📄 License](#-license)

---

## 💡 Why mongoDhārā?

**mongoDhārā** bridges the gap between raw MongoDB power and intuitive usability — without compromise.

### At a Glance

| Feature                    | **mongoDhārā**                                                  | **Typical Web-Based Tools (e.g., Mongo Express)** |
| :------------------------- | :-------------------------------------------------------------- | :------------------------------------------------ |
| **Performance**            | ✅ Near-native MongoDB driver with optimized async I/O          | ⚠️ Varies; often less efficient                   |
| **GridFS Support**         | ✅ Full streaming read/write with chunking.                     | ⚠️ Limited to small file uploads                  |
| **Query Builder**          | ✅ Context-aware autocomplete for operators, fields, and values | ⚠️ Basic JSON/text input                          |
| **Enterprise Security**    | ✅ AES-GCM encrypted resource IDs and granular RBAC             | ⚠️ Minimal access control, exposed ObjectIDs      |
| **Authentication**         | ✅ OAuth2/OIDC proxy integration and custom providers           | ⚠️ Basic HTTP authentication, DIY OAuth           |
| **Audit Logging**          | ✅ Built-in audit trails with TTL-based retention               | ❌ Rarely available or externalized               |
| **Kubernetes Integration** | ✅ Production-ready Helm charts with autoscaling (HPA)          | ⚠️ Basic container images, manual setup           |
| **User Interface**         | ✅ Modern Svelte-based UI, responsive with dark mode            | ⚠️ Often legacy or inconsistent                   |

### Core Strengths

- **Blazing Fast**: Near-native MongoDB performance with direct driver access — no abstraction overhead
- **Production-Ready Security**: Built-in RBAC, audit logging, and encrypted resource IDs for enterprise deployments
- **Developer Experience**: Intelligent query builder with 50+ operator autocomplete, real-time field discovery, and smart templates
- **Kubernetes-Native**: Helm charts with autoscaling, health checks, and production-grade configurations
- **Zero Lock-in**: Open-source MIT license, standard MongoDB wire protocol, deploy anywhere

---

## ✨ **Key Features**

### 🔐 **Security & Enterprise Features**

- **RBAC Authorization**: Role-based access control with granular per-database permissions
- **Opaque IDs**: AES-GCM encrypted resource identifiers to prevent enumeration attacks
- **Audit Logging**: Comprehensive audit trail of all operations stored in MongoDB
- **Configurable Authentication**: Support for various OAuth proxies and authentication systems
- **System Database Protection**: Built-in safeguards against accidental system database modifications

### ⚡ **High-Performance UI**

- Near-native MongoDB speed with minimal overhead
- Optimized queries with fast pagination and filtering
- Responsive layout with light/dark theme support
- Real-time status updates and notifications
- Intuitive navigation with breadcrumbs and global search

### 🗂️ **Database, Collection & Document Management**

- Create, rename, and delete databases and collections
- Browse, query, and edit documents with a rich JSON editor
- **Context-Aware Query Builder**: Streamlines query writing with helpful suggestions:
  - **@ Operator Autocomplete**: Quickly inserts 50+ MongoDB operators (comparison, logical, array, geospatial) with convenient cursor placement
  - **/ Field Name Autocomplete**: Suggests actual field names from your collections in real-time
  - **# Value Helpers**: Provides quick access to common values (DateTime ranges, null, booleans, UUIDs, empty arrays/objects)
  - **Smart Templates**: Inserts pre-defined query patterns with placeholders and cursor positioning
  - **Real-time Validation**: Checks query syntax and structure as you type
  - **Column Pinning**: Pin multiple columns to stay visible while scrolling — persists across sessions with configurable limits
- Full CRUD support with bulk import/export of documents (JSON)
- Run large-scale bulk operations with progress and error tracking
- MongoDB-compliant naming and validation

### 📁 **GridFS File Storage**

- Upload, download, and manage files with GridFS
- Search files by name or metadata
- Create and manage multiple storage buckets

### 🧾 **Rich JSON Editing**

- Syntax-highlighted editor with real-time validation
- Inline error detection and formatting
- Auto-format and schema assistance
- DateTime helpers for quick date range queries

---

## 🚀 Quick Start

### Kubernetes/Helm Deployment

The easiest way to deploy mongoDhārā is using the included Helm chart:

```bash
# Clone the repository
git clone <your-repo-url>
cd mongodhara

# Deploy with custom MongoDB URI and images
helm install mongodhara ./helm-chart \
  --set backend.image.repository=mongodhara/api \
  --set backend.image.tag=1.0.0 \
  --set frontend.image.repository=mongodhara/web \
  --set frontend.image.tag=1.0.0 \
  --set backend.env[0].value="mongodb://your-mongo-host:27017/yourdb"
```

> 💡 **For production deployments and advanced configuration options, see the [Helm Chart README](helm-chart/README.md).**

---

## 🐳 Docker Images

Build and push Docker images:

```bash
# Backend
docker build -f dockerfiles/backend.Dockerfile -t your-registry.com/mongodhara/api:1.0.0 .
docker push your-registry.com/mongodhara/api:1.0.0

# Frontend
docker build -f dockerfiles/frontend.Dockerfile -t your-registry.com/mongodhara/web:1.0.0 .
docker push your-registry.com/mongodhara/web:1.0.0
```

---

## 📦 Published Packages

After publishing (triggered by pushes to `release/**` branches), you can use the pre-built artifacts from GitHub Container Registry (GHCR).

### Helm Chart

Install the published Helm chart directly from GHCR:

```bash
# Install the latest version
helm install my-mongodhara oci://ghcr.io/sensoumya/mongodhara

# Or install a specific version
helm install my-mongodhara oci://ghcr.io/sensoumya/mongodhara --version <chart-version>
```

> 📋 **View Packages**: [GitHub Packages](https://github.com/sensoumya/mongodhara/pkgs/container/mongodhara)

### Docker Images

Pull the published Docker images:

```bash
# Backend API
docker pull ghcr.io/sensoumya/mongodhara/api:<branch>-<short-sha>

# Frontend Web UI
docker pull ghcr.io/sensoumya/mongodhara/web:<branch>-<short-sha>
```

> 📋 **View Images**: [API Package](https://github.com/sensoumya/mongodhara/pkgs/container/mongodhara%2Fapi) | [Web Package](https://github.com/sensoumya/mongodhara/pkgs/container/mongodhara%2Fweb)

---

## 🧑‍💻 Local Development

### Prerequisites

- Python 3.9+
- Node.js 16+
- MongoDB server running locally

### Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app/main.py  # Development server with auto-reload
```

### Setup Frontend

```bash
cd frontend
npm install
npm run dev  # Opens at http://localhost:5173
```

---

## 🔧 Configuration

**Detailed configuration guides:**

- **[Helm Chart](helm-chart/README.md)**: Kubernetes deployment, security features, scaling
- **[Backend](backend/README.md)**: Environment variables, RBAC, opaque IDs, audit logging

---

## 🛡️ Security

### Production Security Checklist

- ✅ Use TLS/HTTPS with valid certificates (Ingress + cert-manager)
- ✅ Enable `ENABLE_AUTHZ=true` and configure user permissions
- ✅ Enable `ENABLE_OPAQUE_IDS=true` to prevent resource enumeration
- ✅ Configure OAuth proxy at ingress level (oauth2-proxy, Authelia, etc.)
- ✅ Enable `global.features.auditLogging.enabled=true` for compliance tracking
- ✅ Use network policies to restrict pod-to-pod communication
- ✅ Configure strong MongoDB authentication and encryption in transit
- ✅ Set appropriate resource limits and enable HPA for scaling
- ✅ Regularly review audit logs and monitor for anomalies

**Built-in protections:** RBAC with per-database permissions, AES-GCM encrypted resource IDs, system database write blocks (`admin`, `local`, `config`, `mongodhara`), TTL-based audit retention (365 days)

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit with clear messages (`git commit -m 'Add amazing feature'`)
4. Push and open a Pull Request

---

## ⚖️ Legal Notice

This project is **not affiliated with, endorsed by, or sponsored by MongoDB, Inc.**

**MongoDB®** is a registered trademark of **MongoDB, Inc.** All product names, logos, and brands are property of their respective owners. Use of these names, trademarks, and brands does not imply endorsement.

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

Made with ❤️ by the [Soumya Sen](https://github.com/sensoumya)
