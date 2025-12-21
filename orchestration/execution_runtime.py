"""Execution runtime for running task plans."""

import logging
import asyncio
from datetime import datetime
from typing import Callable, Any

from core.types import TaskPlan, TaskStep, TaskStatus, Checkpoint
from orchestration.checkpoint_manager import CheckpointManager

logger = logging.getLogger(__name__)


class ExecutionRuntime:
    """
    Execute task plans with checkpointing and recovery.
    """

    def __init__(self, checkpoint_manager: CheckpointManager):
        self._checkpoint = checkpoint_manager
        self._actions: dict[str, Callable] = {}
        self._current_plan: TaskPlan | None = None

    def register_action(self, name: str, handler: Callable):
        """Register an action handler."""
        self._actions[name] = handler

    async def execute(
        self,
        plan: TaskPlan,
        on_progress: Callable[[str, TaskStep], None] | None = None
    ) -> bool:
        """Execute a task plan."""
        self._current_plan = plan
        plan_id = plan.id

        logger.info(f"Starting execution of plan: {plan.description}")

        # Build dependency graph
        step_map = {step.id: step for step in plan.steps}
        name_to_id = {step.name: step.id for step in plan.steps}
        completed = set()
        failed = False

        while len(completed) < len(plan.steps) and not failed:
            # Find ready steps (all dependencies completed)
            ready = [
                step for step in plan.steps
                if step.id not in completed
                and all(name_to_id.get(dep) in completed for dep in step.dependencies)
                and step.status == TaskStatus.PENDING
            ]

            if not ready:
                if len(completed) < len(plan.steps):
                    logger.error("Deadlock detected - no ready steps but plan incomplete")
                    failed = True
                break

            # Execute ready steps (could parallelize non-dependent steps)
            for step in ready:
                success = await self._execute_step(step, plan_id, on_progress)
                
                if success:
                    completed.add(step.id)
                else:
                    failed = True
                    break

        if failed:
            logger.error(f"Plan execution failed")
            await self._handle_failure(plan, completed)
            return False

        logger.info(f"Plan execution completed successfully")
        return True

    async def _execute_step(
        self,
        step: TaskStep,
        plan_id: str,
        on_progress: Callable | None
    ) -> bool:
        """Execute a single step."""
        logger.info(f"Executing step: {step.name}")
        step.status = TaskStatus.EXECUTING

        if on_progress:
            on_progress("executing", step)

        # Create checkpoint before step
        checkpoint = await self._checkpoint.create(plan_id, step.id)

        try:
            # Get action handler
            handler = self._actions.get(step.action)
            if not handler:
                raise ValueError(f"Unknown action: {step.action}")

            # Execute action
            result = await handler(step.parameters)
            
            step.result = result
            step.status = TaskStatus.COMPLETED

            if on_progress:
                on_progress("completed", step)

            logger.info(f"Step completed: {step.name}")
            return True

        except Exception as e:
            logger.error(f"Step failed: {step.name} - {e}")
            step.status = TaskStatus.FAILED
            step.error = str(e)

            if on_progress:
                on_progress("failed", step)

            return False

    async def _handle_failure(self, plan: TaskPlan, completed: set[str]):
        """Handle plan failure - attempt recovery."""
        logger.info("Attempting rollback...")

        # Rollback in reverse order of completion
        completed_steps = [
            step for step in plan.steps 
            if step.id in completed
        ]

        for step in reversed(completed_steps):
            if step.rollback_action:
                try:
                    handler = self._actions.get(step.rollback_action)
                    if handler:
                        await handler(step.parameters)
                        logger.info(f"Rolled back step: {step.name}")
                except Exception as e:
                    logger.error(f"Rollback failed for step {step.name}: {e}")

        # Restore from initial checkpoint
        await self._checkpoint.restore_latest(plan.id)

    async def pause(self):
        """Pause execution (between steps)."""
        # Implementation would set a flag checked between steps
        pass

    async def resume(self):
        """Resume paused execution."""
        pass

    async def cancel(self):
        """Cancel execution and rollback."""
        if self._current_plan:
            # Mark remaining steps as cancelled
            for step in self._current_plan.steps:
                if step.status == TaskStatus.PENDING:
                    step.status = TaskStatus.ROLLED_BACK