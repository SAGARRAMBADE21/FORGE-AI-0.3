# How FORGE 0.3 Generates Backend Code

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        USER INITIATES REQUEST                            │
│                                                                          │
│  Option 1: CLI Command                                                  │
│  $ python main.py backend generate /path/to/project                     │
│                                                                          │
│  Option 2: Python Code                                                  │
│  agent = FullStackAgent(project_path)                                   │
│  result = await agent.generate_backend()                                │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        STEP 1: INITIALIZATION                            │
│  File: fullstack_agent.py → initialize()                                │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Initialize CodeAgent (indexer)                                      │
│     → Parse all code files                                              │
│     → Create semantic embeddings                                        │
│     → Build symbol table                                                │
│     → Index in vector store                                             │
│                                                                          │
│  2. Initialize BackendAgent                                              │
│     → Load/create session                                               │
│     → Initialize multi-agent team (8 agents)                            │
│     → Load checkpoint manager                                           │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   STEP 2: FRONTEND ANALYSIS (Optional)                   │
│  File: backend_agent.py → analyze_frontend()                            │
├─────────────────────────────────────────────────────────────────────────┤
│  • Scan frontend code for:                                              │
│    - Component structure                                                │
│    - State management (Redux/Context)                                   │
│    - API calls (fetch, axios)                                           │
│    - Form inputs and data structures                                    │
│    - Authentication patterns                                            │
│                                                                          │
│  • Infer from frontend:                                                 │
│    - Data models needed                                                 │
│    - API endpoints required                                             │
│    - Auth requirements                                                  │
│    - Relationships between entities                                     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              STEP 3: BACKEND GENERATION (MULTI-AGENT)                    │
│  File: backend_agent.py → generate_backend()                            │
│                        ↓                                                 │
│        _generate_backend_multi_agent() if multi-agent enabled          │
│                        ↓                                                 │
│  File: orchestration/agent_orchestrator.py → execute_workflow()        │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      MULTI-AGENT WORKFLOW                                │
│  8 Specialized Agents Collaborate via Orchestrator                      │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│   PHASE 1: ARCHITECTURE   │   │   PHASE 2: PARALLEL       │
│   (Sequential)            │   │   DESIGN (Concurrent)     │
├───────────────────────────┤   ├───────────────────────────┤
│ 🏗️ Architect Agent        │   │ 🗄️ Database Engineer     │
│ • Analyzes requirements   │   │   • Designs schema        │
│ • Chooses patterns        │   │   • Plans migrations      │
│ • Decides architecture    │   │   • Designs indexes       │
│ • Selects tech stack      │───┤                           │
│                           │   │ 🌐 API Engineer           │
│ Uses Qwen2.5-Coder LLM:   │   │   • Designs endpoints     │
│ system_prompt = """You    │   │   • Plans validation      │
│ are a senior architect""" │   │   • Designs responses     │
│ user_prompt = context     │   │                           │
│ response = llm.generate() │   │ 🔐 Auth Engineer          │
│                           │   │   • Designs auth system   │
│ Output:                   │   │   • Plans JWT strategy    │
│ {                         │   │   • Designs permissions   │
│   "pattern": "layered",   │   │                           │
│   "components": [...],    │   │ All communicate via       │
│   "decisions": {...}      │   │ orchestrator messages     │
│ }                         │   │                           │
└───────────────┬───────────┘   └───────────────┬───────────┘
                │                               │
                └───────────────┬───────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              PHASE 3: PARALLEL IMPLEMENTATION                            │
│              (All agents work simultaneously)                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🗄️ Database Engineer        🌐 API Engineer                           │
│  ┌────────────────────┐      ┌────────────────────┐                   │
│  │ Generates:         │      │ Generates:         │                   │
│  │ • Models           │      │ • Controllers      │                   │
│  │ • Repositories     │      │ • Routes           │                   │
│  │ • Migrations       │      │ • Validators       │                   │
│  │                    │      │ • Middleware       │                   │
│  │ LLM Call:          │      │                    │                   │
│  │ system_prompt =    │      │ LLM Call:          │                   │
│  │ "Generate DB code" │      │ system_prompt =    │                   │
│  │ user_prompt =      │      │ "Generate API      │                   │
│  │ schema_design      │      │  endpoints"        │                   │
│  │                    │      │ user_prompt =      │                   │
│  │ Output files:      │      │ api_design +       │                   │
│  │ - User.model.ts    │      │ service_info       │                   │
│  │ - UserRepo.ts      │      │                    │                   │
│  │ - 001_create.sql   │      │ Output files:      │                   │
│  └────────────────────┘      │ - user.routes.ts   │                   │
│                              │ - user.controller  │                   │
│  ⚙️ Service Engineer         │ - validators.ts    │                   │
│  ┌────────────────────┐      └────────────────────┘                   │
│  │ Generates:         │                                                │
│  │ • Business logic   │      🔐 Auth Engineer                         │
│  │ • Services         │      ┌────────────────────┐                   │
│  │ • Helpers          │      │ Generates:         │                   │
│  │                    │      │ • Auth service     │                   │
│  │ Coordinates with   │      │ • JWT middleware   │                   │
│  │ API Engineer via   │      │ • Guards           │                   │
│  │ messages           │      │ • Token utils      │                   │
│  └────────────────────┘      └────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              PHASE 4: QUALITY & DEPLOYMENT                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🧪 Testing Engineer            🚀 DevOps Engineer                      │
│  ┌──────────────────────┐      ┌──────────────────────┐               │
│  │ Generates:           │      │ Generates:           │               │
│  │ • Unit tests         │      │ • Dockerfile         │               │
│  │ • Integration tests  │      │ • docker-compose.yml │               │
│  │ • Test fixtures      │      │ • CI/CD pipeline     │               │
│  │ • Mock data          │      │ • .env.example       │               │
│  │ • Test config        │      │ • Deploy scripts     │               │
│  │                      │      │                      │               │
│  │ LLM generates 47+    │      │ LLM generates        │               │
│  │ test cases covering  │      │ production configs   │               │
│  │ all endpoints        │      │                      │               │
│  └──────────────────────┘      └──────────────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              PHASE 5: CODE REVIEW & OPTIMIZATION                         │
│  File: orchestration/backend_agents.py → CodeReviewerAgent             │
├─────────────────────────────────────────────────────────────────────────┤
│  👁️ Code Reviewer                                                       │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │ Reviews ALL generated code for:                              │      │
│  │                                                               │      │
│  │ Security:                                                     │      │
│  │ • SQL injection prevention                                   │      │
│  │ • XSS protection                                             │      │
│  │ • Authentication vulnerabilities                             │      │
│  │ • Input validation                                           │      │
│  │                                                               │      │
│  │ Performance:                                                  │      │
│  │ • Query optimization                                         │      │
│  │ • Proper indexing                                            │      │
│  │ • Caching strategies                                         │      │
│  │                                                               │      │
│  │ Best Practices:                                              │      │
│  │ • Code organization                                          │      │
│  │ • Error handling                                             │      │
│  │ • Documentation                                              │      │
│  │ • Type safety                                                │      │
│  │                                                               │      │
│  │ Output:                                                       │      │
│  │ {                                                             │      │
│  │   "approved": true/false,                                    │      │
│  │   "issues": [...],                                           │      │
│  │   "recommendations": [...],                                  │      │
│  │   "optimizations": [...]                                     │      │
│  │ }                                                             │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STEP 4: RESULT AGGREGATION                            │
│  File: backend_agent.py → _generate_backend_multi_agent()              │
├─────────────────────────────────────────────────────────────────────────┤
│  Orchestrator collects results from all agents:                         │
│                                                                          │
│  result = {                                                              │
│    'architecture': {...},      # From Architect                         │
│    'database': {               # From Database Engineer                 │
│      'code': "...",                                                      │
│      'files': {                                                          │
│        'models': "...",                                                  │
│        'repositories': "...",                                            │
│        'migrations': "..."                                               │
│      }                                                                   │
│    },                                                                    │
│    'api': {...},               # From API Engineer                      │
│    'services': {...},          # From Service Engineer                  │
│    'auth': {...},              # From Auth Engineer                     │
│    'tests': {...},             # From Testing Engineer                  │
│    'devops': {...},            # From DevOps Engineer                   │
│    'review': {                 # From Code Reviewer                     │
│      'approved': true,                                                   │
│      'feedback': "..."                                                   │
│    }                                                                     │
│  }                                                                       │
│                                                                          │
│  Convert to GeneratedFile objects:                                      │
│  - src/models/User.ts                                                   │
│  - src/models/Product.ts                                                │
│  - src/api/users.routes.ts                                              │
│  - src/api/users.controller.ts                                          │
│  - src/services/UserService.ts                                          │
│  - src/auth/jwt.middleware.ts                                           │
│  - tests/user.test.ts                                                   │
│  - Dockerfile                                                            │
│  - docker-compose.yml                                                    │
│  - .github/workflows/ci.yml                                              │
│  ... (90+ files total)                                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    STEP 5: RETURN TO USER                                │
├─────────────────────────────────────────────────────────────────────────┤
│  GenerationResult {                                                      │
│    success: true,                                                        │
│    files: [                                                              │
│      GeneratedFile {                                                     │
│        path: "src/models/User.ts",                                       │
│        content: "...",                                                   │
│        file_type: "ts",                                                  │
│        generator: "database_engineer"                                    │
│      },                                                                  │
│      ...                                                                 │
│    ],                                                                    │
│    stats: {                                                              │
│      generated_files: 91,                                                │
│      multi_agent: true,                                                  │
│      agent_messages: 23,                                                 │
│      agents_active: 8,                                                   │
│      review_status: "approved"                                           │
│    }                                                                     │
│  }                                                                       │
│                                                                          │
│  User receives complete, production-ready backend!                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Code Locations

### 1. Entry Points
- **CLI**: `main.py` → `backend_app.command("generate")`
- **Python API**: `fullstack_agent.py` → `generate_backend()`

### 2. Core Generation
- **Main Logic**: `backend_agent.py` → `generate_backend()`
- **Multi-Agent**: `backend_agent.py` → `_generate_backend_multi_agent()`

### 3. Orchestration
- **Orchestrator**: `orchestration/agent_orchestrator.py` → `execute_workflow()`
- **Agents**: `orchestration/backend_agents.py` → 8 specialized agents
- **Coordination**: `orchestration/agent_coordination.py` → workflow coordination

### 4. LLM Integration
- **Generator**: `generation/llm_generator.py` → `LLMGenerator.generate()`
- **Model**: Qwen/Qwen2.5-Coder-32B-Instruct (Hugging Face)

## Example: Full Execution

```python
# 1. User Code
from fullstack_agent import FullStackAgent

agent = FullStackAgent("./my-ecommerce-app")

# 2. Initialize (happens once)
await agent.initialize()
# → Indexes codebase
# → Builds 8-agent team
# → Each agent initializes with Qwen2.5-Coder model

# 3. Generate Backend
result = await agent.generate_backend()

# What happens internally:
# ┌─────────────────────────────────────────┐
# │ BackendAgent.generate_backend()         │
# │   ↓                                     │
# │ _generate_backend_multi_agent()         │
# │   ↓                                     │
# │ orchestrator.execute_workflow()         │
# │   ↓                                     │
# │ Phase 1: Architect plans                │
# │   LLM call → architecture design        │
# │   ↓                                     │
# │ Phase 2: Parallel design                │
# │   Database LLM → schema                 │
# │   API LLM → endpoints                   │
# │   Auth LLM → security                   │
# │   ↓                                     │
# │ Phase 3: Parallel implementation        │
# │   All agents generate code via LLM      │
# │   ↓                                     │
# │ Phase 4: Quality                        │
# │   Testing LLM → tests                   │
# │   DevOps LLM → configs                  │
# │   ↓                                     │
# │ Phase 5: Review                         │
# │   Reviewer LLM → optimization           │
# │   ↓                                     │
# │ Aggregate all files                     │
# │   ↓                                     │
# │ Return GenerationResult                 │
# └─────────────────────────────────────────┘

# 4. Result
print(f"Generated {len(result.files)} files")
# Output: Generated 91 files

print(result.stats)
# {
#   'generated_files': 91,
#   'multi_agent': True,
#   'agent_messages': 23,
#   'agents_active': 8,
#   'review_status': 'approved'
# }

# 5. Files are ready to use
for file in result.files:
    print(f"{file.path} - by {file.generator}")
# src/models/User.ts - by database_engineer
# src/api/users.controller.ts - by api_engineer
# src/services/UserService.ts - by service_engineer
# ... etc
```

## LLM Calls Under the Hood

Each agent makes LLM calls like this:

```python
# Example from Database Engineer Agent
async def _generate_code(self, task: AgentTask) -> Dict[str, Any]:
    system_prompt = """Generate production-ready database code.
    Include models, repositories, migrations, and query optimizations."""
    
    user_prompt = f"""
    Generate database implementation for:
    {schema}
    
    Include:
    1. ORM models
    2. Repository pattern implementations
    3. Database migrations
    4. Seed data (optional)
    5. Query helpers
    """
    
    # This uses Qwen/Qwen2.5-Coder-32B-Instruct
    response = await self.llm.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )
    
    # Response contains complete TypeScript/Python code
    return {
        "code": response,
        "files": {
            "models": "generated models code",
            "repositories": "generated repository code",
            "migrations": "generated migration code"
        }
    }
```

## Summary

**FORGE 0.3 generates backend code through a 5-phase multi-agent workflow:**

1. **Initialize** - Set up indexer and 8-agent team
2. **Analyze** (optional) - Understand frontend requirements
3. **Multi-Agent Generation** - 8 agents collaborate via LLM calls
4. **Aggregate** - Collect all generated files
5. **Return** - Provide production-ready backend

Each agent uses **Qwen/Qwen2.5-Coder-32B-Instruct** to generate specialized code, they communicate through the orchestrator, and the code reviewer ensures everything meets production standards.

**Result**: Complete, tested, deployable backend in ~2 minutes! 🚀
