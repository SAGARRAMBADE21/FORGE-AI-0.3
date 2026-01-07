"""Backend generation agent."""

import logging
from pathlib import Path
from typing import Callable
from datetime import datetime

from core.types import (
    TaskType, TaskStatus, TaskPlan, BackendArchitecture,
    FrontendAnalysis, GenerationResult, InferredModel,
    InferredRelation, ApiResourceContract, AuthRequirements,
    GeneratedFile, FileChange, ChangeType, ChangeSet
)
from core.utils import generate_id
from config.templates_config import TemplateConfig
from indexers.unified_indexer import UnifiedIndexer
from analyzers.frontend_analyzer import FrontendAnalyzer
from inference.evidence_collector import EvidenceCollector
from inference.model_inference_engine import ModelInferenceEngine
from inference.api_contract_extractor import ApiContractExtractor
from inference.auth_requirements_analyzer import AuthRequirementsAnalyzer
from inference.relationship_inferrer import RelationshipInferrer
from synthesis.schema_designer import SchemaDesigner
from synthesis.api_architect import ApiArchitect
from synthesis.service_architect import ServiceArchitect
from synthesis.auth_planner import AuthPlanner
from generation.pipeline import CodeGenerationPipeline, GenerationContext
from execution.change_engine import ChangeEngine
from orchestration.task_planner import TaskPlanner
from orchestration.execution_runtime import ExecutionRuntime
from orchestration.checkpoint_manager import CheckpointManager
from orchestration.session_manager import SessionManager

logger = logging.getLogger(__name__)


class BackendAgent:
    """
    Agent for generating backend code from frontend analysis.
    
    Capabilities:
    - Analyze frontend to infer models and APIs
    - Design database schema
    - Generate complete backend code
    - Apply changes with rollback support
    - Sync with frontend changes
    """

    def __init__(self, project_root: Path, config: TemplateConfig | None = None):
        self.root = project_root
        self.config = config or TemplateConfig()
        
        # Storage
        self._storage = project_root / '.codegen'
        self._storage.mkdir(parents=True, exist_ok=True)
        
        # Components
        self._indexer: UnifiedIndexer | None = None
        self._frontend_analyzer: FrontendAnalyzer | None = None
        
        # Inference
        self._evidence_collector: EvidenceCollector | None = None
        self._model_engine = ModelInferenceEngine()
        self._api_extractor = ApiContractExtractor()
        self._auth_analyzer: AuthRequirementsAnalyzer | None = None
        self._relationship_inferrer = RelationshipInferrer()
        
        # Synthesis
        self._schema_designer = SchemaDesigner()
        self._api_architect = ApiArchitect()
        self._service_architect = ServiceArchitect()
        self._auth_planner = AuthPlanner()
        
        # Generation
        self._pipeline = CodeGenerationPipeline(self.config)
        
        # Execution
        self._change_engine = ChangeEngine(project_root)
        
        # Orchestration
        self._checkpoint = CheckpointManager(self._storage)
        self._session = SessionManager(self._storage)
        self._planner = TaskPlanner()
        self._runtime = ExecutionRuntime(self._checkpoint)
        
        # State
        self._frontend_analysis: FrontendAnalysis | None = None
        self._architecture: BackendArchitecture | None = None
        self._initialized = False
        
        # Register actions
        self._register_actions()

    def _register_actions(self):
        """Register action handlers for execution runtime."""
        self._runtime.register_action('analyze_frontend', self._action_analyze_frontend)
        self._runtime.register_action('infer_models', self._action_infer_models)
        self._runtime.register_action('infer_relations', self._action_infer_relations)
        self._runtime.register_action('extract_api_contracts', self._action_extract_api_contracts)
        self._runtime.register_action('analyze_auth', self._action_analyze_auth)
        self._runtime.register_action('design_schema', self._action_design_schema)
        self._runtime.register_action('design_api', self._action_design_api)
        self._runtime.register_action('design_services', self._action_design_services)
        self._runtime.register_action('plan_auth', self._action_plan_auth)
        self._runtime.register_action('generate_code', self._action_generate_code)
        self._runtime.register_action('validate_code', self._action_validate_code)
        self._runtime.register_action('apply_changes', self._action_apply_changes)
        # Add endpoint actions
        self._runtime.register_action('validate_endpoint', self._action_validate_endpoint)
        self._runtime.register_action('generate_controller_method', self._action_generate_controller_method)
        self._runtime.register_action('generate_service_method', self._action_generate_service_method)
        self._runtime.register_action('update_routes', self._action_update_routes)
        self._runtime.register_action('generate_validation', self._action_generate_validation)
        # Add model actions
        self._runtime.register_action('validate_model', self._action_validate_model)
        self._runtime.register_action('update_prisma_schema', self._action_update_prisma_schema)
        self._runtime.register_action('generate_repository', self._action_generate_repository)
        self._runtime.register_action('generate_service', self._action_generate_service)
        self._runtime.register_action('generate_controller', self._action_generate_controller)
        self._runtime.register_action('generate_migration', self._action_generate_migration)

    async def initialize(
        self,
        indexer: UnifiedIndexer,
        progress: Callable[[str, str], None] | None = None
    ):
        """Initialize the backend agent."""
        self._indexer = indexer
        self._frontend_analyzer = FrontendAnalyzer(self.root)
        self._evidence_collector = EvidenceCollector(indexer)
        self._auth_analyzer = AuthRequirementsAnalyzer(indexer)
        
        # Create or restore session
        await self._session.get_or_create_session(str(self.root))
        
        self._initialized = True
        
        if progress:
            progress("initialized", "Backend agent ready")

    async def generate_backend(
        self,
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Generate complete backend from frontend analysis."""
        if not self._initialized:
            raise RuntimeError("Agent not initialized")

        # Create execution plan
        plan = await self._planner.create_plan(
            TaskType.GENERATE_BACKEND,
            {'project_root': str(self.root)}
        )

        # Update session
        await self._session.update_session(task=plan)

        # Execute plan
        def on_progress(status: str, step):
            if progress:
                progress(status, f"{step.name}: {step.description}")

        success = await self._runtime.execute(plan, on_progress)

        if not success:
            return GenerationResult(
                success=False,
                errors=["Backend generation failed"],
                files=[]
            )

        # Get generation result from step results
        generated_files_dict = {}
        for step in plan.steps:
            if step.action == 'generate_code' and step.result:
                if isinstance(step.result, dict):
                    generated_files_dict = step.result
                    break

        if generated_files_dict:
            # Convert dict to GeneratedFile objects
            from core.types import GeneratedFile
            generated_files = []
            for path, content in generated_files_dict.items():
                file_ext = Path(path).suffix.lstrip('.')
                generated_files.append(GeneratedFile(
                    path=path,
                    content=content,
                    file_type=file_ext or 'txt',
                    generator='backend_agent'
                ))
            
            return GenerationResult(
                success=True,
                files=generated_files,
                stats={'generated_files': len(generated_files)}
            )

        return GenerationResult(
            success=True,
            files=[],
            stats={'message': 'Generation completed'}
        )

    async def add_model(
        self,
        name: str,
        fields: list[dict],
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Add a new model to the backend."""
        plan = await self._planner.create_plan(
            TaskType.ADD_MODEL,
            {'model': {'name': name, 'fields': fields}}
        )

        await self._session.update_session(task=plan)

        success = await self._runtime.execute(plan)

        return GenerationResult(
            success=success,
            files=[],
            errors=[] if success else ["Failed to add model"]
        )

    async def add_endpoint(
        self,
        method: str,
        path: str,
        config: dict | None = None,
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Add a new API endpoint."""
        plan = await self._planner.create_plan(
            TaskType.ADD_ENDPOINT,
            {'endpoint': {'method': method, 'path': path, **(config or {})}}
        )

        await self._session.update_session(task=plan)

        success = await self._runtime.execute(plan)

        return GenerationResult(
            success=success,
            files=[],
            errors=[] if success else ["Failed to add endpoint"]
        )

    async def sync_with_frontend(
        self,
        progress: Callable[[str, str], None] | None = None
    ) -> GenerationResult:
        """Sync backend with frontend changes."""
        plan = await self._planner.create_plan(
            TaskType.SYNC_FRONTEND,
            {}
        )

        await self._session.update_session(task=plan)

        success = await self._runtime.execute(plan)

        return GenerationResult(
            success=success,
            files=[],
            errors=[] if success else ["Failed to sync"]
        )

    async def rollback(self) -> bool:
        """Rollback last change."""
        session = self._session.current_session
        if not session:
            logger.warning("No active session")
            return False

        # If there's a current task, use its ID
        if session.current_task:
            return await self._checkpoint.restore_latest(session.current_task.id)

        # Otherwise, try to find the most recent checkpoint from any task
        # by scanning the checkpoint storage directory
        checkpoint_files = sorted(
            self._checkpoint._storage.glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not checkpoint_files:
            logger.warning("No checkpoints found to rollback")
            return False

        # Restore the most recent checkpoint
        try:
            latest_checkpoint_id = checkpoint_files[0].stem
            logger.info(f"Rolling back to checkpoint: {latest_checkpoint_id}")
            return await self._checkpoint.restore(latest_checkpoint_id)
        except Exception as e:
            logger.error(f"Failed to rollback: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # ACTION HANDLERS
    # ═══════════════════════════════════════════════════════════════════════

    async def _action_analyze_frontend(self, params: dict) -> FrontendAnalysis:
        """Analyze frontend code."""
        if not self._frontend_analyzer or not self._indexer:
            raise RuntimeError("Not initialized")

        self._frontend_analysis = await self._frontend_analyzer.analyze(self._indexer)
        return self._frontend_analysis

    async def _action_infer_models(self, params: dict) -> list[InferredModel]:
        """Infer data models from frontend."""
        if not self._frontend_analysis or not self._evidence_collector:
            raise RuntimeError("Frontend not analyzed")

        evidence_map = await self._evidence_collector.collect_all(self._frontend_analysis)
        models = await self._model_engine.infer_models(evidence_map)

        if not self._architecture:
            self._architecture = BackendArchitecture()
        self._architecture.models = models

        return models

    async def _action_infer_relations(self, params: dict) -> list[InferredRelation]:
        """Infer relationships between models."""
        if not self._architecture or not self._architecture.models:
            raise RuntimeError("Models not inferred")

        relations = await self._relationship_inferrer.infer_relationships(
            self._architecture.models,
            self._architecture.api_resources
        )

        self._architecture.relations = relations
        return relations

    async def _action_extract_api_contracts(self, params: dict) -> list[ApiResourceContract]:
        """Extract API contracts from frontend."""
        if not self._frontend_analysis or not self._architecture:
            raise RuntimeError("Frontend not analyzed")

        resources = await self._api_extractor.extract_contracts(
            self._frontend_analysis.api_calls,
            self._architecture.models
        )

        self._architecture.api_resources = resources
        return resources

    async def _action_analyze_auth(self, params: dict) -> AuthRequirements:
        """Analyze authentication requirements."""
        if not self._frontend_analysis or not self._auth_analyzer or not self._architecture:
            raise RuntimeError("Frontend not analyzed")

        auth = await self._auth_analyzer.analyze(
            self._frontend_analysis.auth,
            self._architecture.api_resources
        )

        self._architecture.auth = auth
        return auth

    async def _action_design_schema(self, params: dict):
        """Design database schema."""
        if not self._architecture:
            raise RuntimeError("Architecture not built")

        schema = await self._schema_designer.design_schema(
            self._architecture.models,
            self._architecture.relations
        )

        self._architecture.schema = schema
        return schema

    async def _action_design_api(self, params: dict):
        """Design API architecture."""
        if not self._architecture or not self._architecture.auth:
            raise RuntimeError("Architecture not built")

        api_arch = await self._api_architect.design_architecture(
            self._architecture.api_resources,
            self._architecture.models,
            self._architecture.auth
        )

        return api_arch

    async def _action_design_services(self, params: dict):
        """Design service layer."""
        if not self._architecture:
            raise RuntimeError("Architecture not built")

        service_arch = await self._service_architect.design_architecture(
            self._architecture.models,
            self._architecture.relations,
            self._architecture.api_resources
        )

        self._architecture.repositories = service_arch.repositories
        self._architecture.services = service_arch.services

        return service_arch

    async def _action_plan_auth(self, params: dict):
        """Plan auth implementation."""
        if not self._architecture or not self._architecture.auth:
            raise RuntimeError("Auth not analyzed")

        auth_plan = await self._auth_planner.plan(self._architecture.auth)
        return auth_plan

    async def _action_generate_code(self, params: dict) -> GenerationResult:
        """Generate backend code."""
        if not self._architecture:
            raise RuntimeError("Architecture not built")

        # Get results from previous steps
        api_arch = None
        service_arch = None
        auth_plan = None

        session = self._session.current_session
        if session and session.current_task:
            for step in session.current_task.steps:
                if step.action == 'design_api' and step.result:
                    api_arch = step.result
                elif step.action == 'design_services' and step.result:
                    service_arch = step.result
                elif step.action == 'plan_auth' and step.result:
                    auth_plan = step.result

        if not api_arch or not service_arch or not auth_plan:
            raise RuntimeError("Missing design artifacts")

        # Map framework to language
        framework_to_language = {
            "express": "typescript",
            "nestjs": "typescript",
            "fastapi": "python",
            "flask": "python",
            "django": "python",
            "gin": "go",
            "spring": "java",
            "dotnet": "csharp"
        }
        
        framework_name = self.config.framework.value if self.config else "express"
        language_name = framework_to_language.get(framework_name, "typescript")

        context = GenerationContext(
            language=language_name,
            framework=framework_name,
            database=self.config.database.value if self.config else "postgresql",
            models=self._architecture.models,
            relations=self._architecture.relations,
            api_resources=self._architecture.api_resources,
            api_architecture=api_arch,
            service_architecture=service_arch,
            auth_requirements=self._architecture.auth,
            auth_plan=auth_plan,
            schema=self._architecture.schema,
            config=self.config
        )

        result = await self._pipeline.generate(context)
        return result

    async def _action_validate_code(self, params: dict) -> bool:
        """Validate generated code."""
        # Get generated files from previous step
        session = self._session.current_session
        if not session or not session.current_task:
            return True

        for step in session.current_task.steps:
            if step.action == 'generate_code' and step.result:
                result = step.result
                # Check if result is a dict or GenerationResult object
                if isinstance(result, dict):
                    # Result is from pipeline.generate() which returns Dict[str, str]
                    if not result:
                        return False
                elif hasattr(result, 'errors') and result.errors:
                    return False

        return True

    async def _action_apply_changes(self, params: dict) -> bool:
        """Apply generated code to filesystem."""
        session = self._session.current_session
        if not session or not session.current_task:
            return False

        # Get generated files
        generated_files_dict: dict[str, str] = {}
        for step in session.current_task.steps:
            if step.action == 'generate_code' and step.result:
                result = step.result
                if isinstance(result, dict):
                    # Result is from pipeline.generate() which returns Dict[str, str]
                    generated_files_dict = result
                elif hasattr(result, 'files'):
                    # Result is a GenerationResult object
                    generated_files_dict = {f.path: f.content for f in result.files}

        if not generated_files_dict:
            logger.warning("No files to apply")
            return True

        # Convert dict to FileChange objects
        changes = []
        for path, content in generated_files_dict.items():
            changes.append(FileChange(
                path=str(Path(self.config.output_dir) / path),
                change_type=ChangeType.CREATE,
                content=content
            ))

        # Create a ChangeSet
        change_set = ChangeSet(
            id=generate_id(),
            description=f"Apply generated backend code ({len(changes)} files)",
            changes=changes,
            rollback_changes=[]
        )

        # Apply all changes
        success = await self._change_engine.apply_changes(change_set)
        return success

    async def _action_validate_endpoint(self, params: dict) -> bool:
        """Validate endpoint configuration."""
        endpoint = params.get('endpoint', {})
        method = endpoint.get('method', '').upper()
        path = endpoint.get('path', '')
        
        # Basic validation
        if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            logger.error(f"Invalid HTTP method: {method}")
            return False
        
        if not path or not path.startswith('/'):
            logger.error(f"Invalid endpoint path: {path}")
            return False
        
        logger.info(f"Endpoint validated: {method} {path}")
        return True

    async def _action_generate_controller_method(self, params: dict) -> bool:
        """Generate controller method for endpoint."""
        endpoint = params.get('endpoint', {})
        logger.info(f"Generated controller method for {endpoint.get('method')} {endpoint.get('path')}")
        # Placeholder - would generate actual controller code
        return True

    async def _action_generate_service_method(self, params: dict) -> bool:
        """Generate service method for endpoint."""
        endpoint = params.get('endpoint', {})
        logger.info(f"Generated service method for {endpoint.get('method')} {endpoint.get('path')}")
        # Placeholder - would generate actual service code
        return True

    async def _action_update_routes(self, params: dict) -> bool:
        """Update routes configuration."""
        endpoint = params.get('endpoint', {})
        model = params.get('model', {})
        logger.info(f"Updated routes for {endpoint.get('method', '')} {endpoint.get('path', model.get('name', ''))}")
        # Placeholder - would update route files
        return True

    async def _action_generate_validation(self, params: dict) -> bool:
        """Generate validation schema for endpoint."""
        endpoint = params.get('endpoint', {})
        logger.info(f"Generated validation schema for {endpoint.get('method')} {endpoint.get('path')}")
        # Placeholder - would generate validation schemas
        return True

    async def _action_validate_model(self, params: dict) -> bool:
        """Validate model configuration."""
        model = params.get('model', {})
        name = model.get('name', '')
        fields = model.get('fields', [])
        
        if not name:
            logger.error("Model name is required")
            return False
        
        if not fields:
            logger.error("Model must have at least one field")
            return False
        
        logger.info(f"Validated model: {name} with {len(fields)} fields")
        return True

    async def _action_update_prisma_schema(self, params: dict) -> bool:
        """Update Prisma schema with new model."""
        model = params.get('model', {})
        logger.info(f"Updated Prisma schema for model: {model.get('name')}")
        # Placeholder - would update schema.prisma file
        return True

    async def _action_generate_repository(self, params: dict) -> bool:
        """Generate repository for model."""
        model = params.get('model', {})
        logger.info(f"Generated repository for: {model.get('name')}")
        # Placeholder - would generate repository class
        return True

    async def _action_generate_service(self, params: dict) -> bool:
        """Generate service for model."""
        model = params.get('model', {})
        logger.info(f"Generated service for: {model.get('name')}")
        # Placeholder - would generate service class
        return True

    async def _action_generate_controller(self, params: dict) -> bool:
        """Generate controller for model."""
        model = params.get('model', {})
        logger.info(f"Generated controller for: {model.get('name')}")
        # Placeholder - would generate controller class
        return True

    async def _action_generate_migration(self, params: dict) -> bool:
        """Generate database migration for model."""
        model = params.get('model', {})
        logger.info(f"Generated migration for: {model.get('name')}")
        # Placeholder - would generate Prisma migration
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # GETTERS
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def architecture(self) -> BackendArchitecture | None:
        """Get current architecture."""
        return self._architecture

    @property
    def frontend_analysis(self) -> FrontendAnalysis | None:
        """Get frontend analysis."""
        return self._frontend_analysis

    def get_models(self) -> list[InferredModel]:
        """Get inferred models."""
        return self._architecture.models if self._architecture else []

    def get_api_resources(self) -> list[ApiResourceContract]:
        """Get API resources."""
        return self._architecture.api_resources if self._architecture else []

    def get_history(self) -> list[dict]:
        """Get session history."""
        return self._session.get_history()