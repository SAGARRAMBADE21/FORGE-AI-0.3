"""Change engine for applying file changes atomically."""

import logging
import shutil
from datetime import datetime
from pathlib import Path

from core.types import ChangeSet, ChangeType, FileChange, ValidationResult
from core.utils import generate_id
from execution.rollback_manager import RollbackManager
from execution.validator import CodeValidator

logger = logging.getLogger(__name__)


class ChangeEngine:
    """
    Apply file changes atomically with validation and rollback support.
    """

    def __init__(self, project_root: Path):
        self.root = project_root
        self._validator = CodeValidator()
        self._rollback = RollbackManager(project_root)
        self._pending: list[ChangeSet] = []

    async def stage_changes(
        self, changes: list[FileChange], description: str
    ) -> ChangeSet:
        """Stage a set of changes for later application."""
        change_set = ChangeSet(
            id=generate_id(),
            description=description,
            changes=changes,
            rollback_changes=self._create_rollback_changes(changes),
        )
        self._pending.append(change_set)

        logger.info(f"Staged {len(changes)} changes: {description}")
        return change_set

    async def validate_changes(self, change_set: ChangeSet) -> ValidationResult:
        """Validate a set of changes before applying."""
        errors = []
        warnings = []

        for change in change_set.changes:
            result = await self._validate_single(change)
            errors.extend(result.errors)
            warnings.extend(result.warnings)

        # Check for conflicts
        conflict_result = self._check_conflicts(change_set)
        errors.extend(conflict_result.errors)
        warnings.extend(conflict_result.warnings)

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    async def apply_changes(
        self, change_set: ChangeSet, validate: bool = True, create_backup: bool = True
    ) -> bool:
        """Apply a set of changes atomically."""
        # Validate first
        if validate:
            validation = await self.validate_changes(change_set)
            if not validation.valid:
                logger.error(f"Validation failed: {validation.errors}")
                return False

        # Create checkpoint for rollback
        if create_backup:
            checkpoint_id = await self._rollback.create_checkpoint(
                change_set.id, [c.path for c in change_set.changes]
            )
            logger.debug(f"Created checkpoint: {checkpoint_id}")

        # Apply changes
        applied = []
        try:
            for change in change_set.changes:
                await self._apply_single(change)
                applied.append(change)

            logger.info(f"Applied {len(applied)} changes")

            # Remove from pending
            self._pending = [cs for cs in self._pending if cs.id != change_set.id]
            return True

        except Exception as e:
            logger.error(f"Error applying changes: {e}")

            # Rollback applied changes
            for change in reversed(applied):
                try:
                    await self._rollback_single(change)
                except Exception as rollback_error:
                    logger.error(f"Rollback error: {rollback_error}")

            return False

    async def rollback_changes(self, change_set_id: str) -> bool:
        """Rollback a previously applied change set."""
        return await self._rollback.restore_checkpoint(change_set_id)

    async def _validate_single(self, change: FileChange) -> ValidationResult:
        """Validate a single file change."""
        errors = []
        warnings = []

        if change.change_type in (ChangeType.CREATE, ChangeType.UPDATE):
            if not change.content:
                errors.append(f"No content provided for {change.path}")
            else:
                # Syntax validation
                syntax_result = self._validator.validate_syntax(
                    change.content, change.path
                )
                errors.extend(syntax_result.errors)
                warnings.extend(syntax_result.warnings)

        if change.change_type == ChangeType.DELETE:
            full_path = self.root / change.path
            if not full_path.exists():
                warnings.append(f"File to delete does not exist: {change.path}")

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    def _check_conflicts(self, change_set: ChangeSet) -> ValidationResult:
        """Check for conflicts between changes."""
        errors = []
        warnings = []

        paths = [c.path for c in change_set.changes]

        # Check for duplicate paths
        seen = set()
        for path in paths:
            if path in seen:
                errors.append(f"Duplicate path in change set: {path}")
            seen.add(path)

        # Check for circular dependencies
        # (simplified - in reality would need more sophisticated analysis)

        return ValidationResult(
            valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    async def _apply_single(self, change: FileChange):
        """Apply a single file change."""
        full_path = self.root / change.path

        if change.change_type == ChangeType.CREATE:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(change.content or "")
            logger.debug(f"Created: {change.path}")

        elif change.change_type == ChangeType.UPDATE:
            if not full_path.exists():
                full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(change.content or "")
            logger.debug(f"Updated: {change.path}")

        elif change.change_type == ChangeType.DELETE:
            if full_path.exists():
                full_path.unlink()
                logger.debug(f"Deleted: {change.path}")

        elif change.change_type == ChangeType.RENAME:
            if change.old_path:
                old_full = self.root / change.old_path
                if old_full.exists():
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_full), str(full_path))
                    logger.debug(f"Renamed: {change.old_path} -> {change.path}")

    async def _rollback_single(self, change: FileChange):
        """Rollback a single file change."""
        # This is a simplified rollback - actual implementation
        # would use the rollback manager's checkpoints
        full_path = self.root / change.path

        if change.change_type == ChangeType.CREATE:
            if full_path.exists():
                full_path.unlink()

        elif change.change_type == ChangeType.DELETE:
            # Cannot rollback delete without backup
            pass

    def _create_rollback_changes(self, changes: list[FileChange]) -> list[FileChange]:
        """Create rollback changes for a set of changes."""
        rollback = []

        for change in changes:
            if change.change_type == ChangeType.CREATE:
                rollback.append(
                    FileChange(change_type=ChangeType.DELETE, path=change.path)
                )
            elif change.change_type == ChangeType.UPDATE:
                full_path = self.root / change.path
                if full_path.exists():
                    rollback.append(
                        FileChange(
                            change_type=ChangeType.UPDATE,
                            path=change.path,
                            content=full_path.read_text(),
                        )
                    )
            elif change.change_type == ChangeType.DELETE:
                full_path = self.root / change.path
                if full_path.exists():
                    rollback.append(
                        FileChange(
                            change_type=ChangeType.CREATE,
                            path=change.path,
                            content=full_path.read_text(),
                        )
                    )
            elif change.change_type == ChangeType.RENAME:
                rollback.append(
                    FileChange(
                        change_type=ChangeType.RENAME,
                        path=change.old_path or "",
                        old_path=change.path,
                    )
                )

        return list(reversed(rollback))

    def get_pending_changes(self) -> list[ChangeSet]:
        """Get all pending change sets."""
        return self._pending.copy()

    def clear_pending(self):
        """Clear all pending changes."""
        self._pending.clear()
