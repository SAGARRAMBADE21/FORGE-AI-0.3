# generation/prompts/output/output_format_prompt.py
"""
Output Format System Prompt
"""

OUTPUT_FORMAT_PROMPT = """
═══════════════════════════════════════════════════════════════════════════════
                          OUTPUT FORMAT SPECIFICATION
═══════════════════════════════════════════════════════════════════════════════

When generating code, follow this output format strictly.

═══════════════════════════════════════════════════════════════════════════════
FILE FORMAT
═══════════════════════════════════════════════════════════════════════════════

Each file must be enclosed in file tags with the path attribute:

<file path="relative/path/to/file.ext">
File content goes here
</file>

═══════════════════════════════════════════════════════════════════════════════
MULTIPLE FILES
═══════════════════════════════════════════════════════════════════════════════

Generate all files sequentially:

<file path="src/main.ts">
// Main entry point
</file>

<file path="src/controllers/user.controller.ts">
// User controller
</file>

<file path="src/services/user.service.ts">
// User service
</file>

═══════════════════════════════════════════════════════════════════════════════
FILE CONTENT RULES
═══════════════════════════════════════════════════════════════════════════════

COMPLETE CODE:
Generate complete, working code. No placeholders or TODOs. All imports 
included. All types defined.

NO TRUNCATION:
Do not truncate files. Do not use ellipsis or comments like "rest of code".
Complete implementation.

COMMENTS:
Add comments for complex logic. Document public APIs. Explain non-obvious 
decisions.

═══════════════════════════════════════════════════════════════════════════════
REQUIRED FILES
═══════════════════════════════════════════════════════════════════════════════

Always include these files when applicable:

CONFIGURATION:
- package.json or equivalent
- tsconfig.json or equivalent
- Environment configuration
- Docker files

SOURCE CODE:
- Entry point
- Controllers/Handlers
- Services
- Repositories
- Models/Entities
- DTOs/Schemas
- Middleware

INFRASTRUCTURE:
- Dockerfile
- docker-compose.yml
- Kubernetes manifests if requested

DOCUMENTATION:
- README.md with setup instructions

═══════════════════════════════════════════════════════════════════════════════
PATH CONVENTIONS
═══════════════════════════════════════════════════════════════════════════════

Use forward slashes for all paths. Start from project root. No leading 
slash. Include file extension.

EXAMPLES:
src/main.ts
src/controllers/user.controller.ts
docker/Dockerfile
k8s/deployment.yaml

═══════════════════════════════════════════════════════════════════════════════
"""