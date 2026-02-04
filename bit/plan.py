"""Execution plan models and management."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import yaml
from pydantic import BaseModel, Field, ConfigDict

from bit.workspace import Workspace
from bit.packages import Pipeline, TaskPackage


class ResolvedInput(BaseModel):
    """Resolved input value."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "audio_file",
            "type": "file",
            "value": "/path/to/audio.wav"
        }
    })

    name: str = Field(description="Input name")
    type: str = Field(description="Input type")
    value: str | int | bool | Any = Field(description="Resolved value")


class ResolvedInputs(BaseModel):
    """Collection of resolved inputs."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "inputs": []
        }
    })

    inputs: list[ResolvedInput] = Field(description="Resolved input values")


class ResourceRequirements(BaseModel):
    """Aggregated resource requirements for plan execution."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total_cpu_cores": 4,
            "gpu_required": False,
            "total_memory_mb": 2048,
            "total_disk_mb": 5000
        }
    })

    total_cpu_cores: int = Field(description="Total CPU cores required")
    gpu_required: bool = Field(description="Whether GPU is required")
    total_memory_mb: int = Field(description="Total memory in MB")
    total_disk_mb: int = Field(description="Total disk space in MB")


class ExecutionPlan(BaseModel):
    """Complete execution plan derived from package."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "plan_id": "plan-550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2026-02-04T12:00:00Z",
            "job_id": "job-550e8400-e29b-41d4-a716-446655440000",
            "package_id": "audio.extract",
            "package_version": "1.0.0",
            "matched_confidence": 0.95,
            "resolved_inputs": {"inputs": []},
            "pipeline": {},
            "resources": {}
        }
    })

    plan_id: str = Field(description="UUID v4 plan ID")
    created_at: str = Field(description="ISO 8601 timestamp")
    job_id: str = Field(description="Reference to job ID")
    package_id: str = Field(description="Matched package ID")
    package_version: str = Field(description="Package version")
    matched_confidence: float = Field(description="Confidence score of match (0.0-1.0)")
    resolved_inputs: ResolvedInputs = Field(description="Resolved input values")
    pipeline: Pipeline = Field(description="Execution pipeline from package")
    resources: ResourceRequirements = Field(description="Aggregated resource requirements")

    def to_canonical_dict(self) -> dict:
        """Return dict for hashing (excludes metadata).

        Returns:
            dict: Canonical representation for deterministic hashing
        """
        return {
            "job_id": self.job_id,
            "package_id": self.package_id,
            "package_version": self.package_version,
            "resolved_inputs": self.resolved_inputs.model_dump(),
            "pipeline": self.pipeline.model_dump(),
            "resources": self.resources.model_dump(),
        }

    def compute_hash(self) -> str:
        """Compute deterministic hash of plan.

        Returns:
            str: SHA256 hash (hex)
        """
        canonical = self.to_canonical_dict()
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return Workspace.hash_content(canonical_json)


class PlanManager:
    """Manages execution plan storage and retrieval."""

    PLANS_SUBDIR = "plans"
    PLAN_FILENAME = "plan.yaml"

    def __init__(self, workspace_path: str):
        """Initialize plan manager.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = Path(workspace_path)

    def _ensure_job_plans_dir(self, job_id: str) -> Path:
        """Ensure job plans directory exists.

        Args:
            job_id: Job ID

        Returns:
            Path: Path to plans directory for job
        """
        plans_dir = self.workspace_path / "jobs" / job_id / self.PLANS_SUBDIR
        plans_dir.mkdir(parents=True, exist_ok=True)
        return plans_dir

    def _get_plan_path(self, job_id: str, plan_id: str) -> Path:
        """Get path to plan.yaml file.

        Args:
            job_id: Job ID
            plan_id: Plan ID

        Returns:
            Path: Path to plan.yaml
        """
        return self.workspace_path / "jobs" / job_id / self.PLANS_SUBDIR / f"{plan_id}.yaml"

    def save(self, plan: ExecutionPlan) -> Path:
        """Save plan to yaml file.

        Args:
            plan: ExecutionPlan to save

        Returns:
            Path: Path to saved file
        """
        self._ensure_job_plans_dir(plan.job_id)
        plan_path = self._get_plan_path(plan.job_id, plan.plan_id)

        with open(plan_path, "w") as f:
            plan_dict = plan.model_dump(mode="json")
            yaml.dump(plan_dict, f, default_flow_style=False, sort_keys=False, indent=2)

        return plan_path

    def load(self, job_id: str, plan_id: str) -> Optional[ExecutionPlan]:
        """Load plan by ID.

        Args:
            job_id: Job ID
            plan_id: Plan ID

        Returns:
            ExecutionPlan: Loaded plan or None if not found/corrupted
        """
        plan_path = self._get_plan_path(job_id, plan_id)

        if not plan_path.exists():
            return None

        try:
            with open(plan_path, "r") as f:
                data = yaml.safe_load(f)
            return ExecutionPlan(**data)
        except (yaml.YAMLError, ValueError):
            return None

    def list_plans(self, job_id: str) -> list[ExecutionPlan]:
        """List all plans for a job.

        Args:
            job_id: Job ID

        Returns:
            list[ExecutionPlan]: All plans for job, sorted by created_at descending
        """
        plans_dir = self.workspace_path / "jobs" / job_id / self.PLANS_SUBDIR

        if not plans_dir.exists():
            return []

        plans = []
        for plan_file in plans_dir.glob("*.yaml"):
            try:
                with open(plan_file, "r") as f:
                    data = yaml.safe_load(f)
                plan = ExecutionPlan(**data)
                plans.append(plan)
            except (yaml.YAMLError, ValueError):
                # Skip corrupted files
                pass

        # Sort by created_at descending (newest first)
        plans.sort(key=lambda p: p.created_at, reverse=True)
        return plans

    def get_latest_plan(self, job_id: str) -> Optional[ExecutionPlan]:
        """Get the latest plan for a job.

        Args:
            job_id: Job ID

        Returns:
            ExecutionPlan: Latest plan or None if no plans exist
        """
        plans = self.list_plans(job_id)
        return plans[0] if plans else None
