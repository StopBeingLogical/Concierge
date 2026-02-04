"""Approval and authorization system."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class ApprovalDecision(str, Enum):
    """Approval decision types."""

    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"


class Approval(BaseModel):
    """Single approval record."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "plan_id": "plan-123",
            "decision": "granted",
            "requested_at": "2026-02-04T10:00:00Z",
            "granted_at": "2026-02-04T10:05:00Z",
            "approver": "user@example.com",
            "note": "Approved for testing"
        }
    })

    plan_id: str = Field(description="Plan ID being approved")
    decision: ApprovalDecision = Field(description="Approval decision")
    requested_at: str = Field(description="ISO 8601 timestamp when approval was requested")
    granted_at: Optional[str] = Field(default=None, description="ISO 8601 timestamp when decision was made")
    approver: Optional[str] = Field(default=None, description="User/system that made decision")
    note: Optional[str] = Field(default=None, description="Approval note or reason")

    @staticmethod
    def grant(plan_id: str, approver: str = "system", note: Optional[str] = None) -> "Approval":
        """Create a granted approval record.

        Args:
            plan_id: Plan ID
            approver: Approver identifier
            note: Optional approval note

        Returns:
            Approval: Granted approval record
        """
        now = datetime.utcnow().isoformat() + "Z"
        return Approval(
            plan_id=plan_id,
            decision=ApprovalDecision.GRANTED,
            requested_at=now,
            granted_at=now,
            approver=approver,
            note=note,
        )

    @staticmethod
    def deny(plan_id: str, approver: str = "system", reason: Optional[str] = None) -> "Approval":
        """Create a denied approval record.

        Args:
            plan_id: Plan ID
            approver: Approver identifier
            reason: Optional denial reason

        Returns:
            Approval: Denied approval record
        """
        now = datetime.utcnow().isoformat() + "Z"
        return Approval(
            plan_id=plan_id,
            decision=ApprovalDecision.DENIED,
            requested_at=now,
            granted_at=now,
            approver=approver,
            note=reason,
        )

    @staticmethod
    def request(plan_id: str) -> "Approval":
        """Create an approval request (pending).

        Args:
            plan_id: Plan ID

        Returns:
            Approval: Pending approval request
        """
        now = datetime.utcnow().isoformat() + "Z"
        return Approval(
            plan_id=plan_id,
            decision=ApprovalDecision.GRANTED,  # Default to granted for pending
            requested_at=now,
            granted_at=None,
            approver=None,
            note=None,
        )


class ApprovalLog:
    """Append-only log of approval records."""

    def __init__(self):
        """Initialize approval log."""
        self.approvals: list[Approval] = []

    def add(self, approval: Approval) -> None:
        """Add approval record to log.

        Args:
            approval: Approval record to add
        """
        self.approvals.append(approval)

    def get_latest(self, plan_id: str) -> Optional[Approval]:
        """Get latest approval for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            Approval: Latest approval record or None if not found
        """
        matching = [a for a in self.approvals if a.plan_id == plan_id]
        return matching[-1] if matching else None

    def get_all(self, plan_id: str) -> list[Approval]:
        """Get all approval records for a plan.

        Args:
            plan_id: Plan ID

        Returns:
            list[Approval]: All approval records for plan
        """
        return [a for a in self.approvals if a.plan_id == plan_id]

    def is_approved(self, plan_id: str) -> bool:
        """Check if plan is approved.

        Args:
            plan_id: Plan ID

        Returns:
            bool: True if plan has granted approval
        """
        latest = self.get_latest(plan_id)
        return latest is not None and latest.decision == ApprovalDecision.GRANTED and latest.granted_at is not None

    def is_denied(self, plan_id: str) -> bool:
        """Check if plan is denied.

        Args:
            plan_id: Plan ID

        Returns:
            bool: True if plan has denied approval
        """
        latest = self.get_latest(plan_id)
        return latest is not None and latest.decision == ApprovalDecision.DENIED

    def to_list(self) -> list[dict]:
        """Convert log to list of dicts for serialization.

        Returns:
            list[dict]: List of approval records as dicts
        """
        return [a.model_dump() for a in self.approvals]

    @staticmethod
    def from_list(data: list[dict]) -> "ApprovalLog":
        """Create approval log from list of dicts.

        Args:
            data: List of approval record dicts

        Returns:
            ApprovalLog: Approval log with loaded records
        """
        log = ApprovalLog()
        for record in data:
            approval = Approval(**record)
            log.add(approval)
        return log
