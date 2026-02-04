"""Tests for modes module."""

import json
import tempfile
from pathlib import Path

import pytest

from bit.modes import (
    MODE_CATALOG,
    ModeSpec,
    SessionManager,
    SessionState,
    get_mode,
    list_modes,
    validate_mode,
)
from bit.workspace import Workspace


@pytest.fixture
def temp_workspace():
    """Create a temporary initialized workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()
        yield tmpdir


# Mode catalog tests

def test_mode_catalog_has_required_modes():
    """Test that all required modes exist in catalog."""
    required = ["chat", "code", "snap", "xform"]
    for mode_name in required:
        assert mode_name in MODE_CATALOG


def test_get_mode_returns_spec():
    """Test get_mode returns ModeSpec for valid mode."""
    spec = get_mode("chat")
    assert spec is not None
    assert isinstance(spec, ModeSpec)
    assert spec.name == "chat"


def test_get_mode_returns_none_for_invalid():
    """Test get_mode returns None for invalid mode."""
    assert get_mode("nonexistent") is None


def test_list_modes_returns_all():
    """Test list_modes returns all modes."""
    modes = list_modes()
    assert len(modes) == len(MODE_CATALOG)
    assert all(isinstance(m, ModeSpec) for m in modes)


def test_validate_mode_valid():
    """Test validate_mode returns True for valid modes."""
    assert validate_mode("chat") is True
    assert validate_mode("code") is True
    assert validate_mode("snap") is True
    assert validate_mode("xform") is True


def test_validate_mode_invalid():
    """Test validate_mode returns False for invalid modes."""
    assert validate_mode("nonexistent") is False
    assert validate_mode("") is False


def test_mode_spec_is_frozen():
    """Test ModeSpec instances are immutable."""
    spec = get_mode("chat")
    with pytest.raises(Exception):  # Pydantic ValidationError
        spec.name = "changed"


# Session state tests

def test_session_state_defaults():
    """Test SessionState has correct defaults."""
    state = SessionState()
    assert state.active_mode == "chat"
    assert state.updated_at == ""


def test_session_state_touch():
    """Test touch updates timestamp."""
    state = SessionState()
    touched = state.touch()
    assert touched.updated_at != ""
    assert "Z" in touched.updated_at


# SessionManager tests

def test_session_manager_load_default(temp_workspace):
    """Test loading returns default when no file exists."""
    session = SessionManager(temp_workspace)
    state = session.load()
    assert state.active_mode == "chat"


def test_session_manager_save_and_load(temp_workspace):
    """Test saving and loading session state."""
    session = SessionManager(temp_workspace)

    # Save a state
    state = SessionState(active_mode="code")
    session.save(state)

    # Load it back
    loaded = session.load()
    assert loaded.active_mode == "code"
    assert loaded.updated_at != ""


def test_session_manager_set_mode(temp_workspace):
    """Test set_mode changes active mode."""
    session = SessionManager(temp_workspace)

    state = session.set_mode("snap")
    assert state.active_mode == "snap"

    # Verify persistence
    loaded = session.load()
    assert loaded.active_mode == "snap"


def test_session_manager_set_mode_invalid(temp_workspace):
    """Test set_mode raises for invalid mode."""
    session = SessionManager(temp_workspace)

    with pytest.raises(ValueError, match="Invalid mode"):
        session.set_mode("nonexistent")


def test_session_manager_get_mode(temp_workspace):
    """Test get_mode returns current mode."""
    session = SessionManager(temp_workspace)

    # Default
    assert session.get_mode() == "chat"

    # After set
    session.set_mode("xform")
    assert session.get_mode() == "xform"


def test_session_manager_creates_context_dir(temp_workspace):
    """Test session manager creates context dir if missing."""
    # Remove context dir
    context_dir = Path(temp_workspace) / "context"
    if context_dir.exists():
        for f in context_dir.iterdir():
            f.unlink()
        context_dir.rmdir()

    session = SessionManager(temp_workspace)
    session.set_mode("code")

    # Should recreate
    assert context_dir.exists()
    assert (context_dir / "session.json").exists()


def test_session_file_is_valid_json(temp_workspace):
    """Test session file is valid JSON."""
    session = SessionManager(temp_workspace)
    session.set_mode("code")

    session_file = Path(temp_workspace) / "context" / "session.json"
    with open(session_file) as f:
        data = json.load(f)

    assert data["active_mode"] == "code"
    assert "updated_at" in data


def test_session_manager_handles_corrupted_file(temp_workspace):
    """Test loading handles corrupted session file."""
    session = SessionManager(temp_workspace)

    # Write invalid JSON
    context_dir = Path(temp_workspace) / "context"
    context_dir.mkdir(exist_ok=True)
    with open(context_dir / "session.json", "w") as f:
        f.write("not valid json")

    # Should return default, not crash
    state = session.load()
    assert state.active_mode == "chat"
