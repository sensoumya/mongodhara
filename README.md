# mongoDhārā

An intuitive interface to visualize and interact with MongoDB databases.  
Built with Svelte on the frontend and FastAPI on the backend, mongoDhārā provides a streamlined, modern experience for exploring your MongoDB data visually.

---

## Tech Stack

- **Frontend:** Svelte  
- **Backend:** FastAPI (Python)  
- **Database:** MongoDB (visualized, but not included)  
- **Containerization:** Docker  
- **Deployment:** Kubernetes with Helm charts supported  

---

## Setup Instructions

### Frontend

The Dockerfile in the `dockerfiles/frontend.Dockerfile` handles compilation and image building of the Svelte frontend.

To build and run locally, use Docker:

```bash
docker build -f dockerfiles/frontend.Dockerfile -t mongoDhara-frontend .
docker run -p 3000:3000 mongoDhara-frontend
```

### Backend

Standard Python setup applies. The Dockerfile is located at `dockerfiles/backend.Dockerfile`.

To run locally without Docker:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

To build and run backend Docker image:

```bash
docker build -f dockerfiles/backend.Dockerfile -t mongoDhara-backend .
docker run -p 8000:8000 mongoDhara-backend
```

---

## Build and Deploy

Build and deploy the project the usual way:

- Use Docker to build images for frontend and backend  
- Deploy to Kubernetes using the Helm chart in the `helm/` directory  
- Kubernetes manifests are also available under `k8s/` if you prefer manual deployment  

---

## Usage

Once deployed, open your browser and navigate to the frontend URL.  
The interface allows you to connect to your MongoDB instance, explore collections, and visualize data in a user-friendly way.

---

## Helm Deployment Guidelines

To deploy mongoDhārā using Helm:

1. **Ensure you have Helm installed** on your machine. See [Helm installation guide](https://helm.sh/docs/intro/install/).

2. **Build and push your Docker images** for the frontend and backend to your container registry.

3. **Update the Helm chart `values.yaml`** (located at `helm/your-app/values.yaml`) to point to your image repositories and tags:

   ```yaml
   backend:
     image:
       repository: your-registry/mongoDhara-backend
       tag: latest

   frontend:
     image:
       repository: your-registry/mongoDhara-frontend
       tag: latest
   ```

4. **Install or upgrade the Helm release** with:

   ```bash
   helm upgrade --install mongoDhara-release helm/your-app \
     --namespace mongoDhara-namespace \
     --create-namespace
   ```

5. **Verify the deployment**:

   ```bash
   kubectl get pods -n mongoDhara-namespace
   kubectl get svc -n mongoDhara-namespace
   ```

6. **Access the frontend service** using the external IP or ingress configured in your cluster.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
