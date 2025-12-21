"""Docker configuration generator."""

import logging

logger = logging.getLogger(__name__)


class DockerGenerator:
    """Generate Docker configuration files."""

    def generate_dockerfile(self, framework: str = "express") -> str:
        """Generate Dockerfile."""
        return '''# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./
COPY prisma ./prisma/

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Generate Prisma client
RUN npx prisma generate

# Build
RUN npm run build

# Production stage
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 app

# Copy built assets
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
COPY --from=builder /app/prisma ./prisma

USER app

EXPOSE 3000

CMD ["npm", "start"]
'''

    def generate_docker_compose(self, services: list[str] | None = None) -> str:
        """Generate docker-compose.yml."""
        services = services or ['db', 'redis']

        compose = '''version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "${PORT:-3000}:3000"
    environment:
      - NODE_ENV=${NODE_ENV:-development}
      - DATABASE_URL=postgresql://${DB_USER:-postgres}:${DB_PASSWORD:-postgres}@db:5432/${DB_NAME:-app}
      - JWT_SECRET=${JWT_SECRET:-change-me-in-production}
'''

        if 'redis' in services:
            compose += '''      - REDIS_URL=redis://redis:6379
'''

        compose += '''    depends_on:
'''
        if 'db' in services:
            compose += '''      db:
        condition: service_healthy
'''
        if 'redis' in services:
            compose += '''      redis:
        condition: service_started
'''

        compose += '''    networks:
      - app-network
    restart: unless-stopped

'''

        if 'db' in services:
            compose += '''  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
      POSTGRES_DB: ${DB_NAME:-app}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${DB_PORT:-5432}:5432"
    networks:
      - app-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

'''

        if 'redis' in services:
            compose += '''  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "${REDIS_PORT:-6379}:6379"
    networks:
      - app-network
    restart: unless-stopped

'''

        compose += '''networks:
  app-network:
    driver: bridge

volumes:
  postgres_data:
'''
        if 'redis' in services:
            compose += '''  redis_data:
'''

        return compose

    def generate_dockerignore(self) -> str:
        """Generate .dockerignore."""
        return '''# Dependencies
node_modules
npm-debug.log

# Build output
dist

# Environment files
.env
.env.*
!.env.example

# Git
.git
.gitignore

# IDE
.idea
.vscode
*.swp
*.swo

# Testing
coverage
.nyc_output

# Documentation
docs
*.md

# Docker
Dockerfile
docker-compose*.yml
.docker

# Misc
.DS_Store
Thumbs.db
'''

    def generate_nginx_config(self) -> str:
        """Generate nginx configuration for production."""
        return '''upstream api {
    server app:3000;
    keepalive 64;
}

server {
    listen 80;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip
    gzip on;
    gzip_types text/plain application/json application/javascript;

    # API proxy
    location /api {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 90s;
    }

    # Health check
    location /health {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
'''