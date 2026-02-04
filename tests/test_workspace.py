"""Tests for workspace module."""

import json
import tempfile
from pathlib import Path

import pytest

from bit.workspace import Workspace, WorkspaceConfig


@pytest.fixture
def temp_workspace_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_workspace_initialize(temp_workspace_dir):
    """Test workspace initialization creates correct structure."""
    ws = Workspace(temp_workspace_dir)
    config = ws.initialize()

    # Check config
    assert config.workspace_path == str(Path(temp_workspace_dir).absolute())
    assert config.version == "1.0"
    assert config.created_at

    # Check all subdirs exist
    for subdir in Workspace.SUBDIRS:
        assert (Path(temp_workspace_dir) / subdir).is_dir()

    # Check config file exists and is valid
    config_file = Path(temp_workspace_dir) / Workspace.CONFIG_FILE
    assert config_file.exists()

    with open(config_file) as f:
        data = json.load(f)
    assert WorkspaceConfig(**data)


def test_workspace_initialize_exists(temp_workspace_dir):
    """Test initialization fails if workspace exists."""
    ws = Workspace(temp_workspace_dir)
    ws.initialize()

    # Try to initialize again
    with pytest.raises(FileExistsError):
        ws.initialize()


def test_workspace_validate(temp_workspace_dir):
    """Test workspace validation."""
    ws = Workspace(temp_workspace_dir)
    ws.initialize()

    # Should validate successfully
    assert ws.validate() is True


def test_workspace_validate_missing_dir(temp_workspace_dir):
    """Test validation fails if subdir missing."""
    ws = Workspace(temp_workspace_dir)
    ws.initialize()

    # Remove a subdirectory
    (Path(temp_workspace_dir) / "jobs").rmdir()

    with pytest.raises(ValueError, match="Missing subdirectory"):
        ws.validate()


def test_workspace_validate_missing_config(temp_workspace_dir):
    """Test validation fails if config missing."""
    ws = Workspace(temp_workspace_dir)
    ws.initialize()

    # Remove config file
    (Path(temp_workspace_dir) / Workspace.CONFIG_FILE).unlink()

    with pytest.raises(ValueError, match="Config file missing"):
        ws.validate()


def test_workspace_validate_missing_workspace():
    """Test validation fails if workspace doesn't exist."""
    ws = Workspace("/nonexistent/path")

    with pytest.raises(FileNotFoundError, match="Workspace not found"):
        ws.validate()


def test_workspace_load_config(temp_workspace_dir):
    """Test loading workspace config."""
    ws = Workspace(temp_workspace_dir)
    config1 = ws.initialize()

    config2 = ws.load_config()

    assert config2.workspace_path == config1.workspace_path
    assert config2.created_at == config1.created_at
    assert config2.version == config1.version


def test_workspace_hash_content():
    """Test deterministic content hashing."""
    content = "test content"

    hash1 = Workspace.hash_content(content)
    hash2 = Workspace.hash_content(content)

    # Same content produces same hash
    assert hash1 == hash2

    # Different content produces different hash
    hash3 = Workspace.hash_content("other content")
    assert hash1 != hash3

    # Hash is hex string
    assert len(hash1) == 64  # SHA256 hex
    assert all(c in "0123456789abcdef" for c in hash1)
