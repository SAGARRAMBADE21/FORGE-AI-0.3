# generation/prompts/output/output_format_prompt.py
"""
Output Format System Prompt - Industry Standard XML Format
"""

OUTPUT_FORMAT_PROMPT = """
<prompt_type>Code Output Format</prompt_type>

<output_format>
## CRITICAL: File Generation Format

You MUST use this EXACT format for EVERY file you generate:

### FILE: path/to/file.ext
```language
complete file content here
```

### FILE: path/to/another.ext
```language
complete file content here
```

### Example Output
### FILE: app/models/user.py
```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### FILE: app/schemas/user.py
```python
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
```

## IMPORTANT INSTRUCTIONS
1. Generate MANY complete files (aim for 10-20+ files per response)
2. Include ALL necessary files: models, schemas, routers, services, middleware, config
3. Each file must be COMPLETE and RUNNABLE - NO placeholders, NO undefined methods
4. DO NOT generate partial files or placeholders
5. Use the ### FILE: format EXACTLY as shown above
6. VERIFY all methods you call exist before generating references
7. ALWAYS generate requirements.txt (Python) or package.json (Node.js)
8. ALWAYS generate .env.example with all environment variables
9. ALWAYS generate config files with proper settings management
10. IF you use repository pattern, GENERATE the repository files too
</output_format>

<formatting_rules>
## Code Formatting

### Indentation
- Python: 4 spaces
- JavaScript/TypeScript: 2 spaces
- Java: 4 spaces
- Go: tabs (gofmt standard)

### Imports
- Group imports by type (standard library, third-party, local)
- Sort alphabetically within groups
- One blank line between groups

### Comments
- Use docstrings for functions and classes
- Inline comments for complex logic
- TODO format: `# TODO(username): description`

### Naming Conventions
| Language | Variables | Functions | Classes | Constants |
|----------|-----------|-----------|---------|-----------|
| Python | snake_case | snake_case | PascalCase | UPPER_SNAKE |
| JavaScript | camelCase | camelCase | PascalCase | UPPER_SNAKE |
| Java | camelCase | camelCase | PascalCase | UPPER_SNAKE |
| Go | camelCase | CamelCase* | PascalCase | CamelCase |

*Exported functions start with uppercase
</formatting_rules>

<file_organization>
## Project Structure

### Python (FastAPI)
```
project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── routers/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── schemas/
│   └── utils/
├── tests/
├── pyproject.toml
└── .env.example
```

### Node.js (Express)
```
project/
├── src/
│   ├── index.js
│   ├── app.js
│   ├── config/
│   ├── routes/
│   ├── controllers/
│   ├── services/
│   ├── models/
│   └── middleware/
├── tests/
├── package.json
└── .env.example
```
</file_organization>

<rules>
<always>
- Generate complete, runnable files
- Include all necessary imports
- Add proper file headers
- Follow framework conventions
- Include type hints/annotations
- Add comprehensive docstrings
</always>
<never>
- Leave TODO placeholders
- Skip imports
- Use incomplete code snippets
- Mix formatting styles
- Forget configuration files
</never>
</rules>
"""
