"""Tests for CLI module."""

import json
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from bit.cli import app
from bit.workspace import Workspace

runner = CliRunner()


def test_init_creates_workspace():
    """Test 'bit init' creates workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["init", tmpdir])

        assert result.exit_code == 0
        assert "Workspace initialized" in result.stdout

        # Verify structure
        ws = Workspace(tmpdir)
        assert ws.validate() is True


def test_init_fails_if_exists():
    """Test 'bit init' fails if workspace exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize once
        runner.invoke(app, ["init", tmpdir])

        # Try again
        result = runner.invoke(app, ["init", tmpdir])

        assert result.exit_code == 1
        assert "already exists" in result.stdout or "already exists" in result.stderr


def test_ws_validate_success():
    """Test 'bit ws validate' on valid workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["ws", "validate", "--path", tmpdir])

        assert result.exit_code == 0
        assert "valid" in result.stdout


def test_ws_validate_fails_missing():
    """Test 'bit ws validate' fails if workspace missing."""
    result = runner.invoke(app, ["ws", "validate", "--path", "/nonexistent"])

    assert result.exit_code == 1


def test_ws_open():
    """Test 'bit ws open' sets active workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["ws", "open", "--path", tmpdir])

        assert result.exit_code == 0
        assert "opened" in result.stdout


def test_ws_show_requires_open():
    """Test 'bit ws show' requires open workspace."""
    result = runner.invoke(app, ["ws", "show"])

    # Without open, should fail
    assert result.exit_code == 1


# Mode command tests

def test_mode_list():
    """Test 'bit mode list' shows all modes."""
    result = runner.invoke(app, ["mode", "list"])

    assert result.exit_code == 0
    assert "chat" in result.stdout
    assert "code" in result.stdout
    assert "snap" in result.stdout
    assert "xform" in result.stdout


def test_mode_set():
    """Test 'bit mode set' changes active mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["mode", "set", "--name", "code", "--path", tmpdir])

        assert result.exit_code == 0
        assert "code" in result.stdout


def test_mode_set_invalid():
    """Test 'bit mode set' fails for invalid mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["mode", "set", "--name", "invalid", "--path", tmpdir])

        assert result.exit_code == 1
        assert "Invalid mode" in result.stdout


def test_mode_set_requires_path():
    """Test 'bit mode set' requires --path."""
    result = runner.invoke(app, ["mode", "set", "--name", "code"])

    assert result.exit_code != 0


def test_mode_show():
    """Test 'bit mode show' displays current mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["mode", "show", "--path", tmpdir])

        assert result.exit_code == 0
        assert "chat" in result.stdout  # Default mode


def test_mode_show_after_set():
    """Test 'bit mode show' reflects set mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        # Set mode
        runner.invoke(app, ["mode", "set", "--name", "snap", "--path", tmpdir])

        # Show should reflect change
        result = runner.invoke(app, ["mode", "show", "--path", tmpdir])

        assert result.exit_code == 0
        assert "snap" in result.stdout


def test_mode_persists_across_commands():
    """Test mode persists across separate CLI invocations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        # Set mode in one invocation
        runner.invoke(app, ["mode", "set", "--name", "xform", "--path", tmpdir])

        # Check in another invocation
        result = runner.invoke(app, ["mode", "show", "--path", tmpdir])

        assert result.exit_code == 0
        assert "xform" in result.stdout
