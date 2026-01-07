# Backend Development Prompts - Visual Structure

```
generation/prompts/backend/
│
├── 📚 DOCUMENTATION
│   ├── README.md                  - Complete guide to using the prompts
│   ├── QUICK_REFERENCE.md         - Quick lookup for prompt selection
│   ├── USAGE_EXAMPLES.md          - 7 real-world usage examples
│   └── COMPLETE_SUMMARY.md        - Detailed summary of all contents
│
├── 🎯 MASTER PROMPT
│   └── backend_master_prompt.py   - Comprehensive overview (28 topics)
│
├── 🌐 CORE BACKEND PROMPTS
│   ├── http_fundamentals_prompt.py      - HTTP, routing, CORS, caching
│   ├── middleware_prompt.py             - Request pipeline, middleware patterns
│   ├── validation_prompt.py             - Input validation, transformation
│   ├── business_logic_prompt.py         - Service layer, CRUD, architecture
│   └── error_handling_prompt.py         - Error strategies, monitoring
│
├── ⚡ PERFORMANCE & SCALABILITY
│   ├── caching_strategies_prompt.py     - Cache patterns, Redis, eviction
│   ├── scaling_performance_prompt.py    - Optimization, scaling, profiling
│   └── task_queuing_prompt.py           - Background jobs, scheduling
│
├── 📊 OPERATIONS
│   └── observability_prompt.py          - Logging, metrics, tracing
│
├── 🔄 REALTIME
│   └── realtime_systems_prompt.py       - WebSockets, SSE, pub/sub
│
└── 🔧 MODULE
    └── __init__.py                       - Python exports

═══════════════════════════════════════════════════════════════════════════════

TOPIC COVERAGE MAP
═══════════════════════════════════════════════════════════════════════════════

http_fundamentals_prompt.py:
  ✓ Request Lifecycle & HTTP Flow         ✓ HTTP Methods (GET, POST, PUT, etc.)
  ✓ HTTP Status Codes                     ✓ HTTP Headers
  ✓ CORS (Simple & Preflight)             ✓ HTTP Caching (ETag, Cache-Control)
  ✓ HTTP Versions (1.1, 2, 3)             ✓ Content Negotiation
  ✓ Compression (gzip, Brotli)            ✓ Persistent Connections
  ✓ SSL/TLS & HTTPS                       ✓ Routing Fundamentals
  ✓ URL Structure & Parameters            ✓ API Versioning

middleware_prompt.py:
  ✓ Middleware Fundamentals               ✓ Middleware Chaining
  ✓ Security Headers (Helmet)             ✓ CORS Configuration
  ✓ CSRF Protection                       ✓ Rate Limiting
  ✓ Authentication Middleware             ✓ Authorization
  ✓ Logging & Request ID                  ✓ Body Parsing
  ✓ Error Handling                        ✓ Compression
  ✓ Multipart Handling                    ✓ Timeout
  ✓ Static File Serving                   ✓ Request Context

validation_prompt.py:
  ✓ Syntactic Validation                  ✓ Semantic Validation
  ✓ Type Validation                       ✓ Client vs Server Validation
  ✓ Type Casting                          ✓ Normalization
  ✓ Sanitization                          ✓ Conditional Validation
  ✓ Relational Validation                 ✓ Async Validation
  ✓ Chain Validation                      ✓ Custom Validators
  ✓ Error Handling                        ✓ Validation Libraries

business_logic_prompt.py:
  ✓ Layer Separation                      ✓ SOLID Principles
  ✓ Transaction Scripts                   ✓ Domain Models
  ✓ Service Orchestration                 ✓ CRUD Operations
  ✓ Error Propagation                     ✓ MVC Pattern
  ✓ Controller Design                     ✓ RESTful Structure

error_handling_prompt.py:
  ✓ Error Types                           ✓ Fail-Safe Strategy
  ✓ Fail-Fast Strategy                    ✓ Graceful Degradation
  ✓ Retry with Backoff                    ✓ Circuit Breaker
  ✓ Custom Error Classes                  ✓ Error Messages
  ✓ Error Logging                         ✓ Stack Traces
  ✓ Error Monitoring (Sentry)             ✓ Alerting
  ✓ Error Recovery                        ✓ Cleanup

caching_strategies_prompt.py:
  ✓ Caching Fundamentals                  ✓ Cache Types
  ✓ Cache-Aside Pattern                   ✓ Write-Through
  ✓ Write-Behind                          ✓ Read-Through
  ✓ Refresh-Ahead                         ✓ LRU Eviction
  ✓ LFU Eviction                          ✓ TTL
  ✓ L1/L2 Caching                         ✓ Cache Invalidation
  ✓ Redis & Memcached                     ✓ CDN Caching

task_queuing_prompt.py:
  ✓ Queue Fundamentals                    ✓ Producer/Consumer
  ✓ Job Lifecycle                         ✓ Task Dependencies
  ✓ Concurrency Control                   ✓ Error Handling
  ✓ Retry Logic                           ✓ Dead Letter Queue
  ✓ Job Prioritization                    ✓ Rate Limiting
  ✓ Scheduling (Delayed, Cron)            ✓ Monitoring
  ✓ BullMQ/Bull                           ✓ RabbitMQ

observability_prompt.py:
  ✓ Three Pillars (Logs, Metrics, Traces) ✓ Log Types
  ✓ Log Levels                            ✓ Structured Logging
  ✓ Centralized Logging                   ✓ Log Rotation
  ✓ Metrics Collection                    ✓ Prometheus
  ✓ Grafana Dashboards                    ✓ Distributed Tracing
  ✓ OpenTelemetry                         ✓ Jaeger/Zipkin
  ✓ Alerting                              ✓ Health Checks

scaling_performance_prompt.py:
  ✓ Performance Metrics                   ✓ Profiling
  ✓ Database Optimization                 ✓ Query Optimization
  ✓ Indexing                              ✓ Connection Pooling
  ✓ Code Optimization                     ✓ Memory Optimization
  ✓ Network Optimization                  ✓ Concurrency
  ✓ Parallelism                           ✓ Vertical Scaling
  ✓ Horizontal Scaling                    ✓ Load Balancing
  ✓ Auto-Scaling                          ✓ Performance Testing

realtime_systems_prompt.py:
  ✓ WebSockets                            ✓ Server-Sent Events
  ✓ Long Polling                          ✓ Pub/Sub Pattern
  ✓ Redis Pub/Sub                         ✓ Room Management
  ✓ Socket.IO                             ✓ Scaling Realtime
  ✓ Sticky Sessions                       ✓ Redis Adapter
  ✓ Connection Management                 ✓ Heartbeat/Ping-Pong
  ✓ Authentication                        ✓ Security

═══════════════════════════════════════════════════════════════════════════════

USAGE PATTERNS
═══════════════════════════════════════════════════════════════════════════════

BASIC REST API:
  HTTP_FUNDAMENTALS + BUSINESS_LOGIC
  └─ Focus: CRUD operations, routing, basic HTTP

SECURE API:
  HTTP_FUNDAMENTALS + MIDDLEWARE + VALIDATION
  └─ Focus: Authentication, authorization, input validation

PRODUCTION API:
  BACKEND_MASTER + ERROR_HANDLING + OBSERVABILITY
  └─ Focus: Monitoring, error handling, logging

HIGH-PERFORMANCE API:
  HTTP_FUNDAMENTALS + CACHING_STRATEGIES + SCALING_PERFORMANCE
  └─ Focus: Optimization, caching, database tuning

ASYNC SYSTEM:
  TASK_QUEUING + ERROR_HANDLING + OBSERVABILITY
  └─ Focus: Background jobs, retries, monitoring

REALTIME APP:
  REALTIME_SYSTEMS + CACHING_STRATEGIES + OBSERVABILITY
  └─ Focus: WebSockets, pub/sub, connection management

FULL-STACK BACKEND:
  BACKEND_MASTER + (All specific prompts as needed)
  └─ Focus: Comprehensive coverage of all aspects

═══════════════════════════════════════════════════════════════════════════════

DEPENDENCY GRAPH
═══════════════════════════════════════════════════════════════════════════════

                    ┌─────────────────────────┐
                    │  BACKEND_MASTER_PROMPT  │
                    │  (Comprehensive Guide)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
            ┌───────▼───────┐         ┌──────▼──────┐
            │  CORE BACKEND │         │ OPERATIONS  │
            └───────┬───────┘         └──────┬──────┘
                    │                        │
        ┌───────────┼───────────┐           │
        │           │           │            │
    ┌───▼───┐   ┌──▼──┐   ┌────▼────┐   ┌──▼──────────┐
    │ HTTP  │   │ MID │   │ VALID.  │   │ OBSERV.     │
    │ FUND. │   │ WARE│   │         │   │             │
    └───┬───┘   └──┬──┘   └────┬────┘   └──┬──────────┘
        │          │           │            │
        │      ┌───▼───────────▼────┐       │
        │      │   BUSINESS_LOGIC   │       │
        │      └───┬───────────┬────┘       │
        │          │           │            │
    ┌───▼──────────▼───┐   ┌──▼────────┐   │
    │  ERROR_HANDLING  │   │  CACHING  │   │
    └──────────┬────────┘   └──┬────────┘   │
               │               │            │
           ┌───▼───────────────▼────────────▼───┐
           │     SCALING_PERFORMANCE            │
           └───┬────────────────────────┬───────┘
               │                        │
        ┌──────▼──────┐         ┌───────▼────────┐
        │ TASK_QUEUE  │         │   REALTIME     │
        └─────────────┘         └────────────────┘

═══════════════════════════════════════════════════════════════════════════════

STATISTICS
═══════════════════════════════════════════════════════════════════════════════

Total Prompts:           11 specialized + 1 master = 12 total
Total Lines of Code:     ~50,000+ lines
Topics Covered:          28 major backend topics
Documentation Files:     4 (README, QUICK_REF, USAGE, SUMMARY)
Example Implementations: 7 complete real-world examples
Coverage Areas:          8 (HTTP, Auth, Validation, Caching, Errors, 
                            Scaling, Realtime, Monitoring)

═══════════════════════════════════════════════════════════════════════════════

QUICK START
═══════════════════════════════════════════════════════════════════════════════

1. Import what you need:
   from generation.prompts.backend import BACKEND_MASTER_PROMPT

2. Combine with your request:
   prompt = f"{BACKEND_MASTER_PROMPT}\\n\\nBuild a REST API for users"

3. Generate code with your LLM

4. Iterate with specific prompts for details

For detailed guidance, see:
- README.md for comprehensive documentation
- QUICK_REFERENCE.md for fast lookup
- USAGE_EXAMPLES.md for real-world examples
```
