"""Rollback manager for change recovery."""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime

from core.types import Checkpoint
from core.utils import generate_id

logger = logging.getLogger(__name__)


class RollbackManager:
    """Manage checkpoints and rollbacks."""

    def __init__(self, project_root: Path):
        self.root = project_root
        self._checkpoints_dir = project_root / '.codegen' / 'checkpoints'
        self._checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._checkpoints_dir / 'index.json'
        self._index = self._load_index()

    def _load_index(self) -> dict:
        """Load checkpoint index."""
        if self._index_file.exists():
            return json.loads(self._index_file.read_text())
        return {'checkpoints': []}

    def _save_index(self):
        """Save checkpoint index."""
        self._index_file.write_text(json.dumps(self._index, indent=2))

    async def create_checkpoint(
        self, 
        task_id: str, 
        file_paths: list[str],
        step_id: str | None = None
    ) -> str:
        """Create a checkpoint for rollback."""
        checkpoint_id = generate_id()
        checkpoint_dir = self._checkpoints_dir / checkpoint_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Save file states
        file_states = {}
        for rel_path in file_paths:
            full_path = self.root / rel_path
            if full_path.exists():
                # Copy file to checkpoint
                dest = checkpoint_dir / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, dest)
                file_states[rel_path] = 'exists'
            else:
                file_states[rel_path] = 'not_exists'

        # Save metadata
        metadata = {
            'id': checkpoint_id,
            'task_id': task_id,
            'step_id': step_id,
            'created_at': datetime.utcnow().isoformat(),
            'file_states': file_states
        }
        
        (checkpoint_dir / 'metadata.json').write_text(json.dumps(metadata, indent=2))

        # Update index
        self._index['checkpoints'].append({
            'id': checkpoint_id,
            'task_id': task_id,
            'created_at': metadata['created_at']
        })
        self._save_index()

        logger.info(f"Created checkpoint {checkpoint_id} with {len(file_states)} files")
        return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore files from a checkpoint."""
        checkpoint_dir = self._checkpoints_dir / checkpoint_id
        
        if not checkpoint_dir.exists():
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False

        metadata_file = checkpoint_dir / 'metadata.json'
        if not metadata_file.exists():
            logger.error(f"Checkpoint metadata not found: {checkpoint_id}")
            return False

        metadata = json.loads(metadata_file.read_text())
        file_states = metadata.get('file_states', {})

        restored = 0
        for rel_path, state in file_states.items():
            full_path = self.root / rel_path
            backup_path = checkpoint_dir / rel_path

            try:
                if state == 'exists' and backup_path.exists():
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(backup_path, full_path)
                    restored += 1
                elif state == 'not_exists':
                    if full_path.exists():
                        full_path.unlink()
                        restored += 1
            except Exception as e:
                logger.error(f"Error restoring {rel_path}: {e}")

        logger.info(f"Restored {restored} files from checkpoint {checkpoint_id}")
        return True

    async def delete_checkpoint(self, checkpoint_id: str):
        """Delete a checkpoint."""
        checkpoint_dir = self._checkpoints_dir / checkpoint_id
        
        if checkpoint_dir.exists():
            shutil.rmtree(checkpoint_dir)

        self._index['checkpoints'] = [
            c for c in self._index['checkpoints']
            if c['id'] != checkpoint_id
        ]
        self._save_index()

        logger.info(f"Deleted checkpoint {checkpoint_id}")

    def get_checkpoints(self, task_id: str | None = None) -> list[dict]:
        """Get list of checkpoints."""
        checkpoints = self._index.get('checkpoints', [])
        
        if task_id:
            checkpoints = [c for c in checkpoints if c.get('task_id') == task_id]
        
        return checkpoints

    async def cleanup_old_checkpoints(self, max_age_hours: int = 24):
        """Remove checkpoints older than max_age."""
        cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        
        to_delete = []
        for checkpoint in self._index.get('checkpoints', []):
            created = datetime.fromisoformat(checkpoint['created_at']).timestamp()
            if created < cutoff:
                to_delete.append(checkpoint['id'])

        for checkpoint_id in to_delete:
            await self.delete_checkpoint(checkpoint_id)

        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old checkpoints")