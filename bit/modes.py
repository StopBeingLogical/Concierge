"""Mode catalog and session state management."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModeSpec(BaseModel):
    """Specification for a reasoning bias mode."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    bias: str  # Short hint for reasoning style


class SessionState(BaseModel):
    """Workspace session state (persisted to context/session.json)."""

    active_mode: str = "chat"
    updated_at: str = ""

    def touch(self) -> "SessionState":
        """Update timestamp."""
        return SessionState(
            active_mode=self.active_mode,
            updated_at=datetime.utcnow().isoformat() + "Z"
        )


# Mode catalog - read-only registry
MODE_CATALOG: dict[str, ModeSpec] = {
    "chat": ModeSpec(
        name="chat",
        description="Conversational interaction, exploratory discussion",
        bias="conversational, exploratory"
    ),
    "code": ModeSpec(
        name="code",
        description="Code generation and implementation focus",
        bias="precise, implementation-focused"
    ),
    "snap": ModeSpec(
        name="snap",
        description="Quick decisions, minimal deliberation",
        bias="fast, decisive, minimal prose"
    ),
    "xform": ModeSpec(
        name="xform",
        description="Transform/refactor existing artifacts",
        bias="structural, preserving intent"
    ),
}


def get_mode(name: str) -> Optional[ModeSpec]:
    """Get mode spec by name.

    Args:
        name: Mode name

    Returns:
        ModeSpec if found, None otherwise
    """
    return MODE_CATALOG.get(name)


def list_modes() -> list[ModeSpec]:
    """List all available modes.

    Returns:
        List of all mode specs
    """
    return list(MODE_CATALOG.values())


def validate_mode(name: str) -> bool:
    """Check if mode name is valid.

    Args:
        name: Mode name to validate

    Returns:
        True if valid mode name
    """
    return name in MODE_CATALOG


class SessionManager:
    """Manages session state for a workspace."""

    SESSION_FILE = "session.json"

    def __init__(self, workspace_path: str):
        """Initialize session manager.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = Path(workspace_path)
        self.context_dir = self.workspace_path / "context"
        self.session_file = self.context_dir / self.SESSION_FILE

    def _ensure_context_dir(self) -> None:
        """Ensure context directory exists."""
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> SessionState:
        """Load session state from disk.

        Returns:
            SessionState (default if file doesn't exist)
        """
        if not self.session_file.exists():
            return SessionState()

        try:
            with open(self.session_file, "r") as f:
                data = json.load(f)
            return SessionState(**data)
        except (json.JSONDecodeError, ValueError):
            # Corrupted file - return default
            return SessionState()

    def save(self, state: SessionState) -> None:
        """Save session state to disk.

        Args:
            state: Session state to persist
        """
        self._ensure_context_dir()

        # Touch timestamp before saving
        state = state.touch()

        with open(self.session_file, "w") as f:
            json.dump(state.model_dump(), f, indent=2)

    def get_mode(self) -> str:
        """Get current active mode.

        Returns:
            Active mode name
        """
        return self.load().active_mode

    def set_mode(self, mode_name: str) -> SessionState:
        """Set active mode.

        Args:
            mode_name: Mode to set as active

        Returns:
            Updated session state

        Raises:
            ValueError: If mode name is invalid
        """
        if not validate_mode(mode_name):
            valid = ", ".join(MODE_CATALOG.keys())
            raise ValueError(f"Invalid mode '{mode_name}'. Valid modes: {valid}")

        state = self.load()
        state = SessionState(active_mode=mode_name, updated_at=state.updated_at)
        self.save(state)
        return state
