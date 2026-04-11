# Pin to a specific patch for reproducible builds.
# Update this digest/tag after verifying: docker pull node:24 && docker inspect node:24
# Stage 1: Build the SvelteKit application
FROM node:24.4.0 AS builder

WORKDIR /app

# Copy package files and config files needed for prepare script
COPY frontend/package*.json frontend/svelte.config.js frontend/tsconfig.json frontend/vite.config.ts ./
RUN npm install

# Copy the rest of the application code
COPY frontend/ .

# Build the application
RUN npm run build

# Stage 2: Create the runtime image
FROM node:24.4.0-slim

WORKDIR /app

# Copy package files for production dependencies (fixed with trailing /)
COPY frontend/package*.json ./
RUN npm install --omit=dev

# Copy the built application from the builder stage
COPY --from=builder /app/build /app/build

# Copy static files
COPY --from=builder /app/static /app/static

# Expose the port the app will run on
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production

# Create a non-root user and switch to it
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app && \
    chmod -R u+w /app/build
USER appuser

CMD ["node", "build/index.js"]
