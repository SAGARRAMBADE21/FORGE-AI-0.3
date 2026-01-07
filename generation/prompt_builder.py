# generation/prompt_builder.py
"""
Prompt Builder - Builds system and user prompts
"""

from typing import Dict, Any, Optional
from .prompts import (
    MASTER_PROMPT,
    ARCHITECTURE_PROMPTS,
    API_PROMPTS,
    DATABASE_PROMPTS,
    SECURITY_PROMPTS,
    AUTH_PROMPTS,
    DEVOPS_PROMPTS,
    PERFORMANCE_PROMPTS,
    TESTING_PROMPTS,
    PRINCIPLES_PROMPTS,
    LANGUAGE_PROMPTS,
    FRAMEWORK_PROMPTS,
    ML_INFERENCE_PROMPTS,
    OUTPUT_FORMAT_PROMPT
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
        features: Optional[list] = None
    ) -> str:
        """
        Build system prompt for a generation stage
        """
        prompts = [MASTER_PROMPT]
        
        # Add architecture prompt
        if architecture in ARCHITECTURE_PROMPTS:
            prompts.append(ARCHITECTURE_PROMPTS[architecture])
        
        # Add language prompt
        if language in LANGUAGE_PROMPTS:
            prompts.append(LANGUAGE_PROMPTS[language])
            
        # Add framework prompt
        if framework in FRAMEWORK_PROMPTS:
            prompts.append(FRAMEWORK_PROMPTS[framework])
        
        # Add stage-specific prompts
        stage_prompts = {
            "architecture": ARCHITECTURE_PROMPTS,
            "database": DATABASE_PROMPTS,
            "api": API_PROMPTS,
            "auth": AUTH_PROMPTS,
            "security": SECURITY_PROMPTS,
            "devops": DEVOPS_PROMPTS,
            "performance": PERFORMANCE_PROMPTS,
            "testing": TESTING_PROMPTS,
        }
        
        if stage in stage_prompts:
            prompts.append(self._get_relevant_prompt(stage_prompts[stage], features))
        
        # Add principles
        prompts.append(PRINCIPLES_PROMPTS.get("clean_code", ""))
        prompts.append(PRINCIPLES_PROMPTS.get("solid", ""))
        
        # Add output format
        prompts.append(OUTPUT_FORMAT_PROMPT)
        
        return "\n\n".join(filter(None, prompts))
    
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
        self,
        file_type: str,
        language: str,
        framework: str
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
        self,
        prompt_dict: Dict[str, str],
        features: Optional[list]
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