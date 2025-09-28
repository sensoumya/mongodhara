<!-- Favicon and Title -->
<p><img src="frontend/static/favicon.ico" alt="favicon" width="48" height="48" style="vertical-align:middle;margin-right:12px;" /> <span style="font-size:2.5em;font-weight:bold;vertical-align:middle;">mongoDhārā</span></p>

---

An intuitive interface to visualize and interact with MongoDB databases.  
Built with Svelte on the frontend and FastAPI on the backend, mongoDhārā provides a streamlined, modern experience for exploring your MongoDB data visually.

---
![CodeQL](https://github.com/sensoumya/mongodhara/actions/workflows/codeql.yml/badge.svg)

---

## Tech Stack

- **Frontend:** Svelte
- **Backend:** FastAPI (Python)
- **Database:** MongoDB (visualized, but not included)
- **Containerization:** Docker
- **Deployment:** Kubernetes with Helm charts supported

---

## 🚀 Quick Start with Helm

The easiest way to deploy mongoDhārā is using the included Helm chart:

```bash
# Clone the repository
git clone <your-repo-url>
cd mongodhara

# Deploy with default configuration
helm install mongodhara ./helm-chart

# Or deploy with custom MongoDB URI
helm install mongodhara ./helm-chart \
  --set backend.env[0].value="mongodb://your-mongo-host:27017/yourdb"
```

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

| Parameter                      | Description                                       | Default               |
| ------------------------------ | ------------------------------------------------- | --------------------- |
| `frontend.enabled`             | Enable frontend deployment                        | `true`                |
| `frontend.replicaCount`        | Number of frontend replicas                       | `1`                   |
| `frontend.image.repository`    | Frontend image repository                         | `mongodhara/frontend` |
| `frontend.image.tag`           | Frontend image tag (defaults to Chart.AppVersion) | `""`                  |
| `frontend.image.pullPolicy`    | Image pull policy                                 | `IfNotPresent`        |
| `frontend.service.type`        | Service type                                      | `ClusterIP`           |
| `frontend.service.port`        | Service port                                      | `80`                  |
| `frontend.service.targetPort`  | Container port                                    | `3000`                |
| `frontend.env[0].name`         | API base URL environment variable                 | `REMOTE_API_BASE_URL` |
| `frontend.env[0].value`        | Backend API URL                                   | `""`                  |
| `frontend.resources`           | CPU/Memory resource requests and limits           | `{}`                  |
| `frontend.autoscaling.enabled` | Enable horizontal pod autoscaler                  | `false`               |

#### Ingress Configuration

| Parameter                | Description         | Default            |
| ------------------------ | ------------------- | ------------------ |
| `ingress.enabled`        | Enable ingress      | `true`             |
| `ingress.className`      | Ingress class name  | `""`               |
| `ingress.annotations`    | Ingress annotations | `{}`               |
| `ingress.hosts[0].host`  | Hostname            | `mongodhara.local` |
| `ingress.hosts[0].paths` | Path configurations | See values.yaml    |
| `ingress.tls`            | TLS configuration   | `[]`               |

### Management Commands

```bash
# View current releases
helm list

# Upgrade deployment
helm upgrade mongodhara ./helm-chart -f production-values.yaml

# Check deployment status
helm status mongodhara

# View deployment history
helm history mongodhara

# Rollback to previous version
helm rollback mongodhara

# Uninstall
helm uninstall mongodhara

# Dry run (validate without installing)
helm install mongodhara ./helm-chart --dry-run

# Generate manifests without installing
helm template mongodhara ./helm-chart -f production-values.yaml
```

### Troubleshooting

#### Check Pod Status

```bash
kubectl get pods -l app.kubernetes.io/instance=mongodhara
kubectl describe pod <pod-name>
```

#### View Logs

```bash
# Backend logs
kubectl logs -f deployment/mongodhara-backend

# Frontend logs
kubectl logs -f deployment/mongodhara-frontend

# Follow logs from all pods
kubectl logs -f -l app.kubernetes.io/instance=mongodhara --all-containers=true
```

#### Debug Services

```bash
# Check services
kubectl get svc -l app.kubernetes.io/instance=mongodhara

# Check ingress
kubectl get ingress -l app.kubernetes.io/instance=mongodhara
kubectl describe ingress mongodhara
```

#### Port Forward for Local Testing

```bash
# Frontend
kubectl port-forward svc/mongodhara-frontend 8080:80

# Backend
kubectl port-forward svc/mongodhara-backend 8000:80

# Access frontend at http://localhost:8080
# Access backend at http://localhost:8000
```

---

## 🐳 Docker Setup (Alternative)

If you prefer Docker without Kubernetes:

### Frontend

```bash
docker build -f dockerfiles/frontend.Dockerfile -t mongodhara-frontend .
docker run -p 3000:3000 mongodhara-frontend
```

### Backend

```bash
docker build -f dockerfiles/backend.Dockerfile -t mongodhara-backend .
docker run -p 8000:8000 -e MONGO_URI="mongodb://host.docker.internal:27017" mongodhara-backend
```

---

## 🛠️ Local Development

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure

```
mongodhara/
├── backend/                    # FastAPI backend
│   ├── main.py
│   ├── requirements.txt
│   └── ...
├── frontend/                   # Svelte frontend
│   ├── src/
│   ├── package.json
│   └── ...
├── helm-chart/                 # Helm chart for Kubernetes
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── templates/
│   └── README.md
├── dockerfiles/               # Docker build files
│   ├── backend.Dockerfile
│   └── frontend.Dockerfile
└── README.md
```

---

## 🔧 Environment Variables

### Backend

- `MONGO_URI`: MongoDB connection string
- `LOG_LEVEL`: Logging level (default: INFO)

### Frontend

- `REMOTE_API_BASE_URL`: Backend API base URL

---

## 📊 Monitoring and Scaling

The Helm chart includes support for:

- **Horizontal Pod Autoscaling (HPA)**: Automatically scale based on CPU/memory usage
- **Resource Limits**: Prevent resource exhaustion
- **Health Checks**: Liveness and readiness probes
- **Service Accounts**: Proper RBAC setup

Enable autoscaling:

```yaml
backend:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
```

---

## 🛡️ Security

- Service accounts created for each component
- Security contexts configurable
- Image pull secrets support
- TLS/SSL support via ingress
- Network policies can be added as needed

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Helm: `helm template test ./helm-chart`
5. Submit a pull request

---

## ⚖️ Legal Notice

mongoDhārā is an independent, third-party application designed to provide an intuitive interface for MongoDB databases.

**Trademark Notice**: MongoDB® is a registered trademark of MongoDB, Inc. This project is not affiliated with, endorsed by, or sponsored by MongoDB, Inc. All MongoDB-related trademarks and logos are the property of their respective owners.

**Disclaimer**: This software is provided "as is" without warranty of any kind. Use at your own risk.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
