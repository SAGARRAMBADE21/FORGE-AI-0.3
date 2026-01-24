"""Session manager for agent state."""

import json
import logging
from datetime import datetime
from pathlib import Path

from core.types import AgentSession, TaskPlan
from core.utils import generate_id

logger = logging.getLogger(__name__)


class SessionManager:
    """Manage agent sessions and state persistence."""

    def __init__(self, storage_dir: Path):
        self._storage = storage_dir / "sessions"
        self._storage.mkdir(parents=True, exist_ok=True)
        self._current_session: AgentSession | None = None

    async def create_session(self, project_path: str) -> AgentSession:
        """Create a new session."""
        session = AgentSession(
            id=generate_id(),
            project_path=project_path,
            current_task=None,
            checkpoints=[],
            history=[],
            created_at=datetime.utcnow(),
        )

        self._current_session = session
        await self._save_session(session)

        logger.info(f"Created session: {session.id}")
        return session

    async def load_session(self, session_id: str) -> AgentSession | None:
        """Load an existing session."""
        session_file = self._storage / f"{session_id}.json"

        if not session_file.exists():
            return None

        data = json.loads(session_file.read_text())

        session = AgentSession(
            id=data["id"],
            project_path=data["project_path"],
            current_task=None,  # Would deserialize TaskPlan
            checkpoints=[],  # Would deserialize checkpoints
            history=data.get("history", []),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

        self._current_session = session
        return session

    async def get_or_create_session(self, project_path: str) -> AgentSession:
        """Get existing session for project or create new one."""
        # Check for existing session
        for session_file in self._storage.glob("*.json"):
            try:
                data = json.loads(session_file.read_text())
                if data.get("project_path") == project_path:
                    session = await self.load_session(data["id"])
                    if session:
                        return session
            except Exception:
                continue

        return await self.create_session(project_path)

    async def update_session(
        self, task: TaskPlan | None = None, history_entry: dict | None = None
    ):
        """Update current session."""
        if not self._current_session:
            raise ValueError("No active session")

        if task is not None:
            self._current_session.current_task = task

        if history_entry:
            self._current_session.history.append(
                {**history_entry, "timestamp": datetime.utcnow().isoformat()}
            )

        await self._save_session(self._current_session)

    async def end_session(self):
        """End current session."""
        if self._current_session:
            self._current_session.current_task = None
            await self._save_session(self._current_session)
            self._current_session = None

    async def _save_session(self, session: AgentSession):
        """Persist session to storage."""
        session_file = self._storage / f"{session.id}.json"

        data = {
            "id": session.id,
            "project_path": session.project_path,
            "current_task_id": (
                session.current_task.id if session.current_task else None
            ),
            "history": session.history,
            "created_at": session.created_at.isoformat(),
        }

        session_file.write_text(json.dumps(data, indent=2))

    @property
    def current_session(self) -> AgentSession | None:
        """Get current session."""
        return self._current_session

    def get_history(self, limit: int = 50) -> list[dict]:
        """Get recent history."""
        if not self._current_session:
            return []
        return self._current_session.history[-limit:]

    async def clear_history(self):
        """Clear session history."""
        if self._current_session:
            self._current_session.history = []
            await self._save_session(self._current_session)
