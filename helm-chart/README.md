# Mongodhara Helm Chart

This Helm chart deploys the Mongodhara application, a MongoDB admin interface with a FastAPI backend and Svelte frontend.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.2.0+

## Installing the Chart

To install the chart with the release name `my-mongodhara`:

```bash
helm install my-mongodhara ./helm-chart
```

## Uninstalling the Chart

To uninstall/delete the `my-mongodhara` deployment:

```bash
helm delete my-mongodhara
```

## Configuration

The following table lists the configurable parameters of the Mongodhara chart and their default values.

### Global Configuration

| Parameter                 | Description                                     | Default |
| ------------------------- | ----------------------------------------------- | ------- |
| `global.imageRegistry`    | Global Docker image registry                    | `""`    |
| `global.imagePullSecrets` | Global Docker registry secret names as an array | `[]`    |

### Backend Configuration

| Parameter                    | Description                           | Default                     |
| ---------------------------- | ------------------------------------- | --------------------------- |
| `backend.enabled`            | Enable backend deployment             | `true`                      |
| `backend.replicaCount`       | Number of backend replicas            | `1`                         |
| `backend.image.repository`   | Backend image repository              | `mongodhara/backend`        |
| `backend.image.pullPolicy`   | Backend image pull policy             | `IfNotPresent`              |
| `backend.image.tag`          | Backend image tag                     | `""`                        |
| `backend.service.type`       | Backend service type                  | `ClusterIP`                 |
| `backend.service.port`       | Backend service port                  | `80`                        |
| `backend.service.targetPort` | Backend container port                | `8000`                      |
| `backend.env[0].name`        | MongoDB URI environment variable name | `MONGO_URI`                 |
| `backend.env[0].value`       | MongoDB URI                           | `mongodb://localhost:27017` |

### Frontend Configuration

| Parameter                     | Description                            | Default               |
| ----------------------------- | -------------------------------------- | --------------------- |
| `frontend.enabled`            | Enable frontend deployment             | `true`                |
| `frontend.replicaCount`       | Number of frontend replicas            | `1`                   |
| `frontend.image.repository`   | Frontend image repository              | `mongodhara/frontend` |
| `frontend.image.pullPolicy`   | Frontend image pull policy             | `IfNotPresent`        |
| `frontend.image.tag`          | Frontend image tag                     | `""`                  |
| `frontend.service.type`       | Frontend service type                  | `ClusterIP`           |
| `frontend.service.port`       | Frontend service port                  | `80`                  |
| `frontend.service.targetPort` | Frontend container port                | `3000`                |
| `frontend.env[0].name`        | API base URL environment variable name | `REMOTE_API_BASE_URL` |
| `frontend.env[0].value`       | API base URL                           | `""`                  |

### Ingress Configuration

| Parameter                        | Description                        | Default            |
| -------------------------------- | ---------------------------------- | ------------------ |
| `ingress.enabled`                | Enable ingress controller resource | `true`             |
| `ingress.className`              | Ingress class name                 | `""`               |
| `ingress.annotations`            | Ingress annotations                | `{}`               |
| `ingress.hosts[0].host`          | Hostname for your service          | `mongodhara.local` |
| `ingress.hosts[0].paths[0].path` | Frontend path                      | `/mongodhara`      |
| `ingress.hosts[0].paths[1].path` | Backend API path                   | `/mongodharaapi`   |
| `ingress.tls`                    | Ingress TLS configuration          | `[]`               |

## Example Usage

### Basic Installation

```bash
helm install mongodhara ./helm-chart \\
  --set backend.env[0].value="mongodb://my-mongo:27017/mydb" \\
  --set frontend.env[0].value="http://my-domain.com/mongodharaapi"
```

### Installation with Custom Images

```bash
helm install mongodhara ./helm-chart \\
  --set backend.image.repository="myregistry/mongodhara-backend" \\
  --set backend.image.tag="v1.0.0" \\
  --set frontend.image.repository="myregistry/mongodhara-frontend" \\
  --set frontend.image.tag="v1.0.0"
```

### Installation with Ingress Configuration

```bash
helm install mongodhara ./helm-chart \\
  --set ingress.hosts[0].host="mongodhara.example.com" \\
  --set ingress.annotations."kubernetes\.io/ingress\.class"="nginx" \\
  --set ingress.annotations."cert-manager\.io/cluster-issuer"="letsencrypt-prod"
```

### Installation with Resource Limits

```bash
helm install mongodhara ./helm-chart \\
  --set backend.resources.limits.cpu="500m" \\
  --set backend.resources.limits.memory="512Mi" \\
  --set frontend.resources.limits.cpu="200m" \\
  --set frontend.resources.limits.memory="256Mi"
```

## Upgrading

To upgrade the chart:

```bash
helm upgrade mongodhara ./helm-chart
```

## Values File Example

Create a `my-values.yaml` file:

```yaml
backend:
  image:
    repository: myregistry/mongodhara-backend
    tag: v1.0.0
  env:
    - name: MONGO_URI
      value: "mongodb://mongo-service:27017/production"
  resources:
    limits:
      cpu: 500m
      memory: 512Mi
    requests:
      cpu: 100m
      memory: 128Mi

frontend:
  image:
    repository: myregistry/mongodhara-frontend
    tag: v1.0.0
  env:
    - name: REMOTE_API_BASE_URL
      value: "https://api.example.com/mongodharaapi"
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
    - host: mongodhara.example.com
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
        - mongodhara.example.com
```

Then install with:

```bash
helm install mongodhara ./helm-chart -f my-values.yaml
```

## Troubleshooting

### Check pod status

```bash
kubectl get pods -l app.kubernetes.io/instance=mongodhara
```

### View logs

```bash
kubectl logs -f deployment/mongodhara-backend
kubectl logs -f deployment/mongodhara-frontend
```

### Port forwarding for local testing

```bash
# Frontend
kubectl port-forward svc/mongodhara-frontend 8080:80

# Backend
kubectl port-forward svc/mongodhara-backend 8000:80
```
