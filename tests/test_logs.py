"""Tests for log reading and monitoring utilities."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from bit.workspace import Workspace
from bit.logs import LogReader
from bit.events import Event, EventType, EventLog, RunRecord
from bit.plan import ExecutionPlan, ResolvedInputs, ResourceRequirements
from bit.packages import Pipeline, PipelineStep, Worker
from bit.router import Router


class TestLogReader:
    """Tests for LogReader."""

    @pytest.fixture
    def workspace(self):
        """Create temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    @pytest.fixture
    def log_reader(self, workspace):
        """Create log reader for testing."""
        return LogReader(workspace)

    def _create_sample_log(self, workspace, job_id):
        """Helper to create a sample event log."""
        logs_dir = Path(workspace) / "jobs" / job_id / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        run_record = RunRecord.create(job_id, "plan-1")
        log_path = logs_dir / f"{run_record.run_id}.jsonl"
        log = EventLog(log_path)

        log.emit(Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id=run_record.run_id,
            job_id=job_id,
        ))

        log.emit(Event(
            type=EventType.STEP_STARTED,
            timestamp="2026-02-04T00:00:01Z",
            run_id=run_record.run_id,
            job_id=job_id,
            step_id="step-1",
            worker_id="test_worker",
        ))

        log.emit(Event(
            type=EventType.STEP_COMPLETED,
            timestamp="2026-02-04T00:00:02Z",
            run_id=run_record.run_id,
            job_id=job_id,
            step_id="step-1",
            worker_id="test_worker",
            payload={"output": "test"},
        ))

        log.emit(Event(
            type=EventType.JOB_COMPLETED,
            timestamp="2026-02-04T00:00:03Z",
            run_id=run_record.run_id,
            job_id=job_id,
        ))

        return run_record

    def test_get_latest_run_log(self, workspace, log_reader):
        """Test getting latest run log."""
        job_id = "test-job-1"
        run_record = self._create_sample_log(workspace, job_id)

        log = log_reader.get_latest_run_log(job_id)

        assert log is not None
        events = log.read()
        assert len(events) == 4

    def test_get_run_log(self, workspace, log_reader):
        """Test getting specific run log."""
        job_id = "test-job-1"
        run_record = self._create_sample_log(workspace, job_id)

        log = log_reader.get_run_log(job_id, run_record.run_id)

        assert log is not None
        events = log.read()
        assert len(events) == 4

    def test_get_job_status(self, workspace, log_reader):
        """Test getting job status."""
        from bit.intent import IntentSynthesizer
        from bit.job import JobManager

        job_id = "test-job-1"
        self._create_sample_log(workspace, job_id)

        # Create actual job for status check
        job_manager = JobManager(workspace)
        intent = IntentSynthesizer.synthesize("Test", "test")
        job = job_manager.create_from_intent(intent, "test")
        job.job_id = job_id
        job_manager.save(job)

        status = log_reader.get_job_status(job_id)

        assert status["job_id"] == job_id
        assert "status" in status
        assert "created_at" in status

    def test_get_job_status_not_found(self, log_reader):
        """Test getting status of non-existent job."""
        status = log_reader.get_job_status("nonexistent-job")

        assert "error" in status

    def test_get_job_artifacts(self, workspace, log_reader):
        """Test listing job artifacts."""
        job_id = "test-job-1"

        # Create artifact
        artifact_dir = Path(workspace) / "artifacts" / job_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_file = artifact_dir / "test.txt"
        artifact_file.write_text("test content")

        artifacts = log_reader.get_job_artifacts(job_id)

        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "test.txt"

    def test_get_run_summary(self, workspace, log_reader):
        """Test getting run summary."""
        job_id = "test-job-1"
        run_record = self._create_sample_log(workspace, job_id)

        summary = log_reader.get_run_summary(job_id, run_record.run_id)

        assert summary["run_id"] == run_record.run_id
        assert summary["total_events"] == 4
        assert summary["status"] == "completed"
        assert summary["steps_started"] == 1
        assert summary["steps_completed"] == 1

    def test_print_events_all(self, workspace, log_reader, capsys):
        """Test printing all events."""
        job_id = "test-job-1"
        run_record = self._create_sample_log(workspace, job_id)

        log_reader.print_events(job_id)

        captured = capsys.readouterr()
        assert "job.started" in captured.out
        assert "job.completed" in captured.out

    def test_print_events_filtered_by_type(self, workspace, log_reader, capsys):
        """Test printing events filtered by type."""
        job_id = "test-job-1"
        run_record = self._create_sample_log(workspace, job_id)

        log_reader.print_events(job_id, event_type=EventType.STEP_STARTED)

        captured = capsys.readouterr()
        assert "step.started" in captured.out
        assert "job.started" not in captured.out

    def test_print_events_with_limit(self, workspace, log_reader, capsys):
        """Test printing limited number of events."""
        job_id = "test-job-1"
        run_record = self._create_sample_log(workspace, job_id)

        log_reader.print_events(job_id, n=2)

        captured = capsys.readouterr()
        lines = [l for l in captured.out.strip().split("\n") if l]
        assert len(lines) == 2

    def test_format_event_basic(self):
        """Test event formatting."""
        event = Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id="run-1",
            job_id="job-1",
        )

        formatted = LogReader._format_event(event)

        assert "2026-02-04T00:00:00Z" in formatted
        assert "job.started" in formatted

    def test_format_event_with_step(self):
        """Test event formatting with step."""
        event = Event(
            type=EventType.STEP_STARTED,
            timestamp="2026-02-04T00:00:01Z",
            run_id="run-1",
            job_id="job-1",
            step_id="step-1",
            worker_id="worker-1",
        )

        formatted = LogReader._format_event(event)

        assert "step.started" in formatted
        assert "step=step-1" in formatted
        assert "worker=worker-1" in formatted

    def test_format_event_with_payload(self):
        """Test event formatting with payload."""
        event = Event(
            type=EventType.STEP_COMPLETED,
            timestamp="2026-02-04T00:00:02Z",
            run_id="run-1",
            job_id="job-1",
            step_id="step-1",
            payload={"output": "test", "count": 42},
        )

        formatted = LogReader._format_event(event)

        assert "step.completed" in formatted
        assert "step=step-1" in formatted
        # Payload should be included
        assert "output" in formatted or "test" in formatted
