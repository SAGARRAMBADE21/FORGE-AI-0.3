# Backend Development Prompts

Comprehensive prompts for generating production-grade backend code covering all aspects of modern web application development.

## Overview

This collection provides detailed, expert-level guidance for implementing backend systems. Each prompt covers a specific domain with best practices, patterns, and real-world examples.

## Prompt Files

### Master Prompt
- **`backend_master_prompt.py`**: Comprehensive overview of all backend development topics. Use this as a primary reference or when you need broad backend expertise.

### Specialized Prompts

1. **`http_fundamentals_prompt.py`**
   - HTTP protocol details (methods, headers, status codes)
   - Request/response lifecycle
   - CORS (simple and preflight requests)
   - HTTP caching (ETag, Cache-Control)
   - HTTP versions (1.1, 2, 3)
   - Compression (gzip, Brotli)
   - SSL/TLS and HTTPS
   - Routing and API design

2. **`middleware_prompt.py`**
   - Middleware architecture and lifecycle
   - Request/response processing
   - Common middleware types (security, CORS, auth, logging, rate limiting)
   - Middleware chaining and order
   - Error handling middleware
   - Performance considerations

3. **`validation_prompt.py`**
   - Input validation strategies
   - Syntactic, semantic, and type validation
   - Client-side vs server-side validation
   - Data transformation and normalization
   - Sanitization and security
   - Complex validation patterns
   - Error handling and messaging

4. **`business_logic_prompt.py`**
   - Layer separation (presentation, business, data access)
   - SOLID principles
   - Service layer patterns
   - CRUD operations
   - Domain-driven design
   - Error propagation
   - Controller and handler patterns

5. **`error_handling_prompt.py`**
   - Error types and strategies
   - Custom error classes
   - Error catching best practices
   - Logging with context
   - Error monitoring and alerting
   - Graceful error handling
   - Recovery and cleanup

6. **`caching_strategies_prompt.py`**
   - Caching fundamentals and use cases
   - Cache types (memory, distributed, CDN)
   - Caching strategies (cache-aside, write-through, read-through)
   - Eviction policies (LRU, LFU, TTL)
   - Cache invalidation
   - Hierarchical caching (L1, L2)
   - Performance optimization

7. **`task_queuing_prompt.py`**
   - Background job processing
   - Queue components (producer, queue, consumer)
   - Job lifecycle and dependencies
   - Concurrency and prioritization
   - Error handling and retries
   - Dead letter queues
   - Scheduling and cron jobs

8. **`observability_prompt.py`**
   - Logging (types, levels, structured logging)
   - Monitoring (metrics, dashboards, alerts)
   - Distributed tracing
   - Three pillars of observability
   - Tools (Prometheus, Grafana, ELK, Jaeger)
   - Health checks and probes

9. **`scaling_performance_prompt.py`**
   - Performance metrics and profiling
   - Bottleneck identification
   - Optimization strategies
   - Database query optimization
   - Horizontal vs vertical scaling
   - Load balancing and auto-scaling
   - Graceful degradation
   - Performance testing

10. **`realtime_systems_prompt.py`**
    - WebSockets for bidirectional communication
    - Server-Sent Events (SSE)
    - Long polling
    - Publish-Subscribe patterns
    - Realtime frameworks (Socket.IO)
    - Scaling realtime systems
    - Security and authentication

11. **`code_quality_checklist_prompt.py`**
    - Pre-generation validation checks
    - Service layer consistency verification
    - Repository pattern validation
    - Authentication completeness checks
    - Import and dependency verification
    - Schema and model alignment
    - Route and endpoint validation

12. **`critical_files_prompt.py`**
    - Essential file generation rules
    - Requirements and dependency files
    - Configuration files (settings, env)
    - Application entry points
    - Database and migration setup
    - Ensures all critical files are present for a working application

## Usage

### In Code Generation

Import and use specific prompts based on the feature you're implementing:

```python
from generation.prompts.backend import (
    BACKEND_MASTER_PROMPT,
    HTTP_FUNDAMENTALS_PROMPT,
    MIDDLEWARE_PROMPT,
    CACHING_STRATEGIES_PROMPT,
    CODE_QUALITY_CHECKLIST_PROMPT,
    CRITICAL_FILES_PROMPT
)

# Use master prompt for comprehensive backend generation
system_prompt = BACKEND_MASTER_PROMPT

# Or combine specific prompts for targeted features
system_prompt = f"""
{HTTP_FUNDAMENTALS_PROMPT}

{MIDDLEWARE_PROMPT}

Now implement a REST API with proper middleware...
"""
```

### Choosing the Right Prompt

- **General backend development**: Use `BACKEND_MASTER_PROMPT`
- **API endpoints and routing**: Use `HTTP_FUNDAMENTALS_PROMPT`
- **Request processing pipeline**: Use `MIDDLEWARE_PROMPT`
- **Form handling and data input**: Use `VALIDATION_PROMPT`
- **Business rules and workflows**: Use `BUSINESS_LOGIC_PROMPT`
- **Fault tolerance**: Use `ERROR_HANDLING_PROMPT`
- **Performance optimization**: Use `CACHING_STRATEGIES_PROMPT` or `SCALING_PERFORMANCE_PROMPT`
- **Async operations**: Use `TASK_QUEUING_PROMPT`
- **Debugging and monitoring**: Use `OBSERVABILITY_PROMPT`
- **Chat/notifications**: Use `REALTIME_SYSTEMS_PROMPT`
- **Pre-generation validation**: Use `CODE_QUALITY_CHECKLIST_PROMPT`
- **Ensuring essential files**: Use `CRITICAL_FILES_PROMPT`

## Topics Covered

### Core Backend Concepts
- HTTP protocol and request lifecycle
- Routing and API design
- Serialization/deserialization
- Authentication and authorization
- Input validation and transformation
- Middleware architecture
- Request context management

### Application Architecture
- MVC pattern
- Service layer design
- SOLID principles
- Domain-driven design
- Layered architecture
- Error handling patterns

### Data Management
- Databases (SQL and NoSQL)
- ACID and CAP theorem
- Query optimization
- Connection pooling
- Transactions and concurrency
- ORM usage

### Performance & Scalability
- Caching strategies
- Database optimization
- Code optimization
- Load balancing
- Horizontal/vertical scaling
- Performance testing
- Graceful degradation

### Asynchronous Processing
- Task queues
- Background jobs
- Job scheduling
- Retry logic
- Dead letter queues
- Concurrency control

### Operations & DevOps
- Logging strategies
- Monitoring and metrics
- Distributed tracing
- Health checks
- Graceful shutdown
- CI/CD concepts
- Containerization

### Realtime Features
- WebSockets
- Server-Sent Events
- Pub/Sub patterns
- Connection management
- Scaling realtime systems

### Security
- SQL injection prevention
- XSS and CSRF protection
- Authentication patterns
- Authorization models
- Rate limiting
- Input sanitization
- Security headers

## Best Practices

Each prompt emphasizes:

- ✓ Production-ready patterns
- ✓ Security considerations
- ✓ Performance optimization
- ✓ Error handling
- ✓ Testing approaches
- ✓ Monitoring and observability
- ✓ Scalability considerations
- ✓ Code maintainability

## Examples

### REST API with Middleware
```python
from generation.prompts.backend import HTTP_FUNDAMENTALS_PROMPT, MIDDLEWARE_PROMPT

prompt = f"""
{HTTP_FUNDAMENTALS_PROMPT}
{MIDDLEWARE_PROMPT}

Create a REST API for user management with:
- CRUD endpoints
- Authentication middleware
- Rate limiting
- Input validation
- Error handling
"""
```

### Task Queue System
```python
from generation.prompts.backend import TASK_QUEUING_PROMPT, ERROR_HANDLING_PROMPT

prompt = f"""
{TASK_QUEUING_PROMPT}
{ERROR_HANDLING_PROMPT}

Implement a task queue system for:
- Email sending
- Image processing
- Report generation

Include retry logic and error handling.
"""
```

### Realtime Chat
```python
from generation.prompts.backend import REALTIME_SYSTEMS_PROMPT, CACHING_STRATEGIES_PROMPT

prompt = f"""
{REALTIME_SYSTEMS_PROMPT}
{CACHING_STRATEGIES_PROMPT}

Build a realtime chat system with:
- WebSocket connections
- Message history caching
- User presence
- Room management
"""
```

## Integration with Generation Pipeline

These prompts are designed to work with the FORGE code generation system:

1. Select appropriate prompt(s) based on requirements
2. Combine with user's specific request
3. Pass to LLM for code generation
4. Generate production-ready backend code

## Contributing

When adding new prompts:
- Follow the established format with clear sections
- Include practical examples
- Cover best practices and common pitfalls
- Add both DO and DON'T guidance
- Update this README

## License

Part of the FORGE code generation system.
