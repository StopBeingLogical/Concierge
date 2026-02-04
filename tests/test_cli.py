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
