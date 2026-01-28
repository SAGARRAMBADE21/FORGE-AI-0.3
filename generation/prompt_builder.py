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
    CRITICAL_FILES_PROMPT,
    CODE_QUALITY_CHECKLIST_PROMPT,
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
        Build OPTIMIZED system prompt with strategic knowledge selection.
        
        This balances comprehensive knowledge with prompt size to avoid
        the "lost in the middle" problem where LLMs miss critical instructions
        in very long prompts.
        
        Strategy:
        - OUTPUT_FORMAT at START and END (reinforcement)
        - Core stack (language, framework, arch) always included
        - Stage-specific knowledge prioritized
        - Essential security (OWASP) always included
        - Core principles (SOLID, Clean Code) always included
        
        Target: ~40-50K characters (~10-12K tokens) - well within context limits
        """
        prompts = []
        
        # =========================================
        # OUTPUT FORMAT - START (Critical - must follow!)
        # =========================================
        prompts.append(OUTPUT_FORMAT_PROMPT)
        prompts.append(CODE_QUALITY_CHECKLIST_PROMPT)  # Pre-generation validation
        
        # =========================================
        # MASTER PROMPTS
        # =========================================
        prompts.append(MASTER_PROMPT)
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
        # DATABASE (Only selected + core knowledge)
        # =========================================
        if database and database in DATABASE_PROMPTS:
            prompts.append(DATABASE_PROMPTS[database])
        # Add core database knowledge
        for db_key in ["sql", "indexing", "transactions"]:
            if db_key in DATABASE_PROMPTS:
                prompts.append(DATABASE_PROMPTS[db_key])

        # =========================================
        # API KNOWLEDGE (Core APIs)
        # =========================================
        for api_key in ["rest", "pagination", "rate_limiting"]:
            if api_key in API_PROMPTS:
                prompts.append(API_PROMPTS[api_key])

        # =========================================
        # BACKEND PATTERNS (Essential)
        # =========================================
        prompts.append(ERROR_HANDLING_PROMPT)
        prompts.append(VALIDATION_PROMPT)
        prompts.append(MIDDLEWARE_PROMPT)
        prompts.append(HTTP_FUNDAMENTALS_PROMPT)
        prompts.append(CRITICAL_FILES_PROMPT)  # CRITICAL: Always include

        # =========================================
        # SECURITY (Essential - OWASP always)
        # =========================================
        if "owasp" in SECURITY_PROMPTS:
            prompts.append(SECURITY_PROMPTS["owasp"])

        # =========================================
        # AUTH (Based on features)
        # =========================================
        features = features or []
        if any(f in features for f in ["auth", "authentication", "jwt"]):
            for auth_key in ["jwt", "oauth2"]:
                if auth_key in AUTH_PROMPTS:
                    prompts.append(AUTH_PROMPTS[auth_key])

        # =========================================
        # PRINCIPLES (Core only)
        # =========================================
        for principle in ["solid", "clean_code"]:
            if principle in PRINCIPLES_PROMPTS:
                prompts.append(PRINCIPLES_PROMPTS[principle])

        # =========================================
        # TESTING (If feature requested)
        # =========================================
        if "testing" in features:
            for test_key in ["unit_testing", "integration_testing"]:
                if test_key in TESTING_PROMPTS:
                    prompts.append(TESTING_PROMPTS[test_key])

        # =========================================
        # DEVOPS (If feature requested)
        # =========================================
        if any(f in features for f in ["docker", "kubernetes", "devops"]):
            for devops_key in ["docker", "cicd"]:
                if devops_key in DEVOPS_PROMPTS:
                    prompts.append(DEVOPS_PROMPTS[devops_key])

        # =========================================
        # OUTPUT FORMAT - END (Reinforcement!)
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
        # Build comprehensive model spec from context
        model_spec = self._build_model_spec(context)
        design_spec = self._build_design_spec(context)
        
        return f"""
<generation_request>
    <stage>{stage}</stage>
    <project_name>{context.project_name or 'backend'}</project_name>
    <language>{context.language}</language>
    <framework>{context.framework}</framework>
    <database>{context.database}</database>
    <architecture>{context.architecture or 'layered'}</architecture>
    <features>{', '.join(context.features) if context.features else ''}</features>
</generation_request>

<data_models>
{model_spec}
</data_models>

<api_resources>
{design_spec}
</api_resources>

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

    def _build_model_spec(self, context: Any) -> str:
        """Build model specification from context models."""
        if not context.models:
            return "No models specified"
        
        import json
        models_data = []
        for model in context.models:
            model_info = {
                "name": model.name,
                "fields": [],
                "primary_key": getattr(model, "primary_key", "id"),
                "timestamps": getattr(model, "timestamps", True),
            }
            for field in model.fields:
                field_info = {
                    "name": field.name,
                    "type": field.field_type.value if hasattr(field.field_type, "value") else str(field.field_type),
                    "nullable": getattr(field, "nullable", False),
                    "unique": getattr(field, "unique", False),
                }
                if hasattr(field, "constraints") and field.constraints:
                    field_info["constraints"] = field.constraints
                if hasattr(field, "relation_to") and field.relation_to:
                    field_info["relation_to"] = field.relation_to
                model_info["fields"].append(field_info)
            models_data.append(model_info)
        
        return json.dumps(models_data, indent=2, default=str)

    def _build_design_spec(self, context: Any) -> str:
        """Build API design specification from context."""
        if not context.api_resources:
            return "No API resources specified"
        
        import json
        api_data = []
        for resource in context.api_resources:
            resource_info = {
                "name": getattr(resource, "name", str(resource)),
                "endpoints": [],
            }
            if hasattr(resource, "endpoints"):
                for endpoint in resource.endpoints:
                    ep_info = {
                        "method": getattr(endpoint, "method", "GET"),
                        "path": getattr(endpoint, "path", ""),
                    }
                    resource_info["endpoints"].append(ep_info)
            api_data.append(resource_info)
        
        return json.dumps(api_data, indent=2, default=str)

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

