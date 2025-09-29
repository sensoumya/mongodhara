<h1 style="font-size:3.2em; font-weight:800; margin-top: 0.5em; margin-bottom: 0.5em;">
  <span style="
    font-size:0.85em;
    opacity:0.8;
    color:black;
    background:transparent;
    text-shadow:
      -1px -1px 0 white,
       1px -1px 0 white,
      -1px  1px 0 white,
       1px  1px 0 white;
  ">
    mongo
  </span>
  <span style="color:white; background:black; padding:6px 14px; border-radius:6px;">
    Dhārā<span style="display:inline-block; transform: skewX(-10deg);">!</span>
  </span>
</h1>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Node.js](https://img.shields.io/badge/node.js-16+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117+-009688.svg)](https://fastapi.tiangolo.com/)
[![Svelte](https://img.shields.io/badge/Svelte-4+-ff3e00.svg)](https://svelte.dev/)
[![MongoDB](https://img.shields.io/badge/MongoDB-Compatible-47A248.svg)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5.svg)](https://kubernetes.io/)

_MongoDB management made elegant, fast, and intuitive._

**mongoDhārā** is a blazing-fast web UI for MongoDB — built with Svelte & FastAPI.  
Manage databases, collections, documents, and GridFS visually with zero overhead.

---

## 📖 Table of Contents

- [✨ Key Features](#-key-features)
- [🚀 Quick Start with Helm](#-quick-start-with-helm)
- [📦 Helm Chart Deployment](#-helm-chart-deployment)
- [🐳 Build & Push Docker Images](#-build--push-docker-images)
- [🧑‍💻 Local Development](#-local-development)
- [📁 Project Structure](#-project-structure)
- [🔧 Environment Variables](#-environment-variables)
- [📊 Monitoring and Scaling](#-monitoring-and-scaling)
- [🛡️ Security](#️-security)
- [🤝 Contributing](#-contributing)
- [⚖️ Legal Notice](#-legal-notice)
- [📄 License](#-license)

---

## 💡 Why mongoDhārā?

- Designed for speed — near-raw MongoDB performance with minimal overhead
- Clean, modern UI for effortless data exploration and management
- Full control: databases, collections, documents, GridFS, and bulk operations
- Scalable deployment with Kubernetes and Helm support
- Open-source and developer-friendly

---

## ✨ **Key Features**

### ⚡ **High-Performance UI**

- Near-raw MongoDB speed with minimal overhead (PyMongo-powered)
- Optimized queries with fast pagination and filtering
- Responsive layout with light/dark theme support
- Real-time status updates and notifications
- Intuitive navigation with breadcrumbs and global search

### 🗂️ **Database, Collection & Document Management**

- Create, rename, and delete databases and collections
- Browse, query, and edit documents with a rich JSON editor
- Advanced query builder with filtering, sorting, and aggregation
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

---

## 🚀 Quick Start with Helm

The easiest way to deploy mongoDhārā is using the included Helm chart:

```bash
# Clone the repository
git clone <your-repo-url>
cd mongodhara

# Deploy with custom MongoDB URI and images
helm install mongodhara ./helm-chart \
  --set backend.image.repository=mongodhara/backend \
  --set backend.image.tag=1.0.0 \
  --set frontend.image.repository=mongodhara/frontend \
  --set frontend.image.tag=1.0.0 \
  --set backend.env[0].value="mongodb://your-mongo-host:27017/yourdb"
```

> 💡 **For production deployments and advanced configuration options, see the detailed Helm Chart Deployment section below.**

---

## 📦 Helm Chart Deployment

### Prerequisites

- Kubernetes cluster (1.16+)
- Helm 3.2.0+
- Docker images pushed to a registry (or use default placeholder images)

### Installation Options

#### 1. Basic Installation

```bash
helm install mongodhara ./helm-chart
```

This deploys with default settings:

- Backend: `mongodhara/backend:1.0.0`
- Frontend: `mongodhara/frontend:1.0.0`
- Ingress: `mongodhara.local`
- MongoDB URI: `mongodb://localhost:27017`

#### 2. Production Installation with Custom Values

Create a `production-values.yaml`:

```yaml
# Production configuration
backend:
  replicaCount: 3
  image:
    repository: your-registry.com/mongodhara-backend
    tag: v1.2.0
  env:
    - name: MONGO_URI
      value: "mongodb://prod-mongo-cluster:27017/production"
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 128Mi
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

frontend:
  replicaCount: 2
  image:
    repository: your-registry.com/mongodhara-frontend
    tag: v1.2.0
  env:
    - name: REMOTE_API_BASE_URL
      value: "https://api.yourdomain.com/mongodharaapi"
  resources:
    limits:
      cpu: 200m
      memory: 256Mi
    requests:
      cpu: 50m
      memory: 64Mi

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: mongodhara.yourdomain.com
      paths:
        - path: /mongodhara
          pathType: Prefix
          backend: frontend
        - path: /mongodharaapi
          pathType: Prefix
          backend: backend
  tls:
    - secretName: mongodhara-tls
      hosts:
        - mongodhara.yourdomain.com
```

Deploy with:

```bash
helm install mongodhara ./helm-chart -f production-values.yaml
```

#### 3. Development Installation with Port Forwarding

```bash
# Install without ingress for local development
helm install mongodhara-dev ./helm-chart \
  --set ingress.enabled=false \
  --set backend.env[0].value="mongodb://docker.for.mac.localhost:27017/dev"

# Port forward to access services
kubectl port-forward svc/mongodhara-dev-frontend 8080:80 &
kubectl port-forward svc/mongodhara-dev-backend 8000:80 &

# Access at http://localhost:8080
```

### Configuration Options

#### Global Settings

| Parameter                 | Description                         | Default |
| ------------------------- | ----------------------------------- | ------- |
| `global.imageRegistry`    | Global Docker image registry        | `""`    |
| `global.imagePullSecrets` | Global Docker registry secret names | `[]`    |

#### Backend Configuration

| Parameter                                            | Description                                      | Default                     |
| ---------------------------------------------------- | ------------------------------------------------ | --------------------------- |
| `backend.enabled`                                    | Enable backend deployment                        | `true`                      |
| `backend.replicaCount`                               | Number of backend replicas                       | `1`                         |
| `backend.image.repository`                           | Backend image repository                         | `mongodhara/backend`        |
| `backend.image.tag`                                  | Backend image tag (defaults to Chart.AppVersion) | `""`                        |
| `backend.image.pullPolicy`                           | Image pull policy                                | `IfNotPresent`              |
| `backend.service.type`                               | Service type                                     | `ClusterIP`                 |
| `backend.service.port`                               | Service port                                     | `80`                        |
| `backend.service.targetPort`                         | Container port                                   | `8000`                      |
| `backend.env[0].name`                                | MongoDB URI environment variable                 | `MONGO_URI`                 |
| `backend.env[0].value`                               | MongoDB connection string                        | `mongodb://localhost:27017` |
| `backend.resources`                                  | CPU/Memory resource requests and limits          | `{}`                        |
| `backend.autoscaling.enabled`                        | Enable horizontal pod autoscaler                 | `false`                     |
| `backend.autoscaling.minReplicas`                    | Minimum number of replicas                       | `1`                         |
| `backend.autoscaling.maxReplicas`                    | Maximum number of replicas                       | `100`                       |
| `backend.autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization                           | `80`                        |

#### Frontend Configuration

| Parameter                   | Description                                       | Default               |
| --------------------------- | ------------------------------------------------- | --------------------- |
| `frontend.enabled`          | Enable frontend deployment                        | `true`                |
| `frontend.replicaCount`     | Number of frontend replicas                       | `1`                   |
| `frontend.image.repository` | Frontend image repository                         | `mongodhara/frontend` |
| `frontend.image.tag`        | Frontend image tag (defaults to Chart.AppVersion) | `""`                  |
| `frontend.image.pullPolicy` | Image pull policy                                 | `IfNotPresent`        |
| `frontend.service.type`     | Service type                                      | `ClusterIP`           |
| `frontend.service.port`     | Service port                                      | `80`                  |
| `frontend.env[0].name`      | API base URL environment variable                 | `REMOTE_API_BASE_URL` |
| `frontend.env[0].value`     | Backend API URL                                   | `http://backend:8000` |
| `frontend.resources`        | CPU/Memory resource requests and limits           | `{}`                  |

#### Ingress Configuration

| Parameter             | Description                 | Default |
| --------------------- | --------------------------- | ------- |
| `ingress.enabled`     | Enable ingress controller   | `false` |
| `ingress.className`   | Ingress class name          | `""`    |
| `ingress.annotations` | Annotations for ingress     | `{}`    |
| `ingress.hosts`       | List of hostnames and paths | `[]`    |
| `ingress.tls`         | TLS configuration           | `[]`    |

---

## 🐳 Build & Push Docker Images

Build and push images for backend and frontend:

```bash
# Backend
docker build -t your-registry.com/mongodhara/backend:1.0.0 ./backend
docker push your-registry.com/mongodhara/backend:1.0.0

# Frontend
docker build -t your-registry.com/mongodhara/frontend:1.0.0 ./frontend
docker push your-registry.com/mongodhara/frontend:1.0.0
```

Replace `your-registry.com` with your Docker registry URL.

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
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Setup Frontend

```bash
cd frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173` (or the port indicated).

---

## 📁 Project Structure

```plaintext
mongodhara/
├── backend/               # FastAPI backend source code
│   ├── main.py            # App entry point
│   ├── api/               # API endpoints and routes
│   ├── models/            # Pydantic models & schemas
│   └── db/                # MongoDB access & utilities
├── frontend/              # Svelte frontend source code
│   ├── src/               # Svelte components & pages
│   ├── static/            # Static assets (favicon, images)
│   └── vite.config.js     # Vite build config
├── helm-chart/            # Helm chart for Kubernetes deployment
│   ├── templates/         # K8s manifests templates
│   ├── values.yaml        # Default chart values
│   └── Chart.yaml         # Chart metadata
├── README.md              # This documentation
└── LICENSE                # License info
```

---

## 🔧 Environment Variables

| Variable              | Description                       | Default                     |
| --------------------- | --------------------------------- | --------------------------- |
| `MONGO_URI`           | MongoDB connection string         | `mongodb://localhost:27017` |
| `REMOTE_API_BASE_URL` | Backend API base URL for frontend | `http://localhost:8000`     |

---

## 📊 Monitoring and Scaling

- Configure resource limits and requests in Helm values
- Enable Horizontal Pod Autoscaler (HPA) for backend for CPU-based scaling
- Use Kubernetes native monitoring tools like Prometheus + Grafana
- Leverage logging (e.g., Fluentd, EFK stack) for production debugging

---

## 🛡️ Security

- Use TLS with Ingress for secure connections
- Configure authentication and authorization on the backend (future enhancement)
- Sanitize and validate all incoming requests
- Use network policies to restrict pod communication as needed

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please adhere to the coding style and write clear commit messages.

---

## ⚖️ Legal Notice

This project is **not affiliated with, endorsed by, or sponsored by MongoDB, Inc.**  
**MongoDB®** is a registered trademark of **MongoDB, Inc.**  
All product names, logos, and brands are property of their respective owners. Use of these names, trademarks, and brands does not imply endorsement.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

Made with ❤️ by the mongoDhārā Team

---
