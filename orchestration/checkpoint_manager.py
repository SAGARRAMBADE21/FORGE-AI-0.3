"""Checkpoint manager for task execution."""

import json
import logging
from pathlib import Path
from datetime import datetime

from core.types import Checkpoint
from core.utils import generate_id

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manage checkpoints during task execution."""

    def __init__(self, storage_dir: Path):
        self._storage = storage_dir / 'checkpoints'
        self._storage.mkdir(parents=True, exist_ok=True)
        self._current_checkpoints: dict[str, list[Checkpoint]] = {}

    async def create(self, task_id: str, step_id: str) -> Checkpoint:
        """Create a checkpoint before step execution."""
        checkpoint = Checkpoint(
            id=generate_id(),
            task_id=task_id,
            step_id=step_id,
            file_states={},  # Would capture actual file states
            created_at=datetime.utcnow()
        )

        if task_id not in self._current_checkpoints:
            self._current_checkpoints[task_id] = []

        self._current_checkpoints[task_id].append(checkpoint)

        # Persist
        await self._save_checkpoint(checkpoint)

        return checkpoint

    async def restore(self, checkpoint_id: str) -> bool:
        """Restore to a specific checkpoint."""
        checkpoint_file = self._storage / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False

        checkpoint_data = json.loads(checkpoint_file.read_text())
        
        # Restore file states
        for path, content in checkpoint_data.get('file_states', {}).items():
            try:
                Path(path).write_text(content)
            except Exception as e:
                logger.error(f"Failed to restore {path}: {e}")

        logger.info(f"Restored checkpoint: {checkpoint_id}")
        return True

    async def restore_latest(self, task_id: str) -> bool:
        """Restore to the latest checkpoint for a task."""
        checkpoints = self._current_checkpoints.get(task_id, [])
        
        if not checkpoints:
            logger.warning(f"No checkpoints found for task: {task_id}")
            return False

        latest = checkpoints[-1]
        return await self.restore(latest.id)

    async def _save_checkpoint(self, checkpoint: Checkpoint):
        """Persist checkpoint to storage."""
        checkpoint_file = self._storage / f"{checkpoint.id}.json"
        
        data = {
            'id': checkpoint.id,
            'task_id': checkpoint.task_id,
            'step_id': checkpoint.step_id,
            'file_states': checkpoint.file_states,
            'created_at': checkpoint.created_at.isoformat()
        }

        checkpoint_file.write_text(json.dumps(data, indent=2))

    async def cleanup(self, task_id: str):
        """Clean up checkpoints for a completed task."""
        checkpoints = self._current_checkpoints.pop(task_id, [])
        
        for checkpoint in checkpoints:
            checkpoint_file = self._storage / f"{checkpoint.id}.json"
            if checkpoint_file.exists():
                checkpoint_file.unlink()

        logger.info(f"Cleaned up {len(checkpoints)} checkpoints for task: {task_id}")

    def get_checkpoints(self, task_id: str) -> list[Checkpoint]:
        """Get all checkpoints for a task."""
        return self._current_checkpoints.get(task_id, [])