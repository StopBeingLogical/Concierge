"""Tests for router and event system."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from bit.workspace import Workspace
from bit.plan import ExecutionPlan, ResolvedInputs, ResolvedInput, ResourceRequirements
from bit.packages import Pipeline, PipelineStep, Worker
from bit.router import Router, RuntimeContext
from bit.events import Event, EventType, EventLog, RunRecord
from bit.workers_stub import EchoWorker, FileWorker


class TestRuntimeContext:
    """Tests for RuntimeContext."""

    def test_context_set_get(self):
        """Test setting and getting values in context."""
        ctx = RuntimeContext()

        ctx.set("key1", "value1")
        assert ctx.get("key1") == "value1"

    def test_context_get_default(self):
        """Test getting value with default."""
        ctx = RuntimeContext()

        value = ctx.get("nonexistent", "default")
        assert value == "default"

    def test_context_has(self):
        """Test checking if key exists."""
        ctx = RuntimeContext()

        ctx.set("key1", "value1")
        assert ctx.has("key1") is True
        assert ctx.has("key2") is False

    def test_context_to_dict(self):
        """Test converting context to dict."""
        ctx = RuntimeContext()

        ctx.set("key1", "value1")
        ctx.set("key2", "value2")

        d = ctx.to_dict()
        assert d == {"key1": "value1", "key2": "value2"}


class TestEvent:
    """Tests for Event model."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id="run-1",
            job_id="job-1",
        )

        assert event.type == EventType.JOB_STARTED
        assert event.run_id == "run-1"

    def test_event_to_jsonl(self):
        """Test converting event to JSONL format."""
        event = Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id="run-1",
            job_id="job-1",
            payload={"status": "started"},
        )

        jsonl = event.to_jsonl()

        # Should be valid JSON
        data = json.loads(jsonl)
        assert data["type"] == "job.started"
        assert data["run_id"] == "run-1"


class TestEventLog:
    """Tests for EventLog."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_event_log_emit(self, temp_dir):
        """Test emitting events to log."""
        log_path = Path(temp_dir) / "test.jsonl"
        log = EventLog(log_path)

        event = Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id="run-1",
            job_id="job-1",
        )

        log.emit(event)

        assert log_path.exists()

    def test_event_log_read(self, temp_dir):
        """Test reading events from log."""
        log_path = Path(temp_dir) / "test.jsonl"
        log = EventLog(log_path)

        event1 = Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id="run-1",
            job_id="job-1",
        )
        event2 = Event(
            type=EventType.JOB_COMPLETED,
            timestamp="2026-02-04T00:01:00Z",
            run_id="run-1",
            job_id="job-1",
        )

        log.emit(event1)
        log.emit(event2)

        events = log.read()

        assert len(events) == 2
        assert events[0].type == EventType.JOB_STARTED
        assert events[1].type == EventType.JOB_COMPLETED

    def test_event_log_filter_by_type(self, temp_dir):
        """Test filtering events by type."""
        log_path = Path(temp_dir) / "test.jsonl"
        log = EventLog(log_path)

        log.emit(Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id="run-1",
            job_id="job-1",
        ))
        log.emit(Event(
            type=EventType.STEP_STARTED,
            timestamp="2026-02-04T00:00:01Z",
            run_id="run-1",
            job_id="job-1",
            step_id="step-1",
        ))

        started_events = log.filter_by_type(EventType.JOB_STARTED)

        assert len(started_events) == 1
        assert started_events[0].type == EventType.JOB_STARTED

    def test_event_log_get_latest(self, temp_dir):
        """Test getting latest event."""
        log_path = Path(temp_dir) / "test.jsonl"
        log = EventLog(log_path)

        log.emit(Event(
            type=EventType.JOB_STARTED,
            timestamp="2026-02-04T00:00:00Z",
            run_id="run-1",
            job_id="job-1",
        ))
        log.emit(Event(
            type=EventType.JOB_COMPLETED,
            timestamp="2026-02-04T00:00:10Z",
            run_id="run-1",
            job_id="job-1",
        ))

        latest = log.get_latest()

        assert latest is not None
        assert latest.type == EventType.JOB_COMPLETED

    def test_event_log_tail(self, temp_dir):
        """Test tailing events."""
        log_path = Path(temp_dir) / "test.jsonl"
        log = EventLog(log_path)

        for i in range(5):
            log.emit(Event(
                type=EventType.STEP_STARTED,
                timestamp=f"2026-02-04T00:00:{i:02d}Z",
                run_id="run-1",
                job_id="job-1",
            ))

        last_3 = log.tail(3)

        assert len(last_3) == 3


class TestRunRecord:
    """Tests for RunRecord."""

    def test_run_record_create(self):
        """Test creating run record."""
        record = RunRecord.create("job-1", "plan-1")

        assert record.job_id == "job-1"
        assert record.plan_id == "plan-1"
        assert record.status == "running"
        assert record.completed_at is None

    def test_run_record_complete(self):
        """Test completing run record."""
        record = RunRecord.create("job-1", "plan-1")

        record.status = "completed"
        record.completed_at = "2026-02-04T00:01:00Z"

        assert record.status == "completed"
        assert record.completed_at is not None


class TestRouter:
    """Tests for Router."""

    @pytest.fixture
    def workspace(self):
        """Create temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    @pytest.fixture
    def router(self, workspace):
        """Create router for testing."""
        return Router(workspace)

    @pytest.fixture
    def echo_plan(self):
        """Create echo execution plan for testing."""
        return ExecutionPlan(
            plan_id="plan-1",
            created_at="2026-02-04T00:00:00Z",
            job_id="job-1",
            package_id="test.echo",
            package_version="1.0.0",
            matched_confidence=0.95,
            resolved_inputs=ResolvedInputs(inputs=[
                ResolvedInput(
                    name="message",
                    type="string",
                    value="Hello World",
                )
            ]),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="echo_worker", version="1.0.0"),
                    inputs=["message"],
                    outputs=["output"],
                    params={"timestamp": True},
                )
            ]),
            resources=ResourceRequirements(
                total_cpu_cores=1,
                gpu_required=False,
                total_memory_mb=512,
                total_disk_mb=1000,
            ),
        )

    def test_router_execute_plan_success(self, router, echo_plan):
        """Test executing plan successfully."""
        success, run_record = router.execute_plan(echo_plan)

        assert success is True
        assert run_record.status == "completed"
        assert run_record.completed_at is not None

    def test_router_creates_event_log(self, router, workspace, echo_plan):
        """Test that router creates event log."""
        success, run_record = router.execute_plan(echo_plan)

        log_path = Path(workspace) / "jobs" / echo_plan.job_id / "logs" / f"{run_record.run_id}.jsonl"
        assert log_path.exists()

    def test_router_emits_job_events(self, router, workspace, echo_plan):
        """Test that router emits job lifecycle events."""
        success, run_record = router.execute_plan(echo_plan)

        log_path = Path(workspace) / "jobs" / echo_plan.job_id / "logs" / f"{run_record.run_id}.jsonl"
        log = EventLog(log_path)

        events = log.read()

        # Should have job started, step started, step completed, job completed
        types = [e.type for e in events]
        assert EventType.JOB_STARTED in types
        assert EventType.JOB_COMPLETED in types

    def test_router_emits_step_events(self, router, workspace, echo_plan):
        """Test that router emits step events."""
        success, run_record = router.execute_plan(echo_plan)

        log_path = Path(workspace) / "jobs" / echo_plan.job_id / "logs" / f"{run_record.run_id}.jsonl"
        log = EventLog(log_path)

        step_events = log.filter_by_type(EventType.STEP_STARTED)

        assert len(step_events) > 0

    def test_router_missing_input_fails(self, router):
        """Test that router fails with missing input."""
        plan = ExecutionPlan(
            plan_id="plan-1",
            created_at="2026-02-04T00:00:00Z",
            job_id="job-1",
            package_id="test.echo",
            package_version="1.0.0",
            matched_confidence=0.95,
            resolved_inputs=ResolvedInputs(inputs=[]),  # Missing required input
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="echo_worker", version="1.0.0"),
                    inputs=["message"],  # Requires message input
                    outputs=["output"],
                    params={},
                )
            ]),
            resources=ResourceRequirements(
                total_cpu_cores=1,
                gpu_required=False,
                total_memory_mb=512,
                total_disk_mb=1000,
            ),
        )

        success, run_record = router.execute_plan(plan)

        assert success is False
        assert run_record.status == "failed"
