# Using Both Single-Agent and Multi-Agent Modes

FORGE 0.3 now supports **hybrid code generation** - use both modes strategically!

## Available Modes

### 1. **HYBRID (Default)** - Intelligent Auto-Selection
```python
agent = BackendAgent(project_root, config)
# Hybrid mode is default - auto-selects based on complexity
await agent.generate_backend()
```

**How it works:**
- Analyzes project complexity automatically
- **Low complexity** (1-3 models, simple auth) → Single-agent
- **Medium complexity** (4-10 models, OAuth) → Multi-agent  
- **High complexity** (10+ models, microservices) → Multi-agent

**Complexity factors:**
- Number of models/entities
- Authentication requirements (JWT, OAuth2, MFA)
- API endpoint count
- Features (microservices, payments, real-time)

---

### 2. **SINGLE-AGENT** - Fast Prototyping
```python
agent = BackendAgent(project_root, config)
agent.set_generation_mode(GenerationMode.SINGLE_AGENT)
await agent.generate_backend()
```

**Best for:**
- ✅ MVPs and prototypes
- ✅ Learning and experimentation
- ✅ Simple CRUD APIs
- ✅ Quick iterations
- ✅ Cost-sensitive projects

**Benefits:**
- ⚡ Faster generation (1-2 minutes)
- 💰 Lower API costs
- 🎯 Simpler workflow
- 📦 Good for small/medium apps

---

### 3. **MULTI-AGENT** - Production Quality
```python
agent = BackendAgent(project_root, config)
agent.set_generation_mode(GenerationMode.MULTI_AGENT)
await agent.generate_backend()
```

**Best for:**
- ✅ Production systems
- ✅ Enterprise applications
- ✅ Microservices architectures
- ✅ High-security requirements
- ✅ Complex business logic

**Benefits:**
- 🏆 Production-ready code
- 🔒 Security hardened
- 🧪 Comprehensive testing
- 🚀 DevOps infrastructure
- 👥 Collaborative design (8 specialized agents)

---

## Strategic Workflow (Recommended)

### Phase 1: MVP Development
```python
# Start with single-agent for fast iteration
agent = BackendAgent(project_root, config)
agent.set_generation_mode(GenerationMode.SINGLE_AGENT)

await agent.initialize()
mvp = await agent.generate_backend()

# Test features, validate ideas, iterate quickly
```

### Phase 2: Production Deployment
```python
# Switch to multi-agent for production quality
agent.set_generation_mode(GenerationMode.MULTI_AGENT)

await agent.initialize()  # Assembles 8-agent team
production = await agent.generate_backend()

# Get comprehensive testing, security, DevOps
report = agent.get_agent_collaboration_report()
```

---

## Usage Examples

### Example 1: Simple Blog API (Auto: Single-Agent)
```python
agent = BackendAgent(Path("./blog"), config)
# Hybrid mode detects: 3 models (User, Post, Comment)
# Auto-selects: Single-agent (low complexity)
result = await agent.generate_backend()
```

### Example 2: E-Commerce Platform (Auto: Multi-Agent)
```python
agent = BackendAgent(Path("./ecommerce"), config)
# Hybrid mode detects: 12 models, payment features, OAuth
# Auto-selects: Multi-agent (high complexity)
result = await agent.generate_backend()
```

### Example 3: Force Mode for Testing
```python
# Test same project with both modes
agent = BackendAgent(Path("./test_project"), config)

# Quick test with single-agent
agent.set_generation_mode(GenerationMode.SINGLE_AGENT)
quick_result = await agent.generate_backend()

# Production test with multi-agent
agent.set_generation_mode(GenerationMode.MULTI_AGENT)
await agent.initialize()  # Re-initialize with team
prod_result = await agent.generate_backend()
```

---

## Mode Comparison

| Feature | Single-Agent | Multi-Agent |
|---------|-------------|-------------|
| **Speed** | ⚡ Fast (1-2 min) | 🐢 Slower (5-10 min) |
| **Cost** | 💰 Low | 💰💰 Higher |
| **Quality** | ✅ Good | ✅✅ Excellent |
| **Testing** | Basic | Comprehensive |
| **Security** | Standard | Hardened |
| **DevOps** | Basic | Production-ready |
| **Architecture** | Simple | Scalable |
| **Best For** | MVP, Learning | Production |

---

## Configuration API

```python
from backend_agent import BackendAgent, GenerationMode

# Set mode
agent.set_generation_mode(GenerationMode.SINGLE_AGENT)
agent.set_generation_mode(GenerationMode.MULTI_AGENT)
agent.set_generation_mode(GenerationMode.HYBRID)

# Legacy method (still works)
agent.enable_multi_agent(True)   # Multi-agent
agent.enable_multi_agent(False)  # Single-agent

# Get collaboration report (multi-agent only)
if agent._generation_mode == GenerationMode.MULTI_AGENT:
    report = agent.get_agent_collaboration_report()
    print(report)
```

---

## When to Use Which Mode?

### Use SINGLE-AGENT when:
- Building MVP or prototype
- Learning backend development
- Simple CRUD applications
- Limited budget/API calls
- Quick iterations needed
- Team is small (1-2 developers)

### Use MULTI-AGENT when:
- Deploying to production
- Enterprise/business-critical app
- Complex authentication (OAuth2, SSO, MFA)
- Microservices architecture
- Payment/billing features
- Real-time features (WebSockets)
- Need comprehensive testing
- Security is critical
- Team is large (multiple engineers)

### Use HYBRID (default) when:
- Want intelligent automatic selection
- Project complexity varies
- Building multiple features incrementally
- Not sure which mode to use

---

## Demo Script

Run the demonstration:
```bash
python demo_hybrid_mode.py
```

This shows:
1. Hybrid mode (auto-selection)
2. Forced single-agent mode
3. Forced multi-agent mode
4. Strategic workflow (both modes)

---

## Under the Hood

### Complexity Assessment Algorithm
```python
def _assess_project_complexity(self) -> str:
    score = 0
    
    # Models: 10+ = +3, 5-10 = +2, 2-5 = +1
    # Auth: Multi-strategy = +2, MFA = +2
    # Endpoints: 20+ = +2, 10-20 = +1
    # Features: Microservices = +3, Payments = +2, Real-time = +2
    
    if score >= 8: return "high"    # Multi-agent
    if score >= 4: return "medium"  # Multi-agent
    return "low"                     # Single-agent
```

### Generation Flow
```
User Request
    ↓
BackendAgent
    ↓
Mode Selection (Hybrid/Single/Multi)
    ↓
┌─────────────────┬──────────────────┐
│ Single-Agent    │   Multi-Agent    │
│   Pipeline      │   Orchestrator   │
│       ↓         │        ↓         │
│ PromptBuilder   │   8 Agents       │
│       ↓         │        ↓         │
│  LLMGenerator   │  LLMGenerator    │
└─────────────────┴──────────────────┘
    ↓
Generated Files
```

---

## Summary

✅ **You now have 3 modes:**
- SINGLE-AGENT for speed
- MULTI-AGENT for quality  
- HYBRID for intelligence

✅ **Use both strategically:**
- MVP → Single-agent
- Production → Multi-agent

✅ **Let FORGE decide:**
- Default HYBRID mode auto-selects based on complexity

**Start prototyping fast, deploy production-ready!** 🚀
