# CLI Mode Usage Guide

## Switch Between Agent Modes in main.py

The CLI now supports all three generation modes!

## Basic Commands

### Default (Hybrid Mode)
```bash
python main.py backend generate ./frontend-project
```
Auto-selects single or multi-agent based on project complexity.

### Force Single-Agent Mode
```bash
python main.py backend generate ./frontend-project --mode single
```
Fast prototyping mode (1-2 minutes).

### Force Multi-Agent Mode
```bash
python main.py backend generate ./frontend-project --mode multi
```
Production quality with 8 specialized agents (5-10 minutes).

## Complete Examples

### Example 1: Quick MVP
```bash
python main.py backend generate ./my-app \
  --framework express \
  --database postgresql \
  --mode single \
  --output ./backend
```

### Example 2: Production Deployment
```bash
python main.py backend generate ./ecommerce-app \
  --framework nestjs \
  --database postgresql \
  --mode multi \
  --output ./backend-prod
```

### Example 3: Let FORGE Decide
```bash
python main.py backend generate ./blog-app \
  --framework fastapi \
  --database mongodb \
  --mode hybrid
```

### Example 4: Preview First (Dry Run)
```bash
python main.py backend generate ./my-app \
  --mode multi \
  --dry-run
```

## All Options

```bash
python main.py backend generate [PATH] [OPTIONS]

Arguments:
  PATH                    Project path (required)

Options:
  -o, --output DIR       Output directory (default: "backend")
  -f, --framework TEXT   Backend framework (default: "express")
                         Choices: express, nestjs, fastapi, flask, django, gin
  -d, --database TEXT    Database type (default: "postgresql")
                         Choices: postgresql, mysql, mongodb, redis
  -m, --mode TEXT        Generation mode (default: "hybrid")
                         Choices:
                           single - Fast single-agent (1-2 min)
                           multi  - Production multi-agent (5-10 min)
                           hybrid - Auto-select based on complexity
  --dry-run              Preview without applying changes
  --help                 Show help message
```

## Output Explained

### Hybrid Mode Output
```
Generation mode: HYBRID
  Will auto-select based on project complexity

[mode_selection] Auto-selected multi-agent mode (complexity: high)
[team_initialized] Backend engineering team assembled
...
✓ Backend generation complete!
Mode used: multi-agent (complexity: high)

Agent Collaboration:
  8 agents collaborated on this project
  - Architect: System design
  - Database Engineer: Schema design
  - API Engineer: REST endpoints
  ...
```

### Single-Agent Output
```
Generation mode: SINGLE
  Fast prototyping mode

[mode_selection] Using single-agent mode (fast generation)
[pipeline_stage] Generating database layer...
[pipeline_stage] Generating API layer...
...
✓ Backend generation complete!
```

### Multi-Agent Output
```
Generation mode: MULTI
  Production-quality mode with 8 specialized agents

[mode_selection] Using multi-agent mode (production-quality)
[team_initialized] Backend engineering team assembled
[architect] Designing system architecture...
[database_engineer] Creating schema...
[api_engineer] Designing REST endpoints...
...
✓ Backend generation complete!

Agent Collaboration:
  Architect Agent → Database Engineer: "Use UUID for all primary keys"
  Database Engineer → API Engineer: "Pagination supported on all list endpoints"
  ...
```

## Quick Reference

| Command | Mode | Speed | Quality | Use Case |
|---------|------|-------|---------|----------|
| `--mode single` | Single-Agent | ⚡ Fast | ✅ Good | MVP, prototypes |
| `--mode multi` | Multi-Agent | 🐢 Slow | ✅✅ Excellent | Production |
| `--mode hybrid` | Auto-Select | ⚡/🐢 Varies | ✅/✅✅ Adaptive | General use |

## Tips

1. **Start with hybrid** - Let FORGE decide
   ```bash
   python main.py backend generate ./my-app
   ```

2. **Quick iterations** - Use single mode
   ```bash
   python main.py backend generate ./my-app --mode single
   ```

3. **Production deployment** - Use multi mode
   ```bash
   python main.py backend generate ./my-app --mode multi
   ```

4. **Test before committing** - Use dry-run
   ```bash
   python main.py backend generate ./my-app --mode multi --dry-run
   ```

## Other Backend Commands

### Analyze Frontend
```bash
python main.py backend analyze ./frontend-project
```
Shows inferred models, APIs, and architecture without generating code.

### Add Model
```bash
python main.py backend add-model ./project User \
  --fields '[{"name":"email","type":"string"},{"name":"age","type":"number"}]'
```

## Help Commands

```bash
# General help
python main.py --help

# Backend commands help
python main.py backend --help

# Specific command help
python main.py backend generate --help
```

---

**Quick Start:**
```bash
# Simple project (auto-selects single-agent)
python main.py backend generate ./simple-blog

# Complex project (auto-selects multi-agent)
python main.py backend generate ./enterprise-ecommerce

# Force specific mode
python main.py backend generate ./my-app --mode single
```

That's it! 🚀
