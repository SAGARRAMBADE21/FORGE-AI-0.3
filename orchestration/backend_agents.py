"""
Specialized Backend Agents

This module contains implementations of specialized agents for different
aspects of backend development.
"""

import logging
from typing import Dict, Any, List
import asyncio

from orchestration.agent_orchestrator import (
    BackendSubAgent, AgentRole, AgentTask, MessageType, AgentMessage
)
from generation.llm_generator import LLMGenerator
from generation.prompt_builder import PromptBuilder
from generation.output_parser import OutputParser
from generation.prompts import (
    MASTER_PROMPT,
    ARCHITECTURE_PROMPTS,
    API_PROMPTS,
    DATABASE_PROMPTS,
    AUTH_PROMPTS,
    TESTING_PROMPTS,
    DEVOPS_PROMPTS,
    SECURITY_PROMPTS,
    PRINCIPLES_PROMPTS
)
from config.settings import settings

logger = logging.getLogger(__name__)


class ArchitectAgent(BackendSubAgent):
    """
    System Architect Agent
    
    Responsibilities:
    - Define overall system architecture
    - Make technology decisions
    - Design component interactions
    - Ensure scalability and maintainability
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.ARCHITECT, orchestrator)
        self.capabilities = [
            "architecture_design",
            "technology_selection",
            "component_design",
            "scalability_planning"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        self.prompt_builder = PromptBuilder()
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Design system architecture"""
        logger.info(f"Architect: {task.description}")
        
        context = task.input_data.get("context")
        requirements = task.input_data.get("requirements", [])
        
        # Use comprehensive prompt library instead of inline prompts
        system_prompt = f"""{MASTER_PROMPT}

{ARCHITECTURE_PROMPTS.get('microservices', '')}

{PRINCIPLES_PROMPTS.get('solid', '')}

{PRINCIPLES_PROMPTS.get('clean_code', '')}"""

        user_prompt = f"""
Design backend architecture for:
- Framework: {context.framework if context else 'Node.js/Express'}
- Database: {context.database if context else 'PostgreSQL'}
- Features: {', '.join(requirements)}

Requirements:
{chr(10).join(f'- {req}' for req in requirements)}

Provide:
1. Architectural pattern (monolith/microservices/hybrid)
2. Layer structure
3. Component organization
4. Data flow
5. Technology stack justification
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "architecture_design": response,
            "pattern": "layered_architecture",
            "components": ["api", "services", "repositories", "models"],
            "decisions": {
                "database": context.database if context else "PostgreSQL",
                "framework": context.framework if context else "Express",
                "auth": "JWT"
            }
        }


class DatabaseEngineerAgent(BackendSubAgent):
    """
    Database Engineer Agent
    
    Responsibilities:
    - Design database schemas
    - Create migrations
    - Optimize queries
    - Design indexes
    - Ensure data integrity
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.DATABASE_ENGINEER, orchestrator)
        self.capabilities = [
            "schema_design",
            "migration_generation",
            "query_optimization",
            "index_design"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute database engineering task"""
        logger.info(f"Database Engineer: {task.description}")
        
        if "Design database schema" in task.description:
            return await self._design_schema(task)
        elif "Generate database code" in task.description:
            return await self._generate_code(task)
        else:
            return {"error": "Unknown task"}
    
    async def _design_schema(self, task: AgentTask) -> Dict[str, Any]:
        """Design database schema"""
        models = task.input_data.get("models", [])
        relations = task.input_data.get("relations", [])
        
        # Consult with API engineer about data requirements
        api_requirements = await self.request_help(
            AgentRole.API_ENGINEER,
            "What data access patterns do you need?",
            {"models": models}
        )
        
        # Use comprehensive database prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{DATABASE_PROMPTS.get('sql', '')}

{DATABASE_PROMPTS.get('schema_design', '')}

{DATABASE_PROMPTS.get('indexing', '')}"""

        user_prompt = f"""
Design database schema for models:
{chr(10).join(f'- {m}' for m in models)}

Relations: {relations}

API Requirements: {api_requirements}

Generate:
1. Schema definition (Prisma/TypeORM/SQLAlchemy)
2. Indexes for performance
3. Constraints and validations
4. Migration strategy
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "schema_design": response,
            "models": models,
            "relations": relations,
            "indexes": [],
            "migrations": []
        }
    
    async def _generate_code(self, task: AgentTask) -> Dict[str, Any]:
        """Generate database code"""
        schema = task.input_data.get("schema", {})
        
        # Use database and principles prompts
        system_prompt = f"""{MASTER_PROMPT}

{DATABASE_PROMPTS.get('sql', '')}

{PRINCIPLES_PROMPTS.get('clean_code', '')}"""

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

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "code": response,
            "files": {
                "models": "generated models code",
                "repositories": "generated repository code",
                "migrations": "generated migration code"
            }
        }


class ApiEngineerAgent(BackendSubAgent):
    """
    API Engineer Agent
    
    Responsibilities:
    - Design REST/GraphQL endpoints
    - Define request/response formats
    - Implement controllers/resolvers
    - Design API versioning
    - Write API documentation
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.API_ENGINEER, orchestrator)
        self.capabilities = [
            "api_design",
            "endpoint_generation",
            "validation",
            "documentation"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute API engineering task"""
        logger.info(f"API Engineer: {task.description}")
        
        if "Design API" in task.description:
            return await self._design_api(task)
        elif "Generate API" in task.description:
            return await self._generate_api(task)
        else:
            return {"error": "Unknown task"}
    
    async def _design_api(self, task: AgentTask) -> Dict[str, Any]:
        """Design API structure"""
        resources = task.input_data.get("resources", [])
        architecture = task.input_data.get("architecture", {})
        
        # Use comprehensive API design prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{API_PROMPTS.get('rest', '')}

{API_PROMPTS.get('versioning', '')}

{API_PROMPTS.get('pagination', '')}"""

        user_prompt = f"""
Design API for resources:
{chr(10).join(f'- {r}' for r in resources)}

Architecture: {architecture}

Provide:
1. Endpoint structure
2. Request/response formats
3. Validation rules
4. Error responses
5. API documentation outline
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "api_design": response,
            "endpoints": [],
            "resources": resources
        }
    
    async def _generate_api(self, task: AgentTask) -> Dict[str, Any]:
        """Generate API implementation"""
        api_design = task.input_data.get("api_design", {})
        schema = task.input_data.get("schema", {})
        
        # Coordinate with Service Engineer
        service_info = await self.request_help(
            AgentRole.SERVICE_ENGINEER,
            "What business logic services do I need to call?",
            {"api_design": api_design}
        )
        
        # Use API and security prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{API_PROMPTS.get('rest', '')}

{SECURITY_PROMPTS.get('owasp', '')}

{PRINCIPLES_PROMPTS.get('clean_code', '')}"""

        user_prompt = f"""
Generate API implementation:
Design: {api_design}
Schema: {schema}
Services: {service_info}

Include:
1. Route definitions
2. Controller methods
3. Request validation
4. Response serialization
5. Error handling
6. API documentation
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "code": response,
            "files": {
                "routes": "generated route code",
                "controllers": "generated controller code",
                "validators": "generated validation code"
            }
        }
    
    async def _handle_question(self, message: AgentMessage) -> AgentMessage:
        """Answer questions about API requirements"""
        question = message.content.get("request")
        
        # Provide information about API data patterns
        response_content = {
            "data_access_patterns": [
                "CRUD operations for all resources",
                "Pagination for list endpoints",
                "Search and filtering",
                "Sorting capabilities"
            ],
            "performance_requirements": {
                "response_time": "< 200ms",
                "pagination": "page-based or cursor-based"
            }
        }
        
        return AgentMessage(
            id=f"answer_{message.id}",
            from_agent=self.role,
            to_agent=message.from_agent,
            message_type=MessageType.ANSWER,
            content=response_content,
            timestamp=str(asyncio.get_event_loop().time()),
            in_reply_to=message.id
        )


class ServiceEngineerAgent(BackendSubAgent):
    """
    Service Engineer Agent
    
    Responsibilities:
    - Implement business logic
    - Design service layer
    - Handle transactions
    - Implement business rules
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.SERVICE_ENGINEER, orchestrator)
        self.capabilities = [
            "business_logic",
            "service_layer",
            "transactions",
            "domain_logic"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute service engineering task"""
        logger.info(f"Service Engineer: {task.description}")
        
        service_architecture = task.input_data.get("service_architecture")
        schema = task.input_data.get("schema", {})
        
        # Use architecture and principles prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{ARCHITECTURE_PROMPTS.get('ddd', '')}

{PRINCIPLES_PROMPTS.get('solid', '')}

{PRINCIPLES_PROMPTS.get('clean_code', '')}"""

        user_prompt = f"""
Generate business services for:
Architecture: {service_architecture}
Schema: {schema}

Include:
1. Service classes
2. Business logic methods
3. Transaction handling
4. Validation logic
5. Error handling
6. Helper methods
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "code": response,
            "services": [],
            "files": {
                "services": "generated service code",
                "validators": "business validation code"
            }
        }
    
    async def _handle_question(self, message: AgentMessage) -> AgentMessage:
        """Answer questions about business services"""
        api_design = message.content.get("context", {}).get("api_design")
        
        response_content = {
            "services_needed": [
                "UserService - user management",
                "AuthService - authentication logic",
                "DataService - data operations"
            ],
            "methods": [
                "create", "update", "delete", "findById", "findAll"
            ]
        }
        
        return AgentMessage(
            id=f"answer_{message.id}",
            from_agent=self.role,
            to_agent=message.from_agent,
            message_type=MessageType.ANSWER,
            content=response_content,
            timestamp=str(asyncio.get_event_loop().time()),
            in_reply_to=message.id
        )


class AuthEngineerAgent(BackendSubAgent):
    """
    Authentication & Authorization Engineer
    
    Responsibilities:
    - Implement authentication
    - Design authorization system
    - Secure endpoints
    - Manage sessions/tokens
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.AUTH_ENGINEER, orchestrator)
        self.capabilities = [
            "authentication",
            "authorization",
            "security",
            "session_management"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute authentication/authorization task"""
        logger.info(f"Auth Engineer: {task.description}")
        
        if "Design authentication" in task.description:
            return await self._design_auth(task)
        elif "Generate auth" in task.description:
            return await self._generate_auth(task)
        else:
            return {"error": "Unknown task"}
    
    async def _design_auth(self, task: AgentTask) -> Dict[str, Any]:
        """Design authentication system"""
        auth_requirements = task.input_data.get("auth_requirements")
        
        # Use comprehensive auth and security prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{AUTH_PROMPTS.get('jwt', '')}

{AUTH_PROMPTS.get('oauth2', '')}

{SECURITY_PROMPTS.get('rbac', '')}

{SECURITY_PROMPTS.get('owasp', '')}"""

        user_prompt = f"""
Design authentication system for:
Requirements: {auth_requirements}

Provide:
1. Authentication strategy
2. Authorization approach (RBAC/ABAC)
3. Token management
4. Security measures
5. Implementation plan
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "auth_design": response,
            "strategy": "JWT",
            "features": ["login", "register", "refresh", "logout"]
        }
    
    async def _generate_auth(self, task: AgentTask) -> Dict[str, Any]:
        """Generate auth implementation"""
        auth_design = task.input_data.get("auth_design", {})
        
        # Use auth and security prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{AUTH_PROMPTS.get('jwt', '')}

{SECURITY_PROMPTS.get('owasp', '')}

{SECURITY_PROMPTS.get('encryption', '')}"""

        user_prompt = f"""
Generate authentication code for:
{auth_design}

Include:
1. Auth service
2. JWT middleware
3. Password hashing
4. Login/register endpoints
5. Token validation
6. Permission checks
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "code": response,
            "files": {
                "auth_service": "auth service code",
                "middleware": "auth middleware code",
                "utils": "security utilities"
            }
        }


class TestingEngineerAgent(BackendSubAgent):
    """
    Testing Engineer Agent
    
    Responsibilities:
    - Generate unit tests
    - Generate integration tests
    - Design test scenarios
    - Ensure code coverage
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.TESTING_ENGINEER, orchestrator)
        self.capabilities = [
            "unit_testing",
            "integration_testing",
            "test_coverage",
            "test_design"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Generate comprehensive tests"""
        logger.info(f"Testing Engineer: {task.description}")
        
        implementation = task.input_data.get("implementation", [])
        context = task.input_data.get("context")
        
        # Use comprehensive testing prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{TESTING_PROMPTS.get('unit_testing', '')}

{TESTING_PROMPTS.get('integration_testing', '')}

{TESTING_PROMPTS.get('tdd_bdd', '')}"""

        user_prompt = f"""
Generate tests for implementation:
{implementation}

Framework: {context.framework if context else 'Jest/Mocha'}

Include:
1. Unit tests
2. Integration tests
3. Test fixtures
4. Mock data
5. Test utilities
6. Coverage configuration
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "code": response,
            "files": {
                "unit_tests": "unit test code",
                "integration_tests": "integration test code",
                "fixtures": "test fixtures",
                "config": "test configuration"
            }
        }


class DevOpsEngineerAgent(BackendSubAgent):
    """
    DevOps Engineer Agent
    
    Responsibilities:
    - Create Docker configurations
    - Design CI/CD pipelines
    - Generate deployment configs
    - Setup monitoring
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.DEVOPS_ENGINEER, orchestrator)
        self.capabilities = [
            "docker",
            "ci_cd",
            "deployment",
            "monitoring"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Generate deployment configurations"""
        logger.info(f"DevOps Engineer: {task.description}")
        
        architecture = task.input_data.get("architecture", {})
        context = task.input_data.get("context")
        
        # Use comprehensive DevOps prompts from library
        system_prompt = f"""{MASTER_PROMPT}

{DEVOPS_PROMPTS.get('docker', '')}

{DEVOPS_PROMPTS.get('kubernetes', '')}

{DEVOPS_PROMPTS.get('cicd', '')}

{DEVOPS_PROMPTS.get('monitoring', '')}"""

        user_prompt = f"""
Generate deployment configs for:
Architecture: {architecture}
Database: {context.database if context else 'PostgreSQL'}

Include:
1. Dockerfile
2. docker-compose.yml
3. CI/CD pipeline (GitHub Actions/GitLab CI)
4. Environment variables template
5. Deployment scripts
6. Monitoring configuration
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "code": response,
            "files": {
                "Dockerfile": "dockerfile content",
                "docker-compose.yml": "compose config",
                "ci_cd": "pipeline config",
                ".env.example": "environment template"
            }
        }


class CodeReviewerAgent(BackendSubAgent):
    """
    Code Reviewer Agent
    
    Responsibilities:
    - Review generated code
    - Suggest optimizations
    - Ensure best practices
    - Check security issues
    - Improve code quality
    """
    
    def __init__(self, orchestrator):
        super().__init__(AgentRole.CODE_REVIEWER, orchestrator)
        self.capabilities = [
            "code_review",
            "optimization",
            "security_audit",
            "quality_check"
        ]
        self.llm = LLMGenerator(
            provider=settings.llm.backend_provider,
            model=settings.llm.backend_model
        )
        
    async def execute_task(self, task: AgentTask) -> Dict[str, Any]:
        """Review and optimize code"""
        logger.info(f"Code Reviewer: {task.description}")
        
        implementation = task.input_data.get("implementation", [])
        tests = task.input_data.get("tests", {})
        devops = task.input_data.get("devops", {})
        
        # Use comprehensive review prompts combining multiple domains
        system_prompt = f"""{MASTER_PROMPT}

{SECURITY_PROMPTS.get('owasp', '')}

{PRINCIPLES_PROMPTS.get('clean_code', '')}

{PRINCIPLES_PROMPTS.get('solid', '')}

{TESTING_PROMPTS.get('unit_testing', '')}"""

        user_prompt = f"""
Review all generated code:

Implementation: {implementation}
Tests: {tests}
DevOps: {devops}

Provide:
1. Overall assessment
2. Security issues (if any)
3. Performance optimizations
4. Code quality improvements
5. Documentation gaps
6. Recommended changes
"""

        response = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )
        
        return {
            "review": response,
            "issues": [],
            "recommendations": [],
            "approved": True
        }
    
    async def _handle_proposal(self, message: AgentMessage) -> AgentMessage:
        """Review and approve/reject proposals"""
        solution = message.content
        
        # Quick review
        approved = True  # Simplified - in real implementation, do actual review
        
        return AgentMessage(
            id=f"review_{message.id}",
            from_agent=self.role,
            to_agent=message.from_agent,
            message_type=MessageType.APPROVAL if approved else MessageType.REJECTION,
            content={
                "approved": approved,
                "feedback": "Looks good!" if approved else "Needs improvements"
            },
            timestamp=str(asyncio.get_event_loop().time()),
            in_reply_to=message.id
        )
