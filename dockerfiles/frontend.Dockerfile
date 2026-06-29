FROM node:26.4.0 AS builder

WORKDIR /app

COPY frontend/package*.json frontend/svelte.config.js frontend/tsconfig.json frontend/vite.config.ts ./
RUN npm install

COPY frontend/ .
RUN npm run build

FROM node:26.4.0-slim

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install --omit=dev

COPY --from=builder /app/build /app/build
COPY --from=builder /app/static /app/static

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/', (r) => process.exit(r.statusCode < 500 ? 0 : 1)).on('error', () => process.exit(1))"

ENV NODE_ENV=production

RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app && \
    chmod -R u+w /app/build
USER appuser

CMD ["node", "build/index.js"]
