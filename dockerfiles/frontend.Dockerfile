# Stage 1: Build the SvelteKit application
FROM node:20 AS builder

WORKDIR /app

# Copy package files to the working directory (fixed with trailing /)
COPY package*.json ./
RUN npm install

# Copy the rest of the application code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Create the runtime image
FROM node:20-slim

WORKDIR /app

# Copy package files for production dependencies (fixed with trailing /)
COPY package*.json ./
RUN npm install --production

# Copy the built application from the builder stage
COPY --from=builder /app/build /app/build

# Expose the port the app will run on
EXPOSE 3000

# Set environment variables
ENV NODE_ENV=production

# Create a non-root user and switch to it
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Command to run the application
CMD ["node", "build/index.js"]
