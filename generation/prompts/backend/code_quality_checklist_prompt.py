# generation/prompts/backend/code_quality_checklist_prompt.py
"""
Code Quality Checklist - Pre-generation validation
"""

CODE_QUALITY_CHECKLIST_PROMPT = """
<prompt_type>Code Quality Checklist</prompt_type>

<critical_validations>
## Before Generating Code, VERIFY:

### 1. Service Layer Consistency
- ✅ All service __init__ methods match how they're called in routers
- ✅ If Service(db) in router, then def __init__(self, db: AsyncSession)
- ✅ If Service(repository) in router, then def __init__(self, repository: SomeRepository)
- ✅ NO mixing patterns: Service(db) and def __init__(self, repository) is WRONG

### 2. Repository Pattern (If Used)
- ✅ If services reference repositories, repository FILES are generated
- ✅ All repository methods called in services actually exist
- ✅ Repository __init__ takes db: AsyncSession
- ✅ NO phantom repositories (referenced but not created)

### 3. Authentication Completeness
- ✅ If auth is used, generate app/core/security.py with:
  - verify_password()
  - get_password_hash()
  - create_access_token()
  - verify_token()
- ✅ User model has hashed_password field
- ✅ get_current_user dependency exists and works
- ✅ NO undefined auth methods (verify_token, get_user_by_token, etc.)

### 4. Database Configuration
- ✅ Database initialization uses ASYNC: async with engine.begin()
- ✅ NO sync patterns: Base.metadata.create_all(bind=engine)
- ✅ AsyncSession used everywhere
- ✅ get_db() dependency exists in database.py or dependencies.py

### 5. Pydantic V2 Compliance
- ✅ Use model_config = ConfigDict(from_attributes=True)
- ✅ NO orm_mode = True (deprecated)
- ✅ Use pydantic_settings.BaseSettings for config
- ✅ NO from pydantic import BaseSettings (deprecated)
- ✅ Use SettingsConfigDict for config class

### 6. Modern Python Datetime
- ✅ Use datetime.now(timezone.utc)
- ✅ NO datetime.utcnow() (deprecated in Python 3.12+)
- ✅ DateTime columns have timezone=True
- ✅ Use lambda: datetime.now(timezone.utc) for defaults

### 7. CORS Middleware
- ✅ CORSMiddleware added to app in main.py
- ✅ CORS origins configured in settings
- ✅ allow_credentials=True, allow_methods=["*"], allow_headers=["*"]

### 8. Critical Files
- ✅ requirements.txt generated with ALL dependencies
- ✅ .env.example generated with ALL environment variables
- ✅ app/core/config.py with pydantic-settings
- ✅ app/database.py with async session
- ✅ app/dependencies.py with get_db() and auth dependencies

### 9. Data Types
- ✅ Money/prices use Decimal (in Python) or Numeric (in SQLAlchemy)
- ✅ NO Float for money
- ✅ Counts/stock use Integer, NOT Float
- ✅ UUIDs use UUID type with uuid.uuid4()

### 10. HTTP Status Codes
- ✅ POST endpoints return 201 Created
- ✅ DELETE can return 204 No Content
- ✅ 404 for not found
- ✅ 401 for unauthorized
- ✅ 422 for validation errors

### 11. Input Validation
- ✅ Pydantic schemas have field validators for constraints
- ✅ Email uses EmailStr
- ✅ Required fields use Field(...) or are not Optional
- ✅ Min/max validation for strings, numbers

### 12. Method References
- ✅ All methods called actually exist in their classes
- ✅ NO AuthService.verify_token() if verify_token is a standalone function
- ✅ NO UserService.authenticate() without defining it
- ✅ Check method signatures match how they're called

</critical_validations>

<common_errors_to_avoid>
## NEVER Do These (From Real Failed Generations):

### ❌ Undefined Repository Pattern
```python
# WRONG: Service expects repository but it doesn't exist
class ProductService:
    def __init__(self, repository: ProductRepository):  # ❌ ProductRepository not generated
        self._repository = repository
```

### ❌ Service Initialization Mismatch
```python
# WRONG: Router passes db, service expects repository
router: service = ProductService(db)  # ❌ Mismatch
class ProductService:
    def __init__(self, repository: ProductRepository):  # Expects repository, not db!
```

### ❌ Deprecated Pydantic V1
```python
# WRONG
class User(BaseModel):
    class Config:  # ❌ Deprecated
        orm_mode = True  # ❌ Use model_config = ConfigDict(from_attributes=True)
```

### ❌ Deprecated datetime
```python
# WRONG
from datetime import datetime
created_at = Column(DateTime, default=datetime.utcnow)  # ❌ Deprecated
# CORRECT
created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

### ❌ Missing Password Field
```python
# WRONG: Auth without password
class User(Base):
    __tablename__ = "users"
    email = Column(String)
    name = Column(String)
    # ❌ NO hashed_password field - auth won't work!
```

### ❌ Sync Database in Async App
```python
# WRONG
Base.metadata.create_all(bind=engine)  # ❌ Synchronous in async app
# CORRECT
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

### ❌ Missing CORS
```python
# WRONG: No CORS = frontend can't connect
app = FastAPI()
# ❌ Missing CORS middleware
app.include_router(router)
```

### ❌ Float for Money
```python
# WRONG
price = Column(Float, nullable=False)  # ❌ Floating point errors with money
# CORRECT
from sqlalchemy import Numeric
price = Column(Numeric(10, 2), nullable=False)  # Or Decimal in Python
```

</common_errors_to_avoid>

<pre_generation_checklist>
## Run This Checklist Before Generating EVERY File:

1. **Service Files**: Does __init__ match router usage?
2. **Repository**: If referenced, is it generated?
3. **Auth**: Is security.py complete with all functions?
4. **Database**: Is it fully async?
5. **Pydantic**: All v2 patterns?
6. **Datetime**: Using timezone.utc?
7. **CORS**: In main.py?
8. **Config Files**: requirements.txt, .env.example exist?
9. **Data Types**: Decimal for money, Integer for counts?
10. **Methods**: All referenced methods exist?

If ANY answer is NO, FIX IT before generating.
</pre_generation_checklist>

<rules>
<always>
- Run through ENTIRE checklist before generating
- Verify every method you reference actually exists
- Match service initialization with router usage
- Generate ALL files referenced (especially repositories)
- Use modern patterns (Pydantic v2, async DB, timezone.utc)
- Include CORS, critical files, proper data types
</always>

<never>
- Generate references to non-existent methods
- Mix sync and async database code
- Use deprecated patterns
- Skip critical configuration files
- Use Float for money
- Reference repositories without generating them
- Forget CORS middleware
- Skip password field in User model when using auth
</never>
</rules>
"""
