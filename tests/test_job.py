"""Tests for job module."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from bit.intent import Intent, IntentSynthesizer, IntentManager
from bit.job import (
    Job,
    JobManager,
    JobSpec,
    JobInput,
    JobOutput,
    ApprovalGates,
    JobStatus,
    InputType,
    OutputType,
)
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


@pytest.fixture
def sample_intent(temp_workspace):
    """Create a sample intent in workspace."""
    intent = IntentSynthesizer.synthesize(
        "Create user authentication system. Must use OAuth2.",
        "code"
    )
    manager = IntentManager(temp_workspace)
    manager.save(intent)
    return intent


# ============================================================================
# Model Tests (15 tests)
# ============================================================================

def test_job_status_enum():
    """Test JobStatus enum values."""
    assert JobStatus.DRAFT.value == "draft"
    assert JobStatus.PLANNED.value == "planned"
    assert JobStatus.APPROVED.value == "approved"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"
    assert JobStatus.HALTED.value == "halted"


def test_input_type_enum():
    """Test InputType enum values."""
    assert InputType.FILE.value == "file"
    assert InputType.FOLDER.value == "folder"
    assert InputType.STRING.value == "string"
    assert InputType.INTEGER.value == "integer"
    assert InputType.BOOLEAN.value == "boolean"


def test_output_type_enum():
    """Test OutputType enum values."""
    assert OutputType.FILE.value == "file"
    assert OutputType.FOLDER.value == "folder"


def test_job_input_model():
    """Test JobInput model."""
    inp = JobInput(
        name="audio_file",
        type=InputType.FILE,
        value="/path/to/audio.wav",
        required=True
    )
    assert inp.name == "audio_file"
    assert inp.type == InputType.FILE
    assert inp.value == "/path/to/audio.wav"
    assert inp.required is True


def test_job_input_model_default_required():
    """Test JobInput with default required."""
    inp = JobInput(
        name="audio_file",
        type=InputType.FILE,
        value="/path/to/audio.wav"
    )
    assert inp.required is True


def test_job_output_model():
    """Test JobOutput model."""
    out = JobOutput(
        name="artifacts",
        type=OutputType.FOLDER,
        location="artifacts/"
    )
    assert out.name == "artifacts"
    assert out.type == OutputType.FOLDER
    assert out.location == "artifacts/"


def test_approval_gates_model():
    """Test ApprovalGates model."""
    gates = ApprovalGates()
    assert gates.required_on == ["destructive_operations", "large_compute_operations"]


def test_approval_gates_model_custom():
    """Test ApprovalGates with custom gates."""
    gates = ApprovalGates(required_on=["delete_data", "format_disk"])
    assert gates.required_on == ["delete_data", "format_disk"]


def test_job_spec_model():
    """Test JobSpec model."""
    spec = JobSpec(
        title="Extract stems",
        intent="Extract stems from /music/song.wav",
        success_criteria=["Stems extracted"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    assert spec.title == "Extract stems"
    assert spec.intent == "Extract stems from /music/song.wav"
    assert spec.success_criteria == ["Stems extracted"]
    assert len(spec.outputs) == 1


def test_job_spec_model_defaults():
    """Test JobSpec model with defaults."""
    spec = JobSpec(
        title="Extract stems",
        intent="Extract stems from /music/song.wav",
        success_criteria=["Stems extracted"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    assert spec.constraints == []
    assert spec.inputs == []
    assert isinstance(spec.approval_gates, ApprovalGates)


def test_job_model():
    """Test Job model."""
    job = Job(
        job_id="job-123",
        created_at="2026-02-04T12:00:00Z",
        intent_ref="intent_550e8400e29b",
        intent_hash="abc123",
        status=JobStatus.DRAFT,
        mode_used="code",
        job_spec=JobSpec(
            title="Test",
            intent="Test intent",
            success_criteria=["Done"],
            outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
        ),
        job_spec_hash="xyz789"
    )
    assert job.job_id == "job-123"
    assert job.status == JobStatus.DRAFT
    assert job.mode_used == "code"


def test_job_spec_to_canonical_dict():
    """Test JobSpec.to_canonical_dict() excludes nothing."""
    spec = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["Criteria B", "Criteria A"],
        constraints=["Constraint 2", "Constraint 1"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    canonical = spec.to_canonical_dict()

    # Should include all fields
    assert canonical["title"] == "Test"
    assert canonical["intent"] == "Test intent"

    # Lists should be sorted
    assert canonical["success_criteria"] == ["Criteria A", "Criteria B"]
    assert canonical["constraints"] == ["Constraint 1", "Constraint 2"]


# ============================================================================
# Hashing Tests (8 tests)
# ============================================================================

def test_job_spec_hash_deterministic():
    """Test that same spec produces same hash."""
    spec1 = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["A"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    spec2 = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["A"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )

    hash1 = JobManager._compute_job_spec_hash(spec1)
    hash2 = JobManager._compute_job_spec_hash(spec2)
    assert hash1 == hash2


def test_job_spec_hash_different_specs():
    """Test that different specs produce different hashes."""
    spec1 = JobSpec(
        title="Test 1",
        intent="Test intent",
        success_criteria=["A"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    spec2 = JobSpec(
        title="Test 2",
        intent="Test intent",
        success_criteria=["A"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )

    hash1 = JobManager._compute_job_spec_hash(spec1)
    hash2 = JobManager._compute_job_spec_hash(spec2)
    assert hash1 != hash2


def test_job_spec_hash_order_independent_criteria():
    """Test hash is same regardless of success_criteria order."""
    spec1 = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["A", "B", "C"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    spec2 = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["C", "B", "A"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )

    hash1 = JobManager._compute_job_spec_hash(spec1)
    hash2 = JobManager._compute_job_spec_hash(spec2)
    assert hash1 == hash2


def test_job_spec_hash_order_independent_constraints():
    """Test hash is same regardless of constraints order."""
    spec1 = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["A"],
        constraints=["X", "Y", "Z"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    spec2 = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["A"],
        constraints=["Z", "Y", "X"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )

    hash1 = JobManager._compute_job_spec_hash(spec1)
    hash2 = JobManager._compute_job_spec_hash(spec2)
    assert hash1 == hash2


def test_job_spec_hash_format():
    """Test job spec hash is valid SHA256 (64 hex chars)."""
    spec = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["A"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    hash_val = JobManager._compute_job_spec_hash(spec)

    assert len(hash_val) == 64
    assert all(c in "0123456789abcdef" for c in hash_val)


def test_job_spec_hash_stability():
    """Test hash doesn't change across multiple computations."""
    spec = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=["A"],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )

    hashes = [JobManager._compute_job_spec_hash(spec) for _ in range(5)]
    assert all(h == hashes[0] for h in hashes)


def test_job_spec_hash_empty_lists():
    """Test hash with empty lists."""
    spec = JobSpec(
        title="Test",
        intent="Test intent",
        success_criteria=[],
        constraints=[],
        inputs=[],
        outputs=[JobOutput(name="artifacts", type=OutputType.FOLDER, location="artifacts/")]
    )
    hash_val = JobManager._compute_job_spec_hash(spec)
    assert len(hash_val) == 64


# ============================================================================
# JobManager Tests (12 tests)
# ============================================================================

def test_job_manager_create_from_intent_basic(temp_workspace, sample_intent):
    """Test creating job from intent."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")

    assert job.job_id.startswith("job-")
    assert job.status == JobStatus.DRAFT
    assert job.intent_ref == sample_intent.intent_id
    assert job.intent_hash == sample_intent.intent_hash
    assert job.mode_used == "code"
    assert job.job_spec.title == sample_intent.distilled_intent[:100]
    assert job.job_spec.intent == sample_intent.distilled_intent


def test_job_manager_create_from_intent_success_criteria_wrapped(temp_workspace, sample_intent):
    """Test success criteria is wrapped in list."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")

    assert isinstance(job.job_spec.success_criteria, list)
    assert len(job.job_spec.success_criteria) > 0


def test_job_manager_create_from_intent_has_output():
    """Test job spec has default artifacts output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()
        session = SessionManager(tmpdir)
        session.set_mode("code")

        intent = IntentSynthesizer.synthesize("Test intent", "code")
        IntentManager(tmpdir).save(intent)

        manager = JobManager(tmpdir)
        job = manager.create_from_intent(intent, "code")

        assert len(job.job_spec.outputs) > 0
        assert job.job_spec.outputs[0].name == "artifacts"
        assert job.job_spec.outputs[0].type == OutputType.FOLDER
        assert job.job_spec.outputs[0].location == "artifacts/"


def test_job_manager_create_from_intent_unique_ids(temp_workspace, sample_intent):
    """Test that same intent produces different job IDs."""
    manager = JobManager(temp_workspace)
    job1 = manager.create_from_intent(sample_intent, "code")
    job2 = manager.create_from_intent(sample_intent, "code")

    assert job1.job_id != job2.job_id


def test_job_manager_create_from_intent_has_hash(temp_workspace, sample_intent):
    """Test created job has valid job_spec_hash."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")

    assert job.job_spec_hash
    assert len(job.job_spec_hash) == 64


def test_job_manager_save_creates_file(temp_workspace, sample_intent):
    """Test save creates job.yaml file."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    path = manager.save(job)

    assert path.exists()
    assert path.name == "job.yaml"
    assert str(job.job_id) in str(path)


def test_job_manager_save_valid_yaml(temp_workspace, sample_intent):
    """Test saved file is valid YAML."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    path = manager.save(job)

    with open(path, "r") as f:
        data = yaml.safe_load(f)

    assert data["job_id"] == job.job_id
    assert data["status"] == "draft"


def test_job_manager_load_by_id(temp_workspace, sample_intent):
    """Test loading job by ID."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    manager.save(job)

    loaded = manager.load(job.job_id)
    assert loaded is not None
    assert loaded.job_id == job.job_id
    assert loaded.status == JobStatus.DRAFT


def test_job_manager_load_nonexistent():
    """Test loading nonexistent job returns None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = Workspace(tmpdir)
        ws.initialize()
        manager = JobManager(tmpdir)
        assert manager.load("job-nonexistent") is None


def test_job_manager_load_corrupted_file(temp_workspace):
    """Test loading corrupted file returns None."""
    manager = JobManager(temp_workspace)
    manager._ensure_job_dir("job-test")
    job_path = manager._get_job_path("job-test")

    with open(job_path, "w") as f:
        f.write("invalid: yaml: [")

    assert manager.load("job-test") is None


def test_job_manager_list_jobs_empty(temp_workspace):
    """Test listing jobs when empty."""
    manager = JobManager(temp_workspace)
    jobs = manager.list_jobs()
    assert jobs == []


def test_job_manager_list_jobs_sorted(temp_workspace, sample_intent):
    """Test jobs are sorted by created_at descending."""
    manager = JobManager(temp_workspace)

    # Create multiple jobs
    job1 = manager.create_from_intent(sample_intent, "code")
    manager.save(job1)

    job2 = manager.create_from_intent(sample_intent, "code")
    manager.save(job2)

    jobs = manager.list_jobs()
    assert len(jobs) >= 2
    # Newest first (descending)
    assert jobs[0].created_at >= jobs[1].created_at


# ============================================================================
# List and Verify Tests (8 tests)
# ============================================================================

def test_verify_job_spec_hash_valid(temp_workspace, sample_intent):
    """Test verifying valid job spec hash."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")

    assert manager.verify_job_spec_hash(job) is True


def test_verify_job_spec_hash_invalid(temp_workspace, sample_intent):
    """Test verifying invalid job spec hash."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    job.job_spec_hash = "invalid_hash"

    assert manager.verify_job_spec_hash(job) is False


def test_verify_job_spec_hash_tampered(temp_workspace, sample_intent):
    """Test verifying tampered job spec."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")

    # Tamper with spec
    original_hash = job.job_spec_hash
    job.job_spec.title = "Different title"

    # Hash should be different now
    assert manager.verify_job_spec_hash(job) is False


def test_verify_intent_hash_valid(temp_workspace, sample_intent):
    """Test verifying valid intent hash."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")

    assert manager.verify_intent_hash(job) is True


def test_verify_intent_hash_invalid(temp_workspace, sample_intent):
    """Test verifying invalid intent hash."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    job.intent_hash = "invalid_hash"

    assert manager.verify_intent_hash(job) is False


def test_verify_intent_hash_mismatched_ref(temp_workspace, sample_intent):
    """Test verifying when intent_ref doesn't match."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    job.intent_ref = "wrong_intent_id"

    assert manager.verify_intent_hash(job) is False


def test_list_jobs_populated(temp_workspace, sample_intent):
    """Test listing jobs with populated jobs."""
    manager = JobManager(temp_workspace)
    job1 = manager.create_from_intent(sample_intent, "code")
    job2 = manager.create_from_intent(sample_intent, "code")
    manager.save(job1)
    manager.save(job2)

    jobs = manager.list_jobs()
    assert len(jobs) >= 2


def test_list_jobs_skips_corrupted(temp_workspace, sample_intent):
    """Test listing jobs skips corrupted files."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    manager.save(job)

    # Create corrupted file
    manager._ensure_job_dir("job-bad")
    bad_path = manager._get_job_path("job-bad")
    with open(bad_path, "w") as f:
        f.write("bad: yaml: [")

    # Should only get the valid job
    jobs = manager.list_jobs()
    assert all(j.job_id != "job-bad" for j in jobs)


# ============================================================================
# Integration Tests (5 tests)
# ============================================================================

def test_full_workflow_create_save_load(temp_workspace, sample_intent):
    """Test full workflow: create -> save -> load."""
    manager = JobManager(temp_workspace)

    # Create
    job = manager.create_from_intent(sample_intent, "code")
    original_id = job.job_id

    # Save
    path = manager.save(job)
    assert path.exists()

    # Load
    loaded = manager.load(original_id)
    assert loaded is not None
    assert loaded.job_id == original_id
    assert loaded.status == JobStatus.DRAFT
    assert loaded.job_spec.title == job.job_spec.title


def test_multiple_jobs_from_same_intent(temp_workspace, sample_intent):
    """Test creating multiple jobs from same intent."""
    manager = JobManager(temp_workspace)

    jobs = []
    for _ in range(3):
        job = manager.create_from_intent(sample_intent, "code")
        manager.save(job)
        jobs.append(job)

    # All should have different IDs
    ids = [j.job_id for j in jobs]
    assert len(ids) == len(set(ids))

    # All should have same intent reference
    refs = [j.intent_ref for j in jobs]
    assert len(set(refs)) == 1


def test_hash_verification_roundtrip(temp_workspace, sample_intent):
    """Test hash verification after save/load roundtrip."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    manager.save(job)

    loaded = manager.load(job.job_id)
    assert manager.verify_job_spec_hash(loaded) is True
    assert manager.verify_intent_hash(loaded) is True


def test_yaml_format_human_readable(temp_workspace, sample_intent):
    """Test that saved YAML is human-readable."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    path = manager.save(job)

    with open(path, "r") as f:
        content = f.read()

    # Check for indentation and structure
    assert "job_id:" in content
    assert "status:" in content
    assert "job_spec:" in content
    # Not all on one line
    assert "\n" in content


def test_yaml_preserves_structure(temp_workspace, sample_intent):
    """Test that YAML preserves all job structure."""
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    manager.save(job)

    loaded = manager.load(job.job_id)

    # All fields match
    assert loaded.job_id == job.job_id
    assert loaded.created_at == job.created_at
    assert loaded.intent_ref == job.intent_ref
    assert loaded.status == job.status
    assert loaded.mode_used == job.mode_used
    assert loaded.job_spec_hash == job.job_spec_hash


# ============================================================================
# CLI Tests (8 tests)
# ============================================================================

def test_cli_job_from_intent(temp_workspace, sample_intent):
    """Test job from-intent CLI command."""
    from bit.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "from-intent",
        "--intent-id", sample_intent.intent_hash,
        "--path", temp_workspace
    ])

    assert result.exit_code == 0
    assert "✓" in result.stdout
    assert "Job ID:" in result.stdout


def test_cli_job_from_intent_not_found(temp_workspace):
    """Test job from-intent with nonexistent intent."""
    from bit.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "from-intent",
        "--intent-id", "nonexistent",
        "--path", temp_workspace
    ])

    assert result.exit_code == 1
    assert "✗" in result.stdout


def test_cli_job_list(temp_workspace, sample_intent):
    """Test job list CLI command."""
    from bit.cli import app
    from typer.testing import CliRunner

    # Create a job first
    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    manager.save(job)

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "list",
        "--path", temp_workspace
    ])

    assert result.exit_code == 0
    assert "Jobs" in result.stdout


def test_cli_job_list_empty(temp_workspace):
    """Test job list when empty."""
    from bit.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "list",
        "--path", temp_workspace
    ])

    assert result.exit_code == 0
    assert "No jobs found" in result.stdout


def test_cli_job_show(temp_workspace, sample_intent):
    """Test job show CLI command."""
    from bit.cli import app
    from typer.testing import CliRunner

    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    manager.save(job)

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "show",
        "--job-id", job.job_id,
        "--path", temp_workspace
    ])

    assert result.exit_code == 0
    assert job.job_id in result.stdout


def test_cli_job_show_not_found(temp_workspace):
    """Test job show with nonexistent job."""
    from bit.cli import app
    from typer.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "show",
        "--job-id", "job-nonexistent",
        "--path", temp_workspace
    ])

    assert result.exit_code == 1
    assert "✗" in result.stdout


def test_cli_job_validate(temp_workspace, sample_intent):
    """Test job validate CLI command."""
    from bit.cli import app
    from typer.testing import CliRunner

    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    manager.save(job)

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "validate",
        "--job-id", job.job_id,
        "--path", temp_workspace
    ])

    assert result.exit_code == 0
    assert "✓" in result.stdout


def test_cli_job_validate_invalid(temp_workspace, sample_intent):
    """Test job validate with invalid job."""
    from bit.cli import app
    from typer.testing import CliRunner

    manager = JobManager(temp_workspace)
    job = manager.create_from_intent(sample_intent, "code")
    job.job_spec_hash = "invalid"
    manager.save(job)

    runner = CliRunner()
    result = runner.invoke(app, [
        "job", "validate",
        "--job-id", job.job_id,
        "--path", temp_workspace
    ])

    assert result.exit_code == 1
