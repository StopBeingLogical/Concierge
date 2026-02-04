"""Job specification and management."""

import json
import uuid
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ConfigDict

from bit.workspace import Workspace
from bit.intent import IntentManager
from bit.approval import Approval, ApprovalLog


class JobStatus(str, Enum):
    """Job lifecycle status."""

    DRAFT = "draft"
    PLANNED = "planned"
    APPROVED = "approved"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    HALTED = "halted"


class InputType(str, Enum):
    """Input parameter types."""

    FILE = "file"
    FOLDER = "folder"
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"


class OutputType(str, Enum):
    """Output artifact types."""

    FILE = "file"
    FOLDER = "folder"


class JobInput(BaseModel):
    """Job input parameter specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "audio_file",
            "type": "file",
            "value": "/path/to/audio.wav",
            "required": True
        }
    })

    name: str = Field(description="Input parameter name")
    type: InputType = Field(description="Input type")
    value: str | int | bool = Field(description="Input value")
    required: bool = Field(default=True, description="Whether input is required")


class JobOutput(BaseModel):
    """Job output artifact specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "artifacts",
            "type": "folder",
            "location": "artifacts/"
        }
    })

    name: str = Field(description="Output artifact name")
    type: OutputType = Field(description="Output type")
    location: str = Field(description="Output location path")


class ApprovalGates(BaseModel):
    """Approval gate configuration."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "required_on": ["destructive_operations", "large_compute_operations"]
        }
    })

    required_on: list[str] = Field(
        default=["destructive_operations", "large_compute_operations"],
        description="Operations requiring approval"
    )


class JobSpec(BaseModel):
    """Job specification schema."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "title": "Extract audio stems",
            "intent": "Extract stems from /music/song.wav",
            "success_criteria": ["Stems extracted successfully"],
            "constraints": [],
            "inputs": [],
            "outputs": [{"name": "artifacts", "type": "folder", "location": "artifacts/"}],
            "approval_gates": {"required_on": ["destructive_operations", "large_compute_operations"]}
        }
    })

    title: str = Field(description="Short title (first 100 chars of intent)")
    intent: str = Field(description="Full intent description")
    success_criteria: list[str] = Field(description="Success criteria (wrapped list)")
    constraints: list[str] = Field(default=[], description="Job constraints")
    inputs: list[JobInput] = Field(default=[], description="Input parameters")
    outputs: list[JobOutput] = Field(description="Output artifacts")
    approval_gates: ApprovalGates = Field(default_factory=ApprovalGates, description="Approval gate configuration")

    def to_canonical_dict(self) -> dict:
        """Return dict for hashing (excludes metadata).

        Returns:
            dict: Canonical representation with sorted keys for deterministic hashing
        """
        return {
            "title": self.title,
            "intent": self.intent,
            "success_criteria": sorted(self.success_criteria),
            "constraints": sorted(self.constraints),
            "inputs": sorted(
                [inp.model_dump() for inp in self.inputs],
                key=lambda x: x["name"]
            ),
            "outputs": sorted(
                [out.model_dump() for out in self.outputs],
                key=lambda x: x["name"]
            ),
            "approval_gates": self.approval_gates.model_dump(),
        }


class Job(BaseModel):
    """Job artifact schema."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "job_id": "job-550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2026-02-04T12:00:00Z",
            "intent_ref": "intent_550e8400e29b41d4a716446655440000",
            "intent_hash": "abc123def456...",
            "status": "draft",
            "mode_used": "code",
            "job_spec": {},
            "job_spec_hash": "xyz789...",
            "approvals": []
        }
    })

    job_id: str = Field(description="UUID v4 random job ID")
    created_at: str = Field(description="ISO 8601 timestamp with Z")
    intent_ref: str = Field(description="Reference to intent ID")
    intent_hash: str = Field(description="Hash of referenced intent")
    status: JobStatus = Field(description="Current job status")
    mode_used: str = Field(description="Mode this job was created in (audit)")
    job_spec: JobSpec = Field(description="Job specification")
    job_spec_hash: str = Field(description="SHA256 hash of job_spec")
    approvals: list[dict] = Field(default=[], description="Approval records (append-only log)")


class JobManager:
    """Manages job storage and retrieval."""

    JOBS_SUBDIR = "jobs"
    JOB_FILENAME = "job.yaml"

    def __init__(self, workspace_path: str):
        """Initialize job manager.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = Path(workspace_path)
        self.jobs_dir = self.workspace_path / self.JOBS_SUBDIR
        self.intent_manager = IntentManager(workspace_path)

    def _ensure_job_dir(self, job_id: str) -> Path:
        """Ensure job directory exists.

        Args:
            job_id: Job ID

        Returns:
            Path: Path to job directory
        """
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def _get_job_path(self, job_id: str) -> Path:
        """Get path to job.yaml file.

        Args:
            job_id: Job ID

        Returns:
            Path: Path to job.yaml
        """
        return self.jobs_dir / job_id / self.JOB_FILENAME

    @staticmethod
    def _compute_job_spec_hash(job_spec: JobSpec) -> str:
        """Compute deterministic hash of job spec.

        Args:
            job_spec: JobSpec to hash

        Returns:
            str: SHA256 hash (hex)
        """
        canonical = job_spec.to_canonical_dict()
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return Workspace.hash_content(canonical_json)

    def create_from_intent(self, intent, mode: str) -> Job:
        """Create job from intent.

        Args:
            intent: Intent object
            mode: Current mode name

        Returns:
            Job: Created job (not saved)
        """
        # Generate random job ID
        job_id = f"job-{uuid.uuid4()}"

        # Create job spec from intent
        # Wrap success_criteria in list if it's a string
        success_criteria = [intent.success_criteria] if isinstance(intent.success_criteria, str) else intent.success_criteria

        job_spec = JobSpec(
            title=intent.distilled_intent[:100],
            intent=intent.distilled_intent,
            success_criteria=success_criteria,
            constraints=intent.constraints,
            inputs=[],
            outputs=[JobOutput(
                name="artifacts",
                type=OutputType.FOLDER,
                location="artifacts/"
            )],
            approval_gates=ApprovalGates()
        )

        # Compute job spec hash
        job_spec_hash = self._compute_job_spec_hash(job_spec)

        # Create job
        job = Job(
            job_id=job_id,
            created_at=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            intent_ref=intent.intent_id,
            intent_hash=intent.intent_hash,
            status=JobStatus.DRAFT,
            mode_used=mode,
            job_spec=job_spec,
            job_spec_hash=job_spec_hash
        )

        return job

    def save(self, job: Job) -> Path:
        """Save job to yaml file.

        Args:
            job: Job to save

        Returns:
            Path: Path to saved file
        """
        self._ensure_job_dir(job.job_id)
        job_path = self._get_job_path(job.job_id)

        with open(job_path, "w") as f:
            job_dict = job.model_dump(mode="json")
            yaml.dump(job_dict, f, default_flow_style=False, sort_keys=False, indent=2)

        return job_path

    def load(self, job_id: str) -> Optional[Job]:
        """Load job by ID.

        Args:
            job_id: Job ID to load

        Returns:
            Job: Loaded job or None if not found/corrupted
        """
        job_path = self._get_job_path(job_id)

        if not job_path.exists():
            return None

        try:
            with open(job_path, "r") as f:
                data = yaml.safe_load(f)
            return Job(**data)
        except (yaml.YAMLError, ValueError):
            return None

    def list_jobs(self) -> list[Job]:
        """List all jobs, sorted by created_at descending.

        Returns:
            list[Job]: All jobs, newest first
        """
        if not self.jobs_dir.exists():
            return []

        jobs = []
        for job_file in self.jobs_dir.glob(f"*/{self.JOB_FILENAME}"):
            try:
                with open(job_file, "r") as f:
                    data = yaml.safe_load(f)
                job = Job(**data)
                jobs.append(job)
            except (yaml.YAMLError, ValueError):
                # Skip corrupted files
                pass

        # Sort by created_at descending (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs

    def verify_job_spec_hash(self, job: Job) -> bool:
        """Verify job spec hash is correct.

        Args:
            job: Job to verify

        Returns:
            bool: True if hash is valid
        """
        computed_hash = self._compute_job_spec_hash(job.job_spec)
        return computed_hash == job.job_spec_hash

    def verify_intent_hash(self, job: Job) -> bool:
        """Verify intent hash matches referenced intent.

        Args:
            job: Job to verify

        Returns:
            bool: True if intent hash is valid
        """
        intent = self.intent_manager.load(job.intent_hash)
        if not intent:
            return False
        return intent.intent_id == job.intent_ref and intent.intent_hash == job.intent_hash

    def get_approval_log(self, job: Job) -> ApprovalLog:
        """Get approval log for job.

        Args:
            job: Job to get approvals for

        Returns:
            ApprovalLog: Approval log with all records
        """
        return ApprovalLog.from_list(job.approvals)

    def approve_job(
        self,
        job: Job,
        plan_id: str,
        approver: str = "system",
        note: Optional[str] = None,
    ) -> Job:
        """Approve a job plan.

        Args:
            job: Job to approve
            plan_id: Plan ID being approved
            approver: Approver identifier
            note: Optional approval note

        Returns:
            Job: Updated job with approval

        Raises:
            ValueError: If job is not in PLANNED status
        """
        if job.status != JobStatus.PLANNED:
            raise ValueError(f"Cannot approve job in {job.status} status. Must be in PLANNED status.")

        # Add approval record
        approval = Approval.grant(plan_id, approver, note)
        job.approvals.append(approval.model_dump())

        # Update status
        job.status = JobStatus.APPROVED

        return job

    def deny_job(
        self,
        job: Job,
        plan_id: str,
        approver: str = "system",
        reason: Optional[str] = None,
    ) -> Job:
        """Deny a job plan.

        Args:
            job: Job to deny
            plan_id: Plan ID being denied
            approver: Approver identifier
            reason: Optional denial reason

        Returns:
            Job: Updated job with denial

        Raises:
            ValueError: If job is not in PLANNED status
        """
        if job.status != JobStatus.PLANNED:
            raise ValueError(f"Cannot deny job in {job.status} status. Must be in PLANNED status.")

        # Add denial record
        denial = Approval.deny(plan_id, approver, reason)
        job.approvals.append(denial.model_dump())

        # Status remains PLANNED (can try with different plan)
        return job

    def transition_to_planned(self, job: Job) -> Job:
        """Transition job from DRAFT to PLANNED.

        Args:
            job: Job to transition

        Returns:
            Job: Updated job

        Raises:
            ValueError: If job is not in DRAFT status
        """
        if job.status != JobStatus.DRAFT:
            raise ValueError(f"Cannot transition to PLANNED from {job.status} status. Must be in DRAFT status.")

        job.status = JobStatus.PLANNED
        return job

    def transition_to_running(self, job: Job) -> Job:
        """Transition job from APPROVED to RUNNING.

        Args:
            job: Job to transition

        Returns:
            Job: Updated job

        Raises:
            ValueError: If job is not in APPROVED status
        """
        if job.status != JobStatus.APPROVED:
            raise ValueError(f"Cannot transition to RUNNING from {job.status} status. Must be in APPROVED status.")

        job.status = JobStatus.RUNNING
        return job

    def complete_job(self, job: Job) -> Job:
        """Mark job as completed.

        Args:
            job: Job to complete

        Returns:
            Job: Updated job

        Raises:
            ValueError: If job is not in RUNNING status
        """
        if job.status != JobStatus.RUNNING:
            raise ValueError(f"Cannot complete job in {job.status} status. Must be in RUNNING status.")

        job.status = JobStatus.COMPLETED
        return job

    def fail_job(self, job: Job, reason: Optional[str] = None) -> Job:
        """Mark job as failed.

        Args:
            job: Job to fail
            reason: Optional failure reason

        Returns:
            Job: Updated job
        """
        job.status = JobStatus.FAILED
        return job

    def halt_job(self, job: Job, reason: Optional[str] = None) -> Job:
        """Mark job as halted.

        Args:
            job: Job to halt
            reason: Optional halt reason

        Returns:
            Job: Updated job
        """
        job.status = JobStatus.HALTED
        return job

    def is_approved(self, job: Job) -> bool:
        """Check if job is approved.

        Args:
            job: Job to check

        Returns:
            bool: True if job is approved
        """
        return job.status == JobStatus.APPROVED
