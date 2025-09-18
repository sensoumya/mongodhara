![mongoDhārā Logo](frontend/static/favicon.ico)  
# mongoDhārā  

An intuitive interface to visualize and interact with MongoDB databases.  
Built with Svelte on the frontend and FastAPI on the backend, mongoDhārā provides a streamlined, modern experience for exploring your MongoDB data visually.

---

## 🚀 Tech Stack

- **Frontend:** Svelte  
- **Backend:** FastAPI (Python)  
- **Database:** MongoDB (visualized, but not included)  
- **Containerization:** Docker  
- **Deployment:** Kubernetes with Helm charts supported  

---

## 🛠 Setup Instructions

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

## 📦 Build and Deploy

Build and deploy the project the usual way:  
- Use Docker to build images for frontend and backend  
- Kubernetes manifests are available under `k8s/` if you prefer manual deployment  

---

## 🔒 Authentication at Ingress with OAuth2 Proxy  
Add these annotations to your ingress resources for UI and only the auth-url annotation for API:  
```yaml
nginx.ingress.kubernetes.io/auth-url: "https://<oauth-proxy-host>/oauth2/auth"
nginx.ingress.kubernetes.io/auth-signin: "https://<oauth-proxy-host>/oauth2/start?rd=$escaped_request_uri"
```

---

## 🌐 Usage  

Once deployed, open your browser and navigate to `<dns>/mongodhara`.  
The interface allows you to connect to your MongoDB instance, explore collections, and visualize data in a user-friendly way.  

---

## 📜 License  

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
