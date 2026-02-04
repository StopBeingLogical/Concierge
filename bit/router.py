"""Router for pipeline execution."""

from pathlib import Path
from typing import Optional, Any
import uuid
from datetime import datetime, UTC

from bit.plan import ExecutionPlan
from bit.events import Event, EventType, EventLog, RunRecord
from bit.workers_stub import WorkerStub, EchoWorker, FileWorker, CounterWorker


class RuntimeContext:
    """Runtime state during pipeline execution."""

    def __init__(self):
        """Initialize runtime context."""
        self.state: dict[str, Any] = {}

    def set(self, name: str, value: Any) -> None:
        """Set value in context.

        Args:
            name: Variable name
            value: Value to store
        """
        self.state[name] = value

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        """Get value from context.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            Any: Value or default
        """
        return self.state.get(name, default)

    def has(self, name: str) -> bool:
        """Check if name exists in context.

        Args:
            name: Variable name

        Returns:
            bool: True if exists
        """
        return name in self.state

    def to_dict(self) -> dict[str, Any]:
        """Get context as dict.

        Returns:
            dict: Current state
        """
        return self.state.copy()


class Router:
    """Pipeline router for sequential execution."""

    # Worker stub registry
    WORKERS = {
        "echo_worker": EchoWorker(),
        "file_copy_worker": FileWorker(),
        "counter_worker": CounterWorker(),
    }

    def __init__(self, workspace_path: str):
        """Initialize router.

        Args:
            workspace_path: Workspace root path
        """
        self.workspace_path = Path(workspace_path)

    def execute_plan(self, plan: ExecutionPlan) -> tuple[bool, RunRecord]:
        """Execute plan sequentially.

        Args:
            plan: ExecutionPlan to execute

        Returns:
            tuple: (success, run_record)
        """
        # Create run record
        run_record = RunRecord.create(plan.job_id, plan.plan_id)

        # Create event log
        logs_dir = self.workspace_path / "jobs" / plan.job_id / "logs"
        log_path = logs_dir / f"{run_record.run_id}.jsonl"
        event_log = EventLog(log_path)

        # Initialize context with resolved inputs
        context = RuntimeContext()
        for resolved_input in plan.resolved_inputs.inputs:
            context.set(resolved_input.name, resolved_input.value)

        # Emit job started event
        event_log.emit(Event(
            type=EventType.JOB_STARTED,
            timestamp=run_record.created_at,
            run_id=run_record.run_id,
            job_id=plan.job_id,
            payload={"plan_id": plan.plan_id},
        ))

        # Execute pipeline steps
        try:
            for step in plan.pipeline.steps:
                # Emit step started event
                event_log.emit(Event(
                    type=EventType.STEP_STARTED,
                    timestamp=self._now(),
                    run_id=run_record.run_id,
                    job_id=plan.job_id,
                    step_id=step.step_id,
                    payload={"worker_id": step.worker.worker_id},
                ))

                # Collect step inputs from context
                step_inputs = {}
                for input_name in step.inputs:
                    if context.has(input_name):
                        step_inputs[input_name] = context.get(input_name)
                    else:
                        raise ValueError(f"Step {step.step_id}: Input not found in context: {input_name}")

                # Invoke worker
                worker = self._get_worker(step.worker.worker_id)
                if not worker:
                    raise ValueError(f"Step {step.step_id}: Unknown worker: {step.worker.worker_id}")

                step_outputs = worker.execute(step_inputs, step.params)

                # Write outputs to context
                for output_name, output_value in step_outputs.items():
                    context.set(output_name, output_value)

                # Emit step completed event
                event_log.emit(Event(
                    type=EventType.STEP_COMPLETED,
                    timestamp=self._now(),
                    run_id=run_record.run_id,
                    job_id=plan.job_id,
                    step_id=step.step_id,
                    worker_id=step.worker.worker_id,
                    payload={"outputs": step_outputs},
                ))

            # Emit job completed event
            now = self._now()
            run_record.status = "completed"
            run_record.completed_at = now

            event_log.emit(Event(
                type=EventType.JOB_COMPLETED,
                timestamp=now,
                run_id=run_record.run_id,
                job_id=plan.job_id,
                payload={"context": context.to_dict()},
            ))

            return True, run_record

        except Exception as e:
            # Emit job failed event
            now = self._now()
            run_record.status = "failed"
            run_record.completed_at = now

            event_log.emit(Event(
                type=EventType.JOB_FAILED,
                timestamp=now,
                run_id=run_record.run_id,
                job_id=plan.job_id,
                payload={"error": str(e)},
            ))

            return False, run_record

    @staticmethod
    def _get_worker(worker_id: str) -> Optional[WorkerStub]:
        """Get worker by ID.

        Args:
            worker_id: Worker ID

        Returns:
            WorkerStub: Worker or None if not found
        """
        return Router.WORKERS.get(worker_id)

    @staticmethod
    def _now() -> str:
        """Get current ISO 8601 timestamp.

        Returns:
            str: Current timestamp
        """
        return datetime.now(UTC).isoformat().replace('+00:00', 'Z')
