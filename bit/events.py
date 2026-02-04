"""Event system for pipeline execution tracking."""

from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Optional, Any
import json

from pydantic import BaseModel, Field, ConfigDict


class EventType(str, Enum):
    """Pipeline execution event types."""

    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    WORKER_INVOKED = "worker.invoked"
    WORKER_OUTPUT = "worker.output"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"


class Event(BaseModel):
    """Single execution event."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "type": "job.started",
            "timestamp": "2026-02-04T12:00:00Z",
            "run_id": "run-123",
            "job_id": "job-456",
            "payload": {"status": "started"}
        }
    })

    type: EventType = Field(description="Event type")
    timestamp: str = Field(description="ISO 8601 timestamp")
    run_id: str = Field(description="Execution run ID")
    job_id: str = Field(description="Job ID")
    step_id: Optional[str] = Field(default=None, description="Step ID (if step-related)")
    worker_id: Optional[str] = Field(default=None, description="Worker ID (if worker-related)")
    payload: dict[str, Any] = Field(default={}, description="Event payload data")

    def to_jsonl(self) -> str:
        """Convert event to JSONL format (single line JSON).

        Returns:
            str: Event as JSON line (no newline)
        """
        return json.dumps(self.model_dump(mode="json"), separators=(",", ":"))


class EventLog:
    """Event log stored in JSONL format."""

    def __init__(self, log_path: Path):
        """Initialize event log.

        Args:
            log_path: Path to JSONL log file
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: Event) -> None:
        """Emit event to log.

        Args:
            event: Event to log
        """
        with open(self.log_path, "a") as f:
            f.write(event.to_jsonl() + "\n")

    def read(self) -> list[Event]:
        """Read all events from log.

        Returns:
            list[Event]: All logged events in order
        """
        if not self.log_path.exists():
            return []

        events = []
        with open(self.log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = Event(**data)
                    events.append(event)
                except (json.JSONDecodeError, ValueError):
                    # Skip malformed lines
                    pass

        return events

    def filter_by_type(self, event_type: EventType) -> list[Event]:
        """Filter events by type.

        Args:
            event_type: Event type to filter by

        Returns:
            list[Event]: Matching events
        """
        return [e for e in self.read() if e.type == event_type]

    def filter_by_step(self, step_id: str) -> list[Event]:
        """Filter events by step.

        Args:
            step_id: Step ID to filter by

        Returns:
            list[Event]: Matching events
        """
        return [e for e in self.read() if e.step_id == step_id]

    def get_latest(self, event_type: Optional[EventType] = None) -> Optional[Event]:
        """Get latest event, optionally filtered by type.

        Args:
            event_type: Optional event type filter

        Returns:
            Event: Latest event or None if no events
        """
        if event_type:
            events = self.filter_by_type(event_type)
        else:
            events = self.read()

        return events[-1] if events else None

    def tail(self, n: int = 10, event_type: Optional[EventType] = None) -> list[Event]:
        """Get last N events.

        Args:
            n: Number of events to return
            event_type: Optional event type filter

        Returns:
            list[Event]: Last N matching events
        """
        if event_type:
            events = self.filter_by_type(event_type)
        else:
            events = self.read()

        return events[-n:] if len(events) > 0 else []


class RunRecord(BaseModel):
    """Record of a single job execution run."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "run_id": "run-550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2026-02-04T12:00:00Z",
            "job_id": "job-123",
            "plan_id": "plan-456",
            "status": "running"
        }
    })

    run_id: str = Field(description="Unique run ID")
    created_at: str = Field(description="ISO 8601 timestamp when run started")
    job_id: str = Field(description="Job ID")
    plan_id: str = Field(description="Execution plan ID")
    status: str = Field(description="Run status (running, completed, failed)")
    completed_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp when run completed")

    @staticmethod
    def create(job_id: str, plan_id: str) -> "RunRecord":
        """Create new run record.

        Args:
            job_id: Job ID
            plan_id: Plan ID

        Returns:
            RunRecord: New run record
        """
        import uuid

        now = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
        return RunRecord(
            run_id=f"run-{uuid.uuid4()}",
            created_at=now,
            job_id=job_id,
            plan_id=plan_id,
            status="running",
        )
