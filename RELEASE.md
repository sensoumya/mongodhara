# Release Notes

## Version: v2.1.0

### Major Features & Updates

- *GridFS Support Added*
  - The backend now supports MongoDB GridFS for file storage and retrieval.
  - New endpoints for uploading, downloading, listing, and deleting files using GridFS.

- *Helm Chart Integration*
  - Added comprehensive Helm chart for Kubernetes deployment.
  - Supports custom naming, ingress configuration, rate limiting, and CORS.
  - Simplifies deployment and scaling in cloud environments.

- *Production-Ready Backend Server*
  - Updated backend to run with Gunicorn using Uvicorn workers for improved performance and reliability.
  - Includes auto-scaling worker configuration and robust server lifecycle management.

### Other Improvements

- Enhanced documentation and code organization.
- Improved security by running containers as non-root users.
- Added rate limiting and CORS configuration at ingress level.

---

For upgrade instructions and migration notes, see the project README.
