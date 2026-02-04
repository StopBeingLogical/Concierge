"""Stub worker implementations for testing."""

from abc import ABC, abstractmethod
from datetime import datetime, UTC
from pathlib import Path
from typing import Any


class WorkerStub(ABC):
    """Abstract base class for stub workers."""

    @abstractmethod
    def execute(self, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Execute worker with inputs and parameters.

        Args:
            inputs: Input values from context
            params: Worker-specific parameters

        Returns:
            dict: Output values to write to context
        """
        pass


class EchoWorker(WorkerStub):
    """Echo worker that echoes input to output."""

    def execute(self, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Echo the input message.

        Inputs:
            message: Message to echo

        Params:
            timestamp: Whether to add timestamp (default: True)

        Outputs:
            output: Echoed message
        """
        message = inputs.get("message", "")
        add_timestamp = params.get("timestamp", True)

        if add_timestamp:
            now = datetime.now(UTC).isoformat().replace('+00:00', 'Z')
            output = f"{message} [echoed at {now}]"
        else:
            output = f"{message} [echoed]"

        return {"output": output}


class FileWorker(WorkerStub):
    """File copy worker that copies files."""

    def execute(self, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Copy a file from source to destination.

        Inputs:
            source_file: Source file path
            destination_path: Destination file path

        Params:
            preserve_metadata: Whether to preserve metadata (default: True)

        Outputs:
            copied_file: Path to copied file
        """
        source_file = inputs.get("source_file", "")
        destination_path = inputs.get("destination_path", "")

        if not source_file or not destination_path:
            raise ValueError("source_file and destination_path are required")

        # For stub purposes, just simulate file copy by creating destination
        source_path = Path(source_file)
        dest_path = Path(destination_path)

        # In a real worker, we would copy the file
        # For stub, we just record the operation
        if not dest_path.parent.exists():
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a marker file to indicate copy was performed
        dest_path.touch()

        return {"copied_file": str(dest_path.absolute())}


class SleepWorker(WorkerStub):
    """Sleep worker that sleeps for a given duration."""

    def execute(self, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Sleep for specified duration.

        Params:
            seconds: Duration to sleep in seconds (default: 1)

        Outputs:
            slept_duration: How long we slept
        """
        import time

        duration = params.get("seconds", 1)
        time.sleep(duration)

        return {"slept_duration": duration}


class CounterWorker(WorkerStub):
    """Counter worker that counts items."""

    def execute(self, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Count items in a list or string.

        Inputs:
            items: Items to count (list or string)

        Outputs:
            count: Number of items
        """
        items = inputs.get("items", [])

        if isinstance(items, str):
            count = len(items)
        elif isinstance(items, (list, tuple)):
            count = len(items)
        else:
            count = 0

        return {"count": count}
