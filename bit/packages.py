"""Task package schema and models."""

import json
from enum import Enum
from typing import Optional, Any
from pathlib import Path
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict

from bit.workspace import Workspace


class WorkerStatus(str, Enum):
    """Worker availability status."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


class ContractField(BaseModel):
    """Input or output contract field specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "audio_file",
            "type": "file",
            "description": "Input audio file to process",
            "required": True
        }
    })

    name: str = Field(description="Field name")
    type: str = Field(description="Field type (file, folder, string, integer, etc)")
    description: str = Field(description="Field description")
    required: bool = Field(default=True, description="Whether field is required")


class Contract(BaseModel):
    """Input or output contract specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "fields": [{"name": "input_file", "type": "file", "description": "Input file", "required": True}]
        }
    })

    fields: list[ContractField] = Field(default=[], description="Contract fields")


class IntentSpec(BaseModel):
    """Intent matching specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "category": "audio",
            "verbs": ["extract", "separate"],
            "entities": ["stems", "tracks"],
            "confidence_threshold": 0.7,
            "match_rules": ["must contain verb 'extract'"]
        }
    })

    category: str = Field(description="Intent category (e.g., audio, video, ml)")
    verbs: list[str] = Field(default=[], description="Action verbs this package handles")
    entities: list[str] = Field(default=[], description="Entities/objects this package works with")
    confidence_threshold: float = Field(default=0.7, description="Minimum confidence score (0.0-1.0)")
    match_rules: list[str] = Field(default=[], description="Pattern matching rules")


class Worker(BaseModel):
    """Worker specification in pipeline."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "worker_id": "audio_extractor",
            "version": "1.0.0",
            "status": "available"
        }
    })

    worker_id: str = Field(description="Unique worker identifier")
    version: str = Field(description="Worker version (semver)")
    status: WorkerStatus = Field(default=WorkerStatus.AVAILABLE, description="Worker availability")


class PipelineStep(BaseModel):
    """Single step in execution pipeline."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "step_id": "step_1",
            "worker": {"worker_id": "audio_processor", "version": "1.0.0"},
            "inputs": ["audio_file"],
            "outputs": ["stems"],
            "params": {"format": "wav"}
        }
    })

    step_id: str = Field(description="Unique step identifier within pipeline")
    worker: Worker = Field(description="Worker to invoke")
    inputs: list[str] = Field(description="Input names from context")
    outputs: list[str] = Field(description="Output names to write to context")
    params: dict[str, Any] = Field(default={}, description="Worker-specific parameters")


class Pipeline(BaseModel):
    """Ordered pipeline of execution steps."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "steps": [
                {
                    "step_id": "step_1",
                    "worker": {"worker_id": "processor", "version": "1.0.0"},
                    "inputs": ["input"],
                    "outputs": ["output"],
                    "params": {}
                }
            ]
        }
    })

    steps: list[PipelineStep] = Field(description="Ordered pipeline steps")


class ApprovalPolicy(BaseModel):
    """Approval policy specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "required": False,
            "conditions": ["destructive_operation"]
        }
    })

    required: bool = Field(default=False, description="Whether approval is required")
    conditions: list[str] = Field(default=[], description="Conditions requiring approval")


class VerificationRule(BaseModel):
    """Rule for verifying package execution."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "output_exists",
            "description": "Verify output artifact exists",
            "check": "file_exists(stems_output)"
        }
    })

    name: str = Field(description="Verification rule name")
    description: str = Field(description="Rule description")
    check: str = Field(description="Check logic (pseudo-code or reference)")


class Verification(BaseModel):
    """Verification specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "required": True,
            "rules": []
        }
    })

    required: bool = Field(default=False, description="Whether verification is required")
    rules: list[VerificationRule] = Field(default=[], description="Verification rules")


class FailureMode(BaseModel):
    """Failure mode specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "timeout",
            "recovery": "retry",
            "max_retries": 3
        }
    })

    error: str = Field(description="Error type to handle")
    recovery: str = Field(description="Recovery strategy (retry, fallback, fail)")
    max_retries: int = Field(default=1, description="Maximum retry attempts")


class FailureHandling(BaseModel):
    """Failure handling specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "modes": [
                {"error": "timeout", "recovery": "retry", "max_retries": 3}
            ]
        }
    })

    modes: list[FailureMode] = Field(default=[], description="Failure mode handlers")


class ResourceProfile(BaseModel):
    """Resource requirements specification."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "cpu_cores": 2,
            "gpu_required": False,
            "memory_mb": 512,
            "disk_mb": 1000
        }
    })

    cpu_cores: int = Field(default=1, description="CPU cores required")
    gpu_required: bool = Field(default=False, description="Whether GPU is required")
    memory_mb: int = Field(default=512, description="Memory requirement in MB")
    disk_mb: int = Field(default=1000, description="Disk space requirement in MB")


class TaskPackage(BaseModel):
    """Complete task package specification (14 sections)."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "package_id": "audio.stem_extraction",
            "version": "1.0.0",
            "title": "Extract Audio Stems",
            "description": "Extract stems from audio files using ML",
            "intent": {"category": "audio", "verbs": ["extract"], "entities": ["stems"]},
            "input_contract": {"fields": []},
            "output_contract": {"fields": []},
            "pipeline": {"steps": []},
            "approval": {"required": False},
            "verification": {"required": False},
            "failure_handling": {"modes": []},
            "resources": {"cpu_cores": 2, "gpu_required": False},
            "metadata": {"created_at": "2026-02-04T00:00:00Z"}
        }
    })

    # Section 1: Identity & versioning
    package_id: str = Field(description="Unique package identifier (e.g., audio.stem_extraction)")
    version: str = Field(description="Semantic version (e.g., 1.0.0)")
    title: str = Field(description="Human-readable title")
    description: str = Field(description="Detailed description of package purpose")

    # Section 2: Intent matching rules
    intent: IntentSpec = Field(description="Intent matching specification")

    # Section 3: Input contract
    input_contract: Contract = Field(description="Input specification")

    # Section 4: Output contract
    output_contract: Contract = Field(description="Output specification")

    # Section 5: Pipeline
    pipeline: Pipeline = Field(description="Execution pipeline")

    # Section 6: Approval policies
    approval: ApprovalPolicy = Field(description="Approval requirements")

    # Section 7: Verification rules
    verification: Verification = Field(description="Verification specification")

    # Section 8: Failure handling
    failure_handling: FailureHandling = Field(description="Failure mode handlers")

    # Section 9: Resource requirements
    resources: ResourceProfile = Field(description="Resource requirements")

    # Section 10: Metadata
    metadata: dict[str, Any] = Field(default={}, description="Package metadata (created_at, etc)")

    # Note: Sections 11-14 can be extended in future phases
    # 11. Caching/memoization
    # 12. Monitoring/observability
    # 13. Security/isolation
    # 14. Cost/quota management

    def to_canonical_dict(self) -> dict:
        """Return dict for hashing (excludes metadata).

        Returns:
            dict: Canonical representation with sorted keys for deterministic hashing
        """
        return {
            "package_id": self.package_id,
            "version": self.version,
            "title": self.title,
            "description": self.description,
            "intent": self.intent.model_dump(),
            "input_contract": self.input_contract.model_dump(),
            "output_contract": self.output_contract.model_dump(),
            "pipeline": self.pipeline.model_dump(),
            "approval": self.approval.model_dump(),
            "verification": self.verification.model_dump(),
            "failure_handling": self.failure_handling.model_dump(),
            "resources": self.resources.model_dump(),
        }

    def compute_hash(self) -> str:
        """Compute deterministic hash of package.

        Returns:
            str: SHA256 hash (hex)
        """
        canonical = self.to_canonical_dict()
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        return Workspace.hash_content(canonical_json)
