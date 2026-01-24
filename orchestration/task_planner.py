"""Task planning for code generation."""

import logging
from datetime import datetime

from core.types import (
    BackendArchitecture,
    FrontendAnalysis,
    TaskPlan,
    TaskStatus,
    TaskStep,
    TaskType,
)
from core.utils import generate_id

logger = logging.getLogger(__name__)


class TaskPlanner:
    """
    Plan tasks for code generation.

    Uses templates for common tasks, LLM for novel ones.
    """

    def __init__(self, llm_client=None):
        self._llm = llm_client

    async def create_plan(self, task_type: TaskType, context: dict) -> TaskPlan:
        """Create an execution plan for a task."""
        if task_type == TaskType.GENERATE_BACKEND:
            return await self._plan_generate_backend(context)
        elif task_type == TaskType.ADD_ENDPOINT:
            return await self._plan_add_endpoint(context)
        elif task_type == TaskType.ADD_MODEL:
            return await self._plan_add_model(context)
        elif task_type == TaskType.ADD_AUTH:
            return await self._plan_add_auth(context)
        elif task_type == TaskType.SYNC_FRONTEND:
            return await self._plan_sync_frontend(context)
        else:
            return await self._plan_custom(task_type, context)

    async def _plan_generate_backend(self, context: dict) -> TaskPlan:
        """Plan full backend generation."""
        steps = [
            TaskStep(
                id=generate_id(),
                name="analyze_frontend",
                description="Analyze frontend code for models and APIs",
                action="analyze_frontend",
                parameters={},
                dependencies=[],
            ),
            TaskStep(
                id=generate_id(),
                name="infer_models",
                description="Infer data models from frontend evidence",
                action="infer_models",
                parameters={},
                dependencies=["analyze_frontend"],
            ),
            TaskStep(
                id=generate_id(),
                name="infer_relations",
                description="Infer relationships between models",
                action="infer_relations",
                parameters={},
                dependencies=["infer_models"],
            ),
            TaskStep(
                id=generate_id(),
                name="extract_api_contracts",
                description="Extract API contracts from frontend",
                action="extract_api_contracts",
                parameters={},
                dependencies=["infer_models"],
            ),
            TaskStep(
                id=generate_id(),
                name="analyze_auth",
                description="Analyze authentication requirements",
                action="analyze_auth",
                parameters={},
                dependencies=["extract_api_contracts"],
            ),
            TaskStep(
                id=generate_id(),
                name="design_schema",
                description="Design database schema",
                action="design_schema",
                parameters={},
                dependencies=["infer_relations"],
            ),
            TaskStep(
                id=generate_id(),
                name="design_api",
                description="Design API architecture",
                action="design_api",
                parameters={},
                dependencies=["extract_api_contracts", "analyze_auth"],
            ),
            TaskStep(
                id=generate_id(),
                name="design_services",
                description="Design service layer",
                action="design_services",
                parameters={},
                dependencies=["design_api"],
            ),
            TaskStep(
                id=generate_id(),
                name="plan_auth",
                description="Plan authentication implementation",
                action="plan_auth",
                parameters={},
                dependencies=["analyze_auth"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_code",
                description="Generate backend code",
                action="generate_code",
                parameters={},
                dependencies=[
                    "design_schema",
                    "design_api",
                    "design_services",
                    "plan_auth",
                ],
            ),
            TaskStep(
                id=generate_id(),
                name="validate_code",
                description="Validate generated code",
                action="validate_code",
                parameters={},
                dependencies=["generate_code"],
            ),
            TaskStep(
                id=generate_id(),
                name="apply_changes",
                description="Apply changes to filesystem",
                action="apply_changes",
                parameters={},
                dependencies=["validate_code"],
            ),
        ]

        return TaskPlan(
            id=generate_id(),
            task_type=TaskType.GENERATE_BACKEND,
            description="Generate complete backend from frontend analysis",
            steps=steps,
            context=context,
            risk_level="medium",
            estimated_time_ms=60000,
        )

    async def _plan_add_endpoint(self, context: dict) -> TaskPlan:
        """Plan adding a new endpoint."""
        endpoint_config = context.get("endpoint", {})

        steps = [
            TaskStep(
                id=generate_id(),
                name="validate_endpoint",
                description="Validate endpoint configuration",
                action="validate_endpoint",
                parameters={"endpoint": endpoint_config},
                dependencies=[],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_controller_method",
                description="Generate controller method",
                action="generate_controller_method",
                parameters={"endpoint": endpoint_config},
                dependencies=["validate_endpoint"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_service_method",
                description="Generate service method",
                action="generate_service_method",
                parameters={"endpoint": endpoint_config},
                dependencies=["validate_endpoint"],
            ),
            TaskStep(
                id=generate_id(),
                name="update_routes",
                description="Add route to router",
                action="update_routes",
                parameters={"endpoint": endpoint_config},
                dependencies=["generate_controller_method"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_validation",
                description="Generate validation schema",
                action="generate_validation",
                parameters={"endpoint": endpoint_config},
                dependencies=["validate_endpoint"],
            ),
            TaskStep(
                id=generate_id(),
                name="apply_changes",
                description="Apply changes",
                action="apply_changes",
                parameters={},
                dependencies=[
                    "generate_controller_method",
                    "generate_service_method",
                    "update_routes",
                    "generate_validation",
                ],
            ),
        ]

        return TaskPlan(
            id=generate_id(),
            task_type=TaskType.ADD_ENDPOINT,
            description=f"Add new endpoint: {endpoint_config.get('method', 'GET')} {endpoint_config.get('path', '/')}",
            steps=steps,
            context=context,
            risk_level="low",
            estimated_time_ms=5000,
        )

    async def _plan_add_model(self, context: dict) -> TaskPlan:
        """Plan adding a new model."""
        model_config = context.get("model", {})

        steps = [
            TaskStep(
                id=generate_id(),
                name="validate_model",
                description="Validate model configuration",
                action="validate_model",
                parameters={"model": model_config},
                dependencies=[],
            ),
            TaskStep(
                id=generate_id(),
                name="update_prisma_schema",
                description="Add model to Prisma schema",
                action="update_prisma_schema",
                parameters={"model": model_config},
                dependencies=["validate_model"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_repository",
                description="Generate repository",
                action="generate_repository",
                parameters={"model": model_config},
                dependencies=["update_prisma_schema"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_service",
                description="Generate service",
                action="generate_service",
                parameters={"model": model_config},
                dependencies=["generate_repository"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_controller",
                description="Generate controller",
                action="generate_controller",
                parameters={"model": model_config},
                dependencies=["generate_service"],
            ),
            TaskStep(
                id=generate_id(),
                name="update_routes",
                description="Add routes for model",
                action="update_routes",
                parameters={"model": model_config},
                dependencies=["generate_controller"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_migration",
                description="Generate database migration",
                action="generate_migration",
                parameters={"model": model_config},
                dependencies=["update_prisma_schema"],
            ),
            TaskStep(
                id=generate_id(),
                name="apply_changes",
                description="Apply changes",
                action="apply_changes",
                parameters={},
                dependencies=[
                    "generate_repository",
                    "generate_service",
                    "generate_controller",
                    "update_routes",
                    "generate_migration",
                ],
            ),
        ]

        return TaskPlan(
            id=generate_id(),
            task_type=TaskType.ADD_MODEL,
            description=f"Add new model: {model_config.get('name', 'Model')}",
            steps=steps,
            context=context,
            risk_level="medium",
            estimated_time_ms=15000,
        )

    async def _plan_add_auth(self, context: dict) -> TaskPlan:
        """Plan adding authentication."""
        steps = [
            TaskStep(
                id=generate_id(),
                name="analyze_requirements",
                description="Analyze auth requirements",
                action="analyze_auth_requirements",
                parameters=context,
                dependencies=[],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_auth_middleware",
                description="Generate auth middleware",
                action="generate_auth_middleware",
                parameters={},
                dependencies=["analyze_requirements"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_auth_service",
                description="Generate auth service",
                action="generate_auth_service",
                parameters={},
                dependencies=["analyze_requirements"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_auth_controller",
                description="Generate auth controller",
                action="generate_auth_controller",
                parameters={},
                dependencies=["generate_auth_service"],
            ),
            TaskStep(
                id=generate_id(),
                name="update_user_model",
                description="Update User model for auth",
                action="update_user_model",
                parameters={},
                dependencies=["analyze_requirements"],
            ),
            TaskStep(
                id=generate_id(),
                name="apply_changes",
                description="Apply changes",
                action="apply_changes",
                parameters={},
                dependencies=[
                    "generate_auth_middleware",
                    "generate_auth_controller",
                    "update_user_model",
                ],
            ),
        ]

        return TaskPlan(
            id=generate_id(),
            task_type=TaskType.ADD_AUTH,
            description="Add authentication to backend",
            steps=steps,
            context=context,
            risk_level="medium",
            estimated_time_ms=20000,
        )

    async def _plan_sync_frontend(self, context: dict) -> TaskPlan:
        """Plan syncing with frontend changes."""
        steps = [
            TaskStep(
                id=generate_id(),
                name="analyze_frontend",
                description="Re-analyze frontend for changes",
                action="analyze_frontend",
                parameters={},
                dependencies=[],
            ),
            TaskStep(
                id=generate_id(),
                name="infer_models",
                description="Infer data models from frontend",
                action="infer_models",
                parameters={},
                dependencies=["analyze_frontend"],
            ),
            TaskStep(
                id=generate_id(),
                name="infer_relations",
                description="Infer relationships between models",
                action="infer_relations",
                parameters={},
                dependencies=["infer_models"],
            ),
            TaskStep(
                id=generate_id(),
                name="extract_api_contracts",
                description="Extract API contracts from frontend",
                action="extract_api_contracts",
                parameters={},
                dependencies=["analyze_frontend"],
            ),
            TaskStep(
                id=generate_id(),
                name="analyze_auth",
                description="Analyze authentication requirements",
                action="analyze_auth",
                parameters={},
                dependencies=["analyze_frontend"],
            ),
            TaskStep(
                id=generate_id(),
                name="design_schema",
                description="Update database schema",
                action="design_schema",
                parameters={},
                dependencies=["infer_models", "infer_relations"],
            ),
            TaskStep(
                id=generate_id(),
                name="design_api",
                description="Design API structure",
                action="design_api",
                parameters={},
                dependencies=["extract_api_contracts", "design_schema"],
            ),
            TaskStep(
                id=generate_id(),
                name="plan_auth",
                description="Plan authentication implementation",
                action="plan_auth",
                parameters={},
                dependencies=["analyze_auth"],
            ),
            TaskStep(
                id=generate_id(),
                name="design_services",
                description="Design services layer",
                action="design_services",
                parameters={},
                dependencies=["design_schema", "design_api"],
            ),
            TaskStep(
                id=generate_id(),
                name="generate_code",
                description="Generate updated code",
                action="generate_code",
                parameters={},
                dependencies=["design_services", "design_api", "plan_auth"],
            ),
            TaskStep(
                id=generate_id(),
                name="validate_code",
                description="Validate generated code",
                action="validate_code",
                parameters={},
                dependencies=["generate_code"],
            ),
            TaskStep(
                id=generate_id(),
                name="apply_changes",
                description="Apply changes to filesystem",
                action="apply_changes",
                parameters={},
                dependencies=["validate_code"],
            ),
        ]

        return TaskPlan(
            id=generate_id(),
            task_type=TaskType.SYNC_FRONTEND,
            description="Sync backend with frontend changes",
            steps=steps,
            context=context,
            risk_level="low",
            estimated_time_ms=10000,
        )

    async def _plan_custom(self, task_type: TaskType, context: dict) -> TaskPlan:
        """Plan a custom task using LLM."""
        # For custom tasks, use a simple plan
        steps = [
            TaskStep(
                id=generate_id(),
                name="execute",
                description=f"Execute {task_type.value}",
                action="execute_custom",
                parameters=context,
                dependencies=[],
            ),
        ]

        return TaskPlan(
            id=generate_id(),
            task_type=task_type,
            description=f"Custom task: {task_type.value}",
            steps=steps,
            context=context,
            risk_level="medium",
            estimated_time_ms=30000,
        )

    def estimate_risk(self, plan: TaskPlan) -> str:
        """Estimate risk level of a plan."""
        # Count impactful steps
        high_risk_actions = {
            "update_prisma_schema",
            "generate_migration",
            "apply_changes",
        }

        high_risk_count = sum(
            1 for step in plan.steps if step.action in high_risk_actions
        )

        if high_risk_count >= 3:
            return "high"
        elif high_risk_count >= 1:
            return "medium"
        return "low"
