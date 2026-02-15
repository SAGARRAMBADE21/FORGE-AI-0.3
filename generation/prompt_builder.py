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
        """Build ENHANCED model specification from context models with full details."""
        if not context.models:
            return "No models specified"
        
        import json
        models_data = []
        
        # Build relation map for quick lookup
        relation_map = {}
        if context.relations:
            for rel in context.relations:
                source = getattr(rel, 'source_model', getattr(rel, 'from_model', None))
                if source:
                    if source not in relation_map:
                        relation_map[source] = []
                    relation_map[source].append(rel)
        
        for model in context.models:
            model_info = {
                "name": model.name,
                "table_name": self._pluralize(model.name.lower()),
                "fields": [],
                "primary_key": getattr(model, "primary_key", "id"),
                "timestamps": getattr(model, "timestamps", True),
                "indexes": getattr(model, "indexes", []),
                "relations": [],
            }
            
            # Add relations for this model
            if model.name in relation_map:
                for rel in relation_map[model.name]:
                    rel_info = {
                        "type": getattr(rel, 'relation_type', getattr(rel, 'type', 'unknown')).value if hasattr(getattr(rel, 'relation_type', getattr(rel, 'type', 'unknown')), 'value') else str(getattr(rel, 'relation_type', getattr(rel, 'type', 'unknown'))),
                        "to_model": getattr(rel, 'target_model', getattr(rel, 'to_model', None)),
                        "field": getattr(rel, 'source_field', getattr(rel, 'field', None)),
                    }
                    model_info["relations"].append(rel_info)
            
            for field in model.fields:
                field_type = field.field_type
                field_type_str = field_type.value if hasattr(field_type, "value") else str(field_type)
                
                field_info = {
                    "name": field.name,
                    "type": field_type_str,
                    "nullable": getattr(field, "nullable", False),
                    "unique": getattr(field, "unique", False),
                    "indexed": getattr(field, "indexed", False),
                    "primary_key": getattr(field, "primary_key", False),
                }
                
                # Add default value if exists
                if hasattr(field, "default_value") and field.default_value is not None:
                    field_info["default"] = str(field.default_value)
                
                # Add description if exists
                if hasattr(field, "description") and field.description:
                    field_info["description"] = field.description
                
                # Add constraints (min/max length, regex, etc.)
                constraints = getattr(field, "constraints", {}) or {}
                if constraints:
                    field_info["constraints"] = constraints
                
                # Add validation rules
                validations = {}
                if hasattr(field, "min_length") and field.min_length is not None:
                    validations["min_length"] = field.min_length
                if hasattr(field, "max_length") and field.max_length is not None:
                    validations["max_length"] = field.max_length
                if hasattr(field, "min_value") and field.min_value is not None:
                    validations["min_value"] = field.min_value
                if hasattr(field, "max_value") and field.max_value is not None:
                    validations["max_value"] = field.max_value
                if hasattr(field, "pattern") and field.pattern:
                    validations["pattern"] = field.pattern
                if validations:
                    field_info["validations"] = validations
                
                # Add relation info
                if hasattr(field, "relation_to") and field.relation_to:
                    field_info["relation"] = {
                        "to_model": field.relation_to,
                        "type": getattr(field, "relation_type", "many_to_one"),
                    }
                
                # Add foreign key info
                if hasattr(field, "foreign_key") and field.foreign_key:
                    field_info["foreign_key"] = field.foreign_key
                
                model_info["fields"].append(field_info)
            
            models_data.append(model_info)
        
        return json.dumps(models_data, indent=2, default=str)

    def _build_design_spec(self, context: Any) -> str:
        """Build ENHANCED API design specification with full endpoint details."""
        if not context.api_resources:
            return "No API resources specified"
        
        import json
        api_data = []
        
        for resource in context.api_resources:
            resource_info = {
                "name": getattr(resource, "name", str(resource)),
                "base_path": getattr(resource, "base_path", f"/{getattr(resource, 'name', '').lower()}"),
                "model": getattr(resource, "model", None),
                "endpoints": [],
                "middleware": getattr(resource, "middleware", []),
            }
            
            if hasattr(resource, "endpoints"):
                for endpoint in resource.endpoints:
                    ep_info = {
                        "method": getattr(endpoint, "method", "GET"),
                        "path": getattr(endpoint, "path", ""),
                        "description": getattr(endpoint, "description", ""),
                        "requires_auth": getattr(endpoint, "requires_auth", False),
                        "permissions": getattr(endpoint, "permissions", []),
                    }
                    
                    # Add path parameters
                    if hasattr(endpoint, "path_params") and endpoint.path_params:
                        ep_info["path_params"] = [
                            {
                                "name": getattr(p, "name", str(p)),
                                "type": getattr(p, "param_type", "string"),
                                "required": getattr(p, "required", True),
                                "description": getattr(p, "description", ""),
                            }
                            for p in endpoint.path_params
                        ]
                    
                    # Add query parameters
                    if hasattr(endpoint, "query_params") and endpoint.query_params:
                        ep_info["query_params"] = [
                            {
                                "name": getattr(q, "name", str(q)),
                                "type": getattr(q, "param_type", "string"),
                                "required": getattr(q, "required", False),
                                "description": getattr(q, "description", ""),
                            }
                            for q in endpoint.query_params
                        ]
                    
                    # Add request body schema
                    if hasattr(endpoint, "request_body") and endpoint.request_body:
                        req_body = endpoint.request_body
                        ep_info["request_body"] = {
                            "required": getattr(req_body, "required", True),
                            "content_type": getattr(req_body, "content_type", "application/json"),
                            "schema": self._extract_schema_fields(getattr(req_body, "schema", None)),
                        }
                    
                    # Add response schemas
                    if hasattr(endpoint, "responses") and endpoint.responses:
                        ep_info["responses"] = []
                        for resp in endpoint.responses:
                            resp_info = {
                                "status_code": getattr(resp, "status_code", 200),
                                "description": getattr(resp, "description", ""),
                                "content_type": getattr(resp, "content_type", "application/json"),
                            }
                            if hasattr(resp, "schema") and resp.schema:
                                resp_info["schema"] = self._extract_schema_fields(resp.schema)
                            ep_info["responses"].append(resp_info)
                    elif hasattr(endpoint, "response_schema") and endpoint.response_schema:
                        ep_info["response_schema"] = self._extract_schema_fields(endpoint.response_schema)
                    
                    resource_info["endpoints"].append(ep_info)
            
            api_data.append(resource_info)
        
        return json.dumps(api_data, indent=2, default=str)
    
    def _extract_schema_fields(self, schema) -> dict:
        """Extract field information from a schema object."""
        if not schema:
            return {}
        
        if isinstance(schema, dict):
            return schema
        
        if hasattr(schema, "fields"):
            return {
                "type": "object",
                "fields": [
                    {
                        "name": getattr(f, "name", str(f)),
                        "type": getattr(f, "field_type", getattr(f, "type", "string")),
                        "required": getattr(f, "required", False),
                    }
                    for f in schema.fields
                ]
            }
        
        if hasattr(schema, "properties"):
            return {
                "type": "object",
                "properties": schema.properties,
            }
        
        return {"type": str(schema)}

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

    def _pluralize(self, word: str) -> str:
        """Simple pluralization for table names."""
        if word.endswith('s') or word.endswith('x') or word.endswith('z') or word.endswith('ch') or word.endswith('sh'):
            return word + 'es'
        elif word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
            return word[:-1] + 'ies'
        elif word.endswith('o') and len(word) > 1 and word[-2] not in 'aeiou':
            return word + 'es'
        else:
            return word + 's'

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

