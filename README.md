# FORGE - AI-Powered Backend Code Generation System

## Overview

FORGE is a powerful AI system that analyzes frontend code and automatically generates production-ready backend code in 8+ frameworks with 4 database options. It also provides code review and debugging capabilities for existing backend code.

## Key Capabilities

| Capability | Description |
|------------|-------------|
| **Frontend Analysis** | Parse React/Vue/Angular to extract API calls, forms, types, auth patterns |
| **Backend Generation** | Generate complete backend code in your choice of framework and database |
| **Code Review** | Review existing backend code for issues, patterns, and best practices |
| **Debugging** | Analyze and debug backend code issues |
| **Semantic Search** | Vector-based code search with embeddings |
| **Interactive Chat** | Natural language interaction with your codebase |

## Supported Technologies

### Backend Frameworks
- Express.js (TypeScript/Node.js)
- NestJS (TypeScript/Node.js)
- FastAPI (Python)
- Django (Python)
- Flask (Python)
- Gin (Go)
- Spring Boot (Java)
- .NET Core (C#)

### Databases
- PostgreSQL
- MySQL
- SQLite
- MongoDB

### Generated Code Includes
- Complete REST API with CRUD endpoints
- Database schema (Prisma/TypeORM/SQLAlchemy)
- Business logic layer (Services)
- Data access layer (Repositories)
- Authentication & authorization
- Input validation
- Error handling
- Docker configuration
- Testing setup
- API documentation (Swagger)

## Quick Start

### 1. Install Dependencies

```bash
cd "FORGE 0.3"
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Add your OPENAI_API_KEY in .env
```

### 3. Run FORGE

```bash
python main.py --help
```

## CLI Commands

### Project Indexing
```bash
# Index a project for semantic search
python main.py index run /path/to/project

# Search code semantically
python main.py index search /path/to/project "search query"

# Search symbols
python main.py index symbols /path/to/project "symbol name"
```

### Backend Generation
```bash
# Analyze frontend and show inferred architecture
python main.py backend analyze /path/to/frontend

# Generate complete backend
python main.py backend generate /path/to/frontend -f express -d postgresql

# Add a new model
python main.py backend add-model /path/to/project ModelName -f '[{"name":"field","type":"string"}]'

# Add an endpoint
python main.py backend add-endpoint /path/to/project GET /api/resource

# Sync backend with frontend changes
python main.py backend sync /path/to/project

# Rollback last change
python main.py backend rollback /path/to/project
```

### Interactive Chat
```bash
# Chat with AI about your codebase
python main.py chat /path/to/project
```

### Project Management
```bash
# Initialize a new project
python main.py init /path/to/project -f express

# Show project status
python main.py status /path/to/project
```

## Architecture

```
FORGE/
├── main.py                # CLI interface
├── agent.py               # Core code agent
├── backend_agent.py       # Backend generation logic
├── fullstack_agent.py     # Unified full-stack agent
├── analyzers/             # Frontend code analysis
├── inference/             # AI model inference
├── synthesis/             # Architecture design
├── generation/            # Code generation pipeline
├── execution/             # File change application
├── indexers/              # Code indexing
├── embeddings/            # Vector embeddings
├── vectorstore/           # Vector storage (ChromaDB)
├── search/                # Semantic search
├── navigation/            # Go-to-definition, references
├── parsers/               # Multi-language parsing
└── orchestration/         # Task planning & execution
```

## What Makes FORGE Unique

1. **Frontend → Backend Translation** - Analyzes React/Vue/Angular and generates matching backend
2. **Multi-Framework Output** - 8 frameworks × 4 databases = 32 combinations
3. **Code Review & Debug** - Review and debug existing backend code
4. **Deep Code Understanding** - Tree-sitter parsing + vector embeddings + AI inference
5. **Free & Open Source** - Unlike paid alternatives

## License

See LICENSE file for details.
