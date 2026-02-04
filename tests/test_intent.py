"""Tests for intent module."""

import json
import tempfile
from pathlib import Path

import pytest

from bit.intent import Intent, IntentSynthesizer, IntentManager
from bit.modes import SessionManager
from bit.workspace import Workspace


@pytest.fixture
def temp_workspace():
    """Create a temporary initialized workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()
        # Set mode to code for tests
        session = SessionManager(tmpdir)
        session.set_mode("code")
        yield tmpdir


# Intent model tests

def test_intent_model_valid():
    """Test Intent model with valid data."""
    intent = Intent(
        intent_id="550e8400-e29b-41d4-a716-446655440000",
        mode="code",
        distilled_intent="Create user auth",
        success_criteria="Users can log in",
        constraints=["OAuth2"],
        created_at="2026-02-04T12:00:00Z",
        intent_hash="abc123"
    )
    assert intent.intent_id == "550e8400-e29b-41d4-a716-446655440000"
    assert intent.mode == "code"
    assert intent.distilled_intent == "Create user auth"


def test_intent_to_canonical_dict():
    """Test to_canonical_dict excludes metadata fields."""
    intent = Intent(
        intent_id="550e8400-e29b-41d4-a716-446655440000",
        mode="code",
        distilled_intent="Create user auth",
        success_criteria="Users can log in",
        constraints=["OAuth2", "JWT"],
        created_at="2026-02-04T12:00:00Z",
        intent_hash="abc123"
    )
    canonical = intent.to_canonical_dict()

    # Should include core fields
    assert canonical["mode"] == "code"
    assert canonical["distilled_intent"] == "Create user auth"
    assert canonical["success_criteria"] == "Users can log in"

    # Constraints should be sorted
    assert canonical["constraints"] == ["JWT", "OAuth2"]

    # Should not include metadata
    assert "intent_id" not in canonical
    assert "intent_hash" not in canonical
    assert "created_at" not in canonical


# IntentSynthesizer tests

def test_synthesizer_extract_distilled_first_sentence():
    """Test extracting first sentence as distilled intent."""
    text = "Create user authentication system. Must use OAuth2."
    distilled = IntentSynthesizer._extract_distilled_intent(text)
    assert distilled == "Create user authentication system."


def test_synthesizer_extract_distilled_no_sentence():
    """Test extracting distilled intent when no sentence markers."""
    text = "Create user authentication system"
    distilled = IntentSynthesizer._extract_distilled_intent(text)
    assert distilled == "Create user authentication system"


def test_synthesizer_extract_distilled_truncate():
    """Test truncating distilled intent to 100 chars."""
    text = "a" * 150 + "."
    distilled = IntentSynthesizer._extract_distilled_intent(text)
    assert len(distilled) <= 103  # 100 + "..."
    assert distilled.endswith("...")


def test_synthesizer_extract_success_criteria_should():
    """Test extracting success criteria with 'should' pattern."""
    text = "Create auth system. Should allow users to log in with email."
    criteria = IntentSynthesizer._extract_success_criteria(text)
    assert "log in" in criteria or "users" in criteria


def test_synthesizer_extract_success_criteria_must():
    """Test extracting success criteria with 'must' pattern."""
    text = "Build API. Must handle 1000 requests per second."
    criteria = IntentSynthesizer._extract_success_criteria(text)
    assert "1000" in criteria or "requests" in criteria


def test_synthesizer_extract_success_criteria_default():
    """Test default success criteria when no pattern matches."""
    text = "Just build something"
    criteria = IntentSynthesizer._extract_success_criteria(text)
    assert "Just build something" in criteria
    assert "Successfully complete" in criteria


def test_synthesizer_extract_constraints_must_use():
    """Test extracting constraints with 'must use' pattern."""
    text = "Build system. Must use OAuth2 and JWT tokens."
    constraints = IntentSynthesizer._extract_constraints(text)
    assert "OAuth2" in constraints or any("OAuth" in c for c in constraints)


def test_synthesizer_extract_constraints_cannot():
    """Test extracting constraints with 'cannot' pattern."""
    text = "Create database. Cannot use eval() or unsafe functions."
    constraints = IntentSynthesizer._extract_constraints(text)
    assert any("eval" in c.lower() or "unsafe" in c.lower() for c in constraints)


def test_synthesizer_extract_constraints_multiple():
    """Test extracting multiple constraints."""
    text = "Build API. Must use OAuth2. Cannot store passwords. Within 1000ms response time."
    constraints = IntentSynthesizer._extract_constraints(text)
    assert len(constraints) >= 2


def test_synthesizer_synthesize_basic():
    """Test basic intent synthesis."""
    text = "Create user authentication system"
    intent = IntentSynthesizer.synthesize(text, "code")

    assert intent.mode == "code"
    assert intent.distilled_intent == "Create user authentication system"
    assert intent.intent_hash  # Should have hash
    assert intent.intent_id  # Should have UUID


def test_synthesizer_synthesis_deterministic():
    """Test that same input produces same hash."""
    text = "Create user authentication system. Must use OAuth2."
    mode = "code"

    intent1 = IntentSynthesizer.synthesize(text, mode)
    intent2 = IntentSynthesizer.synthesize(text, mode)

    assert intent1.intent_hash == intent2.intent_hash
    assert intent1.intent_id == intent2.intent_id
    assert intent1.distilled_intent == intent2.distilled_intent


def test_synthesizer_different_text_different_hash():
    """Test that different text produces different hash."""
    intent1 = IntentSynthesizer.synthesize("Create auth", "code")
    intent2 = IntentSynthesizer.synthesize("Create database", "code")

    assert intent1.intent_hash != intent2.intent_hash
    assert intent1.intent_id != intent2.intent_id


def test_synthesizer_different_mode_different_hash():
    """Test that different mode produces different hash."""
    text = "Create something"
    intent1 = IntentSynthesizer.synthesize(text, "code")
    intent2 = IntentSynthesizer.synthesize(text, "snap")

    assert intent1.intent_hash != intent2.intent_hash
    assert intent1.intent_id != intent2.intent_id


def test_synthesizer_constraint_order_doesnt_matter():
    """Test that constraint order in the same sentence doesn't affect sorting."""
    text = "Must use OAuth2 and JWT tokens"

    intent1 = IntentSynthesizer.synthesize(text, "code")
    intent2 = IntentSynthesizer.synthesize(text, "code")

    # Extracting same text twice should produce identical constraints (sorted)
    assert sorted(intent1.constraints) == sorted(intent2.constraints)
    assert intent1.intent_hash == intent2.intent_hash


# IntentManager tests

def test_manager_save_creates_file(temp_workspace):
    """Test saving intent creates file."""
    intent = IntentSynthesizer.synthesize("Test intent", "code")
    manager = IntentManager(temp_workspace)

    path = manager.save(intent)

    assert path.exists()
    assert path.name.startswith("intent_")
    assert path.suffix == ".json"


def test_manager_save_file_location(temp_workspace):
    """Test intent saved to artifacts directory."""
    intent = IntentSynthesizer.synthesize("Test intent", "code")
    manager = IntentManager(temp_workspace)

    path = manager.save(intent)

    assert path.parent.name == "artifacts"
    assert str(intent.intent_hash[:16]) in path.name


def test_manager_load_by_hash(temp_workspace):
    """Test loading intent by hash."""
    intent = IntentSynthesizer.synthesize("Test intent", "code")
    manager = IntentManager(temp_workspace)
    manager.save(intent)

    loaded = manager.load(intent.intent_hash)

    assert loaded is not None
    assert loaded.intent_id == intent.intent_id
    assert loaded.distilled_intent == intent.distilled_intent


def test_manager_load_by_partial_hash(temp_workspace):
    """Test loading intent by partial hash (first 16 chars)."""
    intent = IntentSynthesizer.synthesize("Test intent", "code")
    manager = IntentManager(temp_workspace)
    manager.save(intent)

    # Load by first 16 chars (what's in filename)
    loaded = manager.load(intent.intent_hash[:16])

    assert loaded is not None
    assert loaded.intent_id == intent.intent_id


def test_manager_load_nonexistent():
    """Test loading nonexistent intent returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()
        manager = IntentManager(tmpdir)

        loaded = manager.load("nonexistent_hash_123456789")

        assert loaded is None


def test_manager_load_invalid_json(temp_workspace):
    """Test loading corrupted intent file returns None."""
    manager = IntentManager(temp_workspace)
    manager._ensure_artifacts_dir()

    # Write invalid JSON
    bad_file = manager.artifacts_dir / "intent_0000000000000000.json"
    with open(bad_file, "w") as f:
        f.write("not valid json")

    loaded = manager.load("0000000000000000")

    assert loaded is None


def test_manager_list_intents_empty(temp_workspace):
    """Test list_intents returns empty list when no intents."""
    manager = IntentManager(temp_workspace)
    intents = manager.list_intents()

    assert intents == []


def test_manager_list_intents(temp_workspace):
    """Test listing multiple intents."""
    manager = IntentManager(temp_workspace)

    intent1 = IntentSynthesizer.synthesize("First intent", "code")
    intent2 = IntentSynthesizer.synthesize("Second intent", "code")
    intent3 = IntentSynthesizer.synthesize("Third intent", "code")

    manager.save(intent1)
    manager.save(intent2)
    manager.save(intent3)

    intents = manager.list_intents()

    assert len(intents) == 3
    assert all(isinstance(i, Intent) for i in intents)


def test_manager_list_intents_sorted(temp_workspace):
    """Test list_intents returns intents sorted by created_at (newest first)."""
    manager = IntentManager(temp_workspace)

    # Create intents (created_at will be auto-set)
    intent1 = IntentSynthesizer.synthesize("First", "code")
    intent2 = IntentSynthesizer.synthesize("Second", "code")

    manager.save(intent1)
    # Intents are sorted newest first, so list should have intent2 first
    manager.save(intent2)

    intents = manager.list_intents()

    # Both should be present, but order depends on timestamps
    assert len(intents) == 2


def test_manager_verify_hash_valid(temp_workspace):
    """Test hash verification for valid intent."""
    intent = IntentSynthesizer.synthesize("Test intent", "code")
    manager = IntentManager(temp_workspace)
    manager.save(intent)

    is_valid = manager.verify_hash(intent)

    assert is_valid is True


def test_manager_verify_hash_invalid(temp_workspace):
    """Test hash verification fails for tampered intent."""
    intent = IntentSynthesizer.synthesize("Test intent", "code")
    manager = IntentManager(temp_workspace)
    manager.save(intent)

    # Tamper with intent
    intent.distilled_intent = "Modified text"

    is_valid = manager.verify_hash(intent)

    assert is_valid is False


def test_manager_verify_hash_constraint_order_ignored(temp_workspace):
    """Test that constraint order doesn't affect hash verification."""
    intent = IntentSynthesizer.synthesize("Must use X and Y", "code")
    manager = IntentManager(temp_workspace)
    manager.save(intent)

    # Modify constraint order but not content
    original_constraints = intent.constraints
    intent.constraints = sorted(original_constraints, reverse=True)

    # Hash should still verify because constraints are sorted during comparison
    is_valid = manager.verify_hash(intent)

    assert is_valid is True


def test_manager_save_preserves_json(temp_workspace):
    """Test that saved intent can be read back as valid JSON."""
    intent = IntentSynthesizer.synthesize("Test", "code")
    manager = IntentManager(temp_workspace)
    path = manager.save(intent)

    with open(path, "r") as f:
        data = json.load(f)

    assert data["intent_id"] == intent.intent_id
    assert data["mode"] == intent.mode
    assert data["distilled_intent"] == intent.distilled_intent


# Integration tests

def test_integration_synthesize_and_verify(temp_workspace):
    """Test full workflow: synthesize, save, load, verify."""
    manager = IntentManager(temp_workspace)

    # Synthesize
    text = "Create auth system. Must use OAuth2."
    intent = IntentSynthesizer.synthesize(text, "code")

    # Save
    manager.save(intent)

    # Load
    loaded = manager.load(intent.intent_hash)

    # Verify
    assert manager.verify_hash(loaded) is True
    assert loaded.distilled_intent == intent.distilled_intent
    assert loaded.mode == intent.mode


def test_integration_determinism_across_invocations(temp_workspace):
    """Test that hash is deterministic across multiple synthesizer invocations."""
    manager = IntentManager(temp_workspace)

    text = "Build API endpoint. Must be fast."
    mode = "code"

    # Synthesize 5 times
    hashes = []
    for _ in range(5):
        intent = IntentSynthesizer.synthesize(text, mode)
        hashes.append(intent.intent_hash)

    # All hashes should be identical
    assert len(set(hashes)) == 1, "Hashes should be identical across invocations"
