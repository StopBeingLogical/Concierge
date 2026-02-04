"""Log reading and filtering utilities."""

from pathlib import Path
from typing import Optional
from datetime import datetime

from bit.events import Event, EventLog, EventType
from bit.plan import PlanManager
from bit.job import JobManager


class LogReader:
    """Reads and filters logs for a job."""

    def __init__(self, workspace_path: str):
        """Initialize log reader.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = Path(workspace_path)
        self.job_manager = JobManager(workspace_path)
        self.plan_manager = PlanManager(workspace_path)

    def get_latest_run_log(self, job_id: str) -> Optional[EventLog]:
        """Get event log for latest run of a job.

        Args:
            job_id: Job ID

        Returns:
            EventLog: Latest run log or None if not found
        """
        logs_dir = self.workspace_path / "jobs" / job_id / "logs"

        if not logs_dir.exists():
            return None

        # Find latest JSONL file
        log_files = sorted(logs_dir.glob("run-*.jsonl"), reverse=True)

        if not log_files:
            return None

        return EventLog(log_files[0])

    def get_run_log(self, job_id: str, run_id: str) -> Optional[EventLog]:
        """Get event log for specific run.

        Args:
            job_id: Job ID
            run_id: Run ID

        Returns:
            EventLog: Run log or None if not found
        """
        log_path = self.workspace_path / "jobs" / job_id / "logs" / f"{run_id}.jsonl"

        if not log_path.exists():
            return None

        return EventLog(log_path)

    def get_job_status(self, job_id: str) -> dict:
        """Get current status of a job.

        Args:
            job_id: Job ID

        Returns:
            dict: Job status info
        """
        job = self.job_manager.load(job_id)

        if not job:
            return {"error": f"Job not found: {job_id}"}

        log = self.get_latest_run_log(job_id)

        status_info = {
            "job_id": job_id,
            "status": job.status.value,
            "created_at": job.created_at,
            "title": job.job_spec.title,
            "intent": job.job_spec.intent,
        }

        if log:
            events = log.read()
            status_info["total_events"] = len(events)

            # Find latest event
            if events:
                latest = events[-1]
                status_info["latest_event"] = latest.type.value
                status_info["latest_timestamp"] = latest.timestamp

                # Find current step
                step_events = log.filter_by_type(EventType.STEP_STARTED)
                if step_events:
                    status_info["current_step"] = step_events[-1].step_id

        return status_info

    def get_job_artifacts(self, job_id: str) -> list[dict]:
        """List artifacts produced by a job.

        Args:
            job_id: Job ID

        Returns:
            list[dict]: List of artifact info dicts
        """
        artifacts_dir = self.workspace_path / "artifacts" / job_id

        if not artifacts_dir.exists():
            return []

        artifacts = []
        for artifact_file in artifacts_dir.rglob("*"):
            if artifact_file.is_file():
                artifacts.append({
                    "name": artifact_file.name,
                    "path": str(artifact_file),
                    "size": artifact_file.stat().st_size,
                    "modified": datetime.fromtimestamp(artifact_file.stat().st_mtime).isoformat(),
                })

        return artifacts

    def get_run_summary(self, job_id: str, run_id: str) -> dict:
        """Get summary of a run.

        Args:
            job_id: Job ID
            run_id: Run ID

        Returns:
            dict: Run summary
        """
        log = self.get_run_log(job_id, run_id)

        if not log:
            return {"error": f"Run not found: {run_id}"}

        events = log.read()

        if not events:
            return {"run_id": run_id, "events": 0}

        job_started = log.get_latest(EventType.JOB_STARTED)
        job_completed = log.get_latest(EventType.JOB_COMPLETED)
        job_failed = log.get_latest(EventType.JOB_FAILED)

        summary = {
            "run_id": run_id,
            "total_events": len(events),
            "started_at": job_started.timestamp if job_started else None,
            "completed_at": job_completed.timestamp if job_completed else None,
            "failed_at": job_failed.timestamp if job_failed else None,
            "status": "completed" if job_completed else ("failed" if job_failed else "running"),
        }

        # Count step events
        step_starts = log.filter_by_type(EventType.STEP_STARTED)
        step_completions = log.filter_by_type(EventType.STEP_COMPLETED)

        summary["steps_started"] = len(step_starts)
        summary["steps_completed"] = len(step_completions)

        return summary

    def print_events(
        self,
        job_id: str,
        run_id: Optional[str] = None,
        event_type: Optional[EventType] = None,
        n: Optional[int] = None,
    ) -> None:
        """Print events for a run.

        Args:
            job_id: Job ID
            run_id: Optional run ID (uses latest if not specified)
            event_type: Optional event type filter
            n: Optional limit on number of events to show
        """
        if run_id:
            log = self.get_run_log(job_id, run_id)
        else:
            log = self.get_latest_run_log(job_id)

        if not log:
            print(f"No log found for job: {job_id}")
            return

        if event_type:
            events = log.filter_by_type(event_type)
        else:
            events = log.read()

        if n:
            events = events[-n:]

        for event in events:
            print(self._format_event(event))

    @staticmethod
    def _format_event(event: Event) -> str:
        """Format event for display.

        Args:
            event: Event to format

        Returns:
            str: Formatted event string
        """
        parts = [
            f"[{event.timestamp}]",
            f"{event.type.value}",
        ]

        if event.step_id:
            parts.append(f"step={event.step_id}")

        if event.worker_id:
            parts.append(f"worker={event.worker_id}")

        if event.payload:
            payload_str = ", ".join(f"{k}={v}" for k, v in event.payload.items())
            parts.append(payload_str)

        return " | ".join(parts)
