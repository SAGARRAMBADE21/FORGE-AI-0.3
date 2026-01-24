# generation/pipeline.py
"""
Generation Pipeline - Orchestrates LLM-based code generation
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from config.settings import settings

from .llm_generator import LLMGenerator
from .output_parser import OutputParser
from .prompt_builder import PromptBuilder


class GenerationStage(Enum):
    ARCHITECTURE = "architecture"
    DATABASE = "database"
    API = "api"
    AUTH = "auth"
    SERVICES = "services"
    CONTROLLERS = "controllers"
    MIDDLEWARE = "middleware"
    TESTING = "testing"
    DEVOPS = "devops"


@dataclass
class GenerationContext:
    """Context passed through generation pipeline"""

    # Original fields
    project_name: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    database: Optional[str] = None
    architecture: Optional[str] = None
    features: Optional[List[str]] = None
    inferred_spec: Optional[Dict[str, Any]] = None
    synthesized_design: Optional[Dict[str, Any]] = None

    # Backend agent fields
    models: Optional[List[Any]] = None
    relations: Optional[List[Any]] = None
    api_resources: Optional[List[Any]] = None
    api_architecture: Optional[Any] = None
    service_architecture: Optional[Any] = None
    auth_requirements: Optional[Any] = None
    auth_plan: Optional[Any] = None
    schema: Optional[Any] = None
    config: Optional[Any] = None

    # Output
    generated_files: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.generated_files is None:
            self.generated_files = {}
        if self.features is None:
            self.features = []


class GenerationPipeline:
    """
    Main pipeline that orchestrates backend generation using LLM
    """

    def __init__(self, config_or_provider=None, model: str = None):
        # Handle both TemplateConfig and string provider
        if hasattr(config_or_provider, "framework"):
            # It's a TemplateConfig
            self.config = config_or_provider
            # Use backend-specific model from settings for backend generation
            self.llm = LLMGenerator(
                provider=settings.llm.backend_provider, model=settings.llm.backend_model
            )
            self.llm.config.max_tokens = settings.llm.backend_max_tokens
            self.llm.config.temperature = settings.llm.backend_temperature
        elif config_or_provider is not None:
            # It's a provider string (legacy support)
            self.config = None
            self.llm = LLMGenerator(
                provider=config_or_provider, model=model or settings.llm.backend_model
            )
        else:
            # Use default backend settings
            self.config = None
            self.llm = LLMGenerator(
                provider=settings.llm.backend_provider, model=settings.llm.backend_model
            )
            self.llm.config.max_tokens = settings.llm.backend_max_tokens
            self.llm.config.temperature = settings.llm.backend_temperature

        self.parser = OutputParser()
        self.prompt_builder = PromptBuilder()

    async def generate(self, context: GenerationContext) -> Dict[str, str]:
        """
        Generate complete backend from context

        Returns:
            Dict mapping file paths to file contents
        """
        stages = self._determine_stages(context)

        for stage in stages:
            await self._execute_stage(stage, context)

        return context.generated_files

    def _determine_stages(self, context: GenerationContext) -> List[GenerationStage]:
        """Determine which stages to run based on features"""
        stages = [
            GenerationStage.ARCHITECTURE,
            GenerationStage.DATABASE,
            GenerationStage.API,
        ]

        if "auth" in context.features or "authentication" in context.features:
            stages.append(GenerationStage.AUTH)

        stages.extend(
            [
                GenerationStage.SERVICES,
                GenerationStage.CONTROLLERS,
                GenerationStage.MIDDLEWARE,
            ]
        )

        if "testing" in context.features:
            stages.append(GenerationStage.TESTING)

        if "docker" in context.features or "kubernetes" in context.features:
            stages.append(GenerationStage.DEVOPS)

        return stages

    async def _execute_stage(self, stage: GenerationStage, context: GenerationContext):
        """Execute a single generation stage"""

        # Build prompt for this stage
        system_prompt = self.prompt_builder.build_system_prompt(
            stage=stage,
            language=context.language,
            framework=context.framework,
            architecture=context.architecture,
        )

        user_prompt = self.prompt_builder.build_user_prompt(
            stage=stage, context=context
        )

        # Generate with LLM
        response = await self.llm.generate(
            system_prompt=system_prompt, user_prompt=user_prompt, context=context
        )

        # Parse output into files
        files = self.parser.parse(response)

        # Add to generated files
        context.generated_files.update(files)

    async def generate_single_file(
        self,
        file_type: str,
        context: GenerationContext,
        additional_context: Optional[str] = None,
    ) -> str:
        """Generate a single file"""

        system_prompt = self.prompt_builder.build_single_file_prompt(
            file_type=file_type, language=context.language, framework=context.framework
        )

        user_prompt = f"""
Generate {file_type} for:
- Project: {context.project_name}
- Spec: {context.inferred_spec}
{f'- Additional: {additional_context}' if additional_context else ''}
"""

        response = await self.llm.generate(
            system_prompt=system_prompt, user_prompt=user_prompt, context=context
        )

        return response


# Alias for backward compatibility
CodeGenerationPipeline = GenerationPipeline
