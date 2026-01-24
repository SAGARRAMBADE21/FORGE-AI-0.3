# generation/prompt_builder.py
"""
Prompt Builder - Builds system and user prompts

This module provides both legacy and industry-standard XML-based prompt building.
The XML format follows the same structure used by Cursor, Claude Code, and 
other production AI coding assistants.
"""

from typing import Any, Dict, Optional

from .prompts import (
    API_PROMPTS,
    ARCHITECTURE_PROMPTS,
    AUTH_PROMPTS,
    DATABASE_PROMPTS,
    DEVOPS_PROMPTS,
    FRAMEWORK_PROMPTS,
    LANGUAGE_PROMPTS,
    MASTER_PROMPT,
    ML_INFERENCE_PROMPTS,
    OUTPUT_FORMAT_PROMPT,
    PERFORMANCE_PROMPTS,
    PRINCIPLES_PROMPTS,
    SECURITY_PROMPTS,
    TESTING_PROMPTS,
    # New XML-based prompts
    build_system_prompt as build_xml_system_prompt,
    build_generation_prompt as build_xml_generation_prompt,
)
from .prompts.backend import (
    ERROR_HANDLING_PROMPT,
    VALIDATION_PROMPT,
    MIDDLEWARE_PROMPT,
    BACKEND_MASTER_PROMPT,
    BUSINESS_LOGIC_PROMPT,
    OBSERVABILITY_PROMPT,
    HTTP_FUNDAMENTALS_PROMPT,
)


class PromptBuilder:
    """
    Builds combined prompts for LLM generation
    """

    def build_system_prompt(
        self,
        stage: str,
        language: str,
        framework: str,
        architecture: str,
        features: Optional[list] = None,
        database: Optional[str] = None,
    ) -> str:
        """
        Build MAXIMUM system prompt utilizing ALL backend knowledge.
        
        FORGE is focused on backend - this includes ALL relevant prompts:
        - ALL security prompts (OWASP, encryption, secrets, RBAC, vulnerability scanning)
        - ALL principles (SOLID, Clean Code, DRY/KISS/YAGNI, Design Patterns)
        - ALL database knowledge (SQL, NoSQL, indexing, transactions, schema, sharding)
        - ALL API best practices (REST, GraphQL, gRPC, pagination, rate limiting, versioning)
        - ALL backend patterns (error handling, validation, middleware, business logic)
        - ALL auth patterns (JWT, OAuth2, SSO, MFA, session management)
        - ALL performance (caching, scaling, load balancing, message queues)
        - ALL testing (unit, integration, e2e, load, contract, TDD)
        - ALL DevOps (Docker, CI/CD, Kubernetes, monitoring)
        """
        prompts = [MASTER_PROMPT]

        # =========================================
        # BACKEND MASTER (Comprehensive guidance)
        # =========================================
        prompts.append(BACKEND_MASTER_PROMPT)

        # =========================================
        # CORE STACK (Language + Framework + Arch)
        # =========================================
        if architecture in ARCHITECTURE_PROMPTS:
            prompts.append(ARCHITECTURE_PROMPTS[architecture])

        if language in LANGUAGE_PROMPTS:
            prompts.append(LANGUAGE_PROMPTS[language])

        if framework in FRAMEWORK_PROMPTS:
            prompts.append(FRAMEWORK_PROMPTS[framework])

        # =========================================
        # ALL DATABASE KNOWLEDGE
        # =========================================
        for db_key, db_prompt in DATABASE_PROMPTS.items():
            if database and db_key == database:
                prompts.append(db_prompt)  # Primary database first
        # Then add all database knowledge
        for db_key in ["sql", "nosql", "indexing", "transactions", "schema_design", "sharding_replication"]:
            if db_key in DATABASE_PROMPTS:
                prompts.append(DATABASE_PROMPTS[db_key])

        # =========================================
        # ALL API KNOWLEDGE
        # =========================================
        for api_key in ["rest", "graphql", "grpc", "pagination", "rate_limiting", "versioning"]:
            if api_key in API_PROMPTS:
                prompts.append(API_PROMPTS[api_key])

        # =========================================
        # ALL BACKEND PATTERNS
        # =========================================
        prompts.append(ERROR_HANDLING_PROMPT)
        prompts.append(VALIDATION_PROMPT)
        prompts.append(MIDDLEWARE_PROMPT)
        prompts.append(BUSINESS_LOGIC_PROMPT)
        prompts.append(HTTP_FUNDAMENTALS_PROMPT)
        prompts.append(OBSERVABILITY_PROMPT)

        # =========================================
        # ALL SECURITY KNOWLEDGE
        # =========================================
        for sec_key in ["owasp", "encryption", "rbac", "secrets_management", "vulnerability_scanning"]:
            if sec_key in SECURITY_PROMPTS:
                prompts.append(SECURITY_PROMPTS[sec_key])

        # =========================================
        # ALL AUTH KNOWLEDGE
        # =========================================
        for auth_key in ["jwt", "oauth2", "session_management", "sso", "mfa", "ldap"]:
            if auth_key in AUTH_PROMPTS:
                prompts.append(AUTH_PROMPTS[auth_key])

        # =========================================
        # ALL PERFORMANCE KNOWLEDGE
        # =========================================
        for perf_key in ["caching", "scaling", "load_balancing", "message_queue", "disaster_recovery"]:
            if perf_key in PERFORMANCE_PROMPTS:
                prompts.append(PERFORMANCE_PROMPTS[perf_key])

        # =========================================
        # ALL DEVOPS KNOWLEDGE
        # =========================================
        for devops_key in ["docker", "cicd", "kubernetes", "monitoring", "terraform"]:
            if devops_key in DEVOPS_PROMPTS:
                prompts.append(DEVOPS_PROMPTS[devops_key])

        # =========================================
        # ALL TESTING KNOWLEDGE
        # =========================================
        for test_key in ["unit_testing", "integration_testing", "e2e_testing", "load_testing", "contract_testing", "tdd_bdd"]:
            if test_key in TESTING_PROMPTS:
                prompts.append(TESTING_PROMPTS[test_key])

        # =========================================
        # ALL PRINCIPLES
        # =========================================
        for principle in ["solid", "clean_code", "dry_kiss_yagni", "design_patterns"]:
            if principle in PRINCIPLES_PROMPTS:
                prompts.append(PRINCIPLES_PROMPTS[principle])

        # =========================================
        # OUTPUT FORMAT
        # =========================================
        prompts.append(OUTPUT_FORMAT_PROMPT)

        # Remove duplicates while preserving order
        seen = set()
        unique_prompts = []
        for p in prompts:
            if p and p not in seen:
                seen.add(p)
                unique_prompts.append(p)

        return "\n\n".join(unique_prompts)


    def build_user_prompt(self, stage: str, context: Any) -> str:
        """
        Build user prompt with context
        """
        return f"""
<generation_request>
    <stage>{stage}</stage>
    <project_name>{context.project_name}</project_name>
    <language>{context.language}</language>
    <framework>{context.framework}</framework>
    <database>{context.database}</database>
    <architecture>{context.architecture}</architecture>
    <features>{', '.join(context.features)}</features>
</generation_request>

<inferred_specification>
{self._format_spec(context.inferred_spec)}
</inferred_specification>

<synthesized_design>
{self._format_spec(context.synthesized_design)}
</synthesized_design>

<already_generated_files>
{self._format_generated_files(context.generated_files)}
</already_generated_files>

Generate the {stage} layer code following all system prompt guidelines.
Output using the specified file format.
"""

    def build_single_file_prompt(
        self, file_type: str, language: str, framework: str
    ) -> str:
        """Build prompt for single file generation"""
        prompts = [MASTER_PROMPT]

        if language in LANGUAGE_PROMPTS:
            prompts.append(LANGUAGE_PROMPTS[language])

        if framework in FRAMEWORK_PROMPTS:
            prompts.append(FRAMEWORK_PROMPTS[framework])

        prompts.append(OUTPUT_FORMAT_PROMPT)

        return "\n\n".join(filter(None, prompts))

    def _get_relevant_prompt(
        self, prompt_dict: Dict[str, str], features: Optional[list]
    ) -> str:
        """Get relevant prompts based on features"""
        if not features:
            return list(prompt_dict.values())[0] if prompt_dict else ""

        prompts = []
        for feature in features:
            if feature in prompt_dict:
                prompts.append(prompt_dict[feature])

        return "\n\n".join(prompts) if prompts else list(prompt_dict.values())[0]

    def _format_spec(self, spec: Dict[str, Any]) -> str:
        """Format specification for prompt"""
        if not spec:
            return "No specification provided"

        import json

        return json.dumps(spec, indent=2, default=str)

    def _format_generated_files(self, files: Dict[str, str]) -> str:
        """Format already generated files"""
        if not files:
            return "No files generated yet"

        result = []
        for filepath, content in files.items():
            # Include just file structure, not full content
            result.append(f"- {filepath}")

        return "\n".join(result)

    # =========================================================================
    # NEW: Industry-Standard XML-Based Prompt Methods
    # =========================================================================

    def build_xml_system_prompt(
        self,
        stage: str,
        language: str,
        framework: str,
        database: str,
        architecture: str,
        features: Optional[list] = None,
    ) -> str:
        """
        Build system prompt using industry-standard XML format.
        
        This format follows the same structure used by Cursor, Claude Code,
        GitHub Copilot, and other production AI coding assistants.
        
        Args:
            stage: Generation stage (e.g., 'api', 'database', 'auth')
            language: Target language (e.g., 'python', 'javascript')
            framework: Target framework (e.g., 'fastapi', 'express')
            database: Target database (e.g., 'postgresql', 'mongodb')
            architecture: Architecture style (e.g., 'layered', 'microservices')
            features: List of features to include
            
        Returns:
            Complete XML-formatted system prompt
        """
        return build_xml_generation_prompt(
            stage=stage,
            language=language,
            framework=framework,
            database=database,
            architecture=architecture,
            features=features or [],
        )

    def build_xml_user_prompt(self, stage: str, context: Any) -> str:
        """
        Build user prompt with XML structure for generation request.
        
        This complements build_xml_system_prompt() by providing structured
        context in the same XML format.
        """
        import json
        
        return f"""
<generation_request>
<stage>{stage}</stage>
<project>
    <name>{context.project_name}</name>
    <language>{context.language}</language>
    <framework>{context.framework}</framework>
    <database>{context.database}</database>
    <architecture>{context.architecture}</architecture>
    <features>{', '.join(context.features)}</features>
</project>
</generation_request>

<inferred_specification>
{self._format_spec(context.inferred_spec)}
</inferred_specification>

<synthesized_design>
{self._format_spec(context.synthesized_design)}
</synthesized_design>

<generated_files>
{self._format_generated_files(context.generated_files)}
</generated_files>

<task>
Generate the {stage} layer code following all system prompt guidelines.
Output using the specified file format.
</task>
"""

