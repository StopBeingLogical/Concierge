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


# Intent command tests

def test_intent_synth_basic():
    """Test 'bit intent synth' creates intent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["intent", "synth", "--text", "Create auth system", "--path", tmpdir])

        assert result.exit_code == 0
        assert "Intent synthesized" in result.stdout
        assert "Hash:" in result.stdout
        assert "Distilled:" in result.stdout


def test_intent_synth_requires_text():
    """Test 'bit intent synth' requires --text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["intent", "synth", "--path", tmpdir])

        assert result.exit_code != 0


def test_intent_synth_deterministic():
    """Test 'bit intent synth' produces same hash for same text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        text = "Create user authentication with OAuth2"

        result1 = runner.invoke(app, ["intent", "synth", "--text", text, "--path", tmpdir])
        result2 = runner.invoke(app, ["intent", "synth", "--text", text, "--path", tmpdir])

        assert result1.exit_code == 0
        assert result2.exit_code == 0

        # Extract hash from output (format: "Hash: abc123def...")
        def extract_hash(output):
            for line in output.split("\n"):
                if "Hash:" in line:
                    return line.split("Hash:")[-1].strip()
            return None

        hash1 = extract_hash(result1.stdout)
        hash2 = extract_hash(result2.stdout)

        assert hash1 == hash2


def test_intent_synth_includes_mode():
    """Test synthesized intent includes current mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        # Set mode to code
        runner.invoke(app, ["mode", "set", "--name", "code", "--path", tmpdir])

        result = runner.invoke(app, ["intent", "synth", "--text", "Test intent", "--path", tmpdir])

        assert result.exit_code == 0
        assert "Mode: code" in result.stdout


def test_intent_list_empty():
    """Test 'bit intent list' on empty workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["intent", "list", "--path", tmpdir])

        assert result.exit_code == 0
        assert "No intents found" in result.stdout


def test_intent_list_multiple():
    """Test 'bit intent list' shows all intents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        # Create intents
        runner.invoke(app, ["intent", "synth", "--text", "First intent", "--path", tmpdir])
        runner.invoke(app, ["intent", "synth", "--text", "Second intent", "--path", tmpdir])

        result = runner.invoke(app, ["intent", "list", "--path", tmpdir])

        assert result.exit_code == 0
        assert "Intents" in result.stdout
        # Should show 2 intents in table


def test_intent_show_by_hash():
    """Test 'bit intent show' displays intent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        # Create intent
        result = runner.invoke(app, ["intent", "synth", "--text", "Test intent", "--path", tmpdir])
        assert result.exit_code == 0

        # Extract hash
        hash_value = None
        for line in result.stdout.split("\n"):
            if "Hash:" in line:
                hash_value = line.split("Hash:")[-1].strip()
                break

        assert hash_value

        # Show intent
        show_result = runner.invoke(app, ["intent", "show", "--hash", hash_value, "--path", tmpdir])

        assert show_result.exit_code == 0
        assert "Intent" in show_result.stdout


def test_intent_show_nonexistent():
    """Test 'bit intent show' fails for nonexistent hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["intent", "show", "--hash", "nonexistent", "--path", tmpdir])

        assert result.exit_code == 1
        assert "not found" in result.stdout


def test_intent_show_requires_hash():
    """Test 'bit intent show' requires --hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["intent", "show", "--path", tmpdir])

        assert result.exit_code != 0


def test_intent_verify_valid():
    """Test 'bit intent verify' validates correct hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        # Create intent
        result = runner.invoke(app, ["intent", "synth", "--text", "Test intent", "--path", tmpdir])
        assert result.exit_code == 0

        # Extract hash
        hash_value = None
        for line in result.stdout.split("\n"):
            if "Hash:" in line:
                hash_value = line.split("Hash:")[-1].strip()
                break

        assert hash_value

        # Verify
        verify_result = runner.invoke(app, ["intent", "verify", "--hash", hash_value, "--path", tmpdir])

        assert verify_result.exit_code == 0
        assert "valid" in verify_result.stdout.lower()


def test_intent_verify_nonexistent():
    """Test 'bit intent verify' fails for nonexistent hash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()

        result = runner.invoke(app, ["intent", "verify", "--hash", "nonexistent", "--path", tmpdir])

        assert result.exit_code == 1
        assert "not found" in result.stdout
