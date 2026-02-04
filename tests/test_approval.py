"""Tests for approval and authorization system."""

import pytest
from tempfile import TemporaryDirectory

from bit.workspace import Workspace
from bit.approval import Approval, ApprovalDecision, ApprovalLog
from bit.job import Job, JobStatus, JobSpec, JobManager


class TestApproval:
    """Tests for Approval model."""

    def test_approval_grant(self):
        """Test creating a granted approval."""
        approval = Approval.grant("plan-123", "user@test.com", "Looks good")

        assert approval.plan_id == "plan-123"
        assert approval.decision == ApprovalDecision.GRANTED
        assert approval.approver == "user@test.com"
        assert approval.note == "Looks good"
        assert approval.granted_at is not None

    def test_approval_deny(self):
        """Test creating a denied approval."""
        approval = Approval.deny("plan-123", "user@test.com", "Needs review")

        assert approval.plan_id == "plan-123"
        assert approval.decision == ApprovalDecision.DENIED
        assert approval.approver == "user@test.com"
        assert approval.note == "Needs review"
        assert approval.granted_at is not None

    def test_approval_request(self):
        """Test creating an approval request."""
        approval = Approval.request("plan-123")

        assert approval.plan_id == "plan-123"
        assert approval.requested_at is not None
        assert approval.granted_at is None
        assert approval.approver is None


class TestApprovalLog:
    """Tests for ApprovalLog."""

    def test_approval_log_add(self):
        """Test adding approvals to log."""
        log = ApprovalLog()

        approval1 = Approval.grant("plan-1", "user1")
        approval2 = Approval.grant("plan-1", "user2")

        log.add(approval1)
        log.add(approval2)

        assert len(log.approvals) == 2

    def test_approval_log_get_latest(self):
        """Test getting latest approval for a plan."""
        log = ApprovalLog()

        approval1 = Approval.grant("plan-1", "user1")
        approval2 = Approval.deny("plan-1", "user2")

        log.add(approval1)
        log.add(approval2)

        latest = log.get_latest("plan-1")

        assert latest is not None
        assert latest.decision == ApprovalDecision.DENIED

    def test_approval_log_get_all(self):
        """Test getting all approvals for a plan."""
        log = ApprovalLog()

        approval1 = Approval.grant("plan-1", "user1")
        approval2 = Approval.grant("plan-1", "user2")
        approval3 = Approval.grant("plan-2", "user3")

        log.add(approval1)
        log.add(approval2)
        log.add(approval3)

        all_plan1 = log.get_all("plan-1")

        assert len(all_plan1) == 2
        assert all(a.plan_id == "plan-1" for a in all_plan1)

    def test_approval_log_is_approved(self):
        """Test checking if plan is approved."""
        log = ApprovalLog()

        approval = Approval.grant("plan-1", "user1")
        log.add(approval)

        assert log.is_approved("plan-1") is True
        assert log.is_approved("plan-2") is False

    def test_approval_log_is_denied(self):
        """Test checking if plan is denied."""
        log = ApprovalLog()

        approval = Approval.deny("plan-1", "user1")
        log.add(approval)

        assert log.is_denied("plan-1") is True
        assert log.is_denied("plan-2") is False

    def test_approval_log_serialization(self):
        """Test serializing and deserializing approval log."""
        log = ApprovalLog()

        approval1 = Approval.grant("plan-1", "user1")
        approval2 = Approval.deny("plan-1", "user2")

        log.add(approval1)
        log.add(approval2)

        # Serialize
        data = log.to_list()

        assert len(data) == 2
        assert data[0]["plan_id"] == "plan-1"

        # Deserialize
        log2 = ApprovalLog.from_list(data)

        assert len(log2.approvals) == 2
        assert log2.get_latest("plan-1").decision == ApprovalDecision.DENIED


class TestJobStateTransitions:
    """Tests for job state machine transitions."""

    @pytest.fixture
    def workspace(self):
        """Create temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    @pytest.fixture
    def job_manager(self, workspace):
        """Create job manager for testing."""
        return JobManager(workspace)

    @pytest.fixture
    def sample_job(self, job_manager):
        """Create a sample job for testing."""
        from bit.intent import IntentSynthesizer

        intent = IntentSynthesizer.synthesize("Test intent", "test")
        job = job_manager.create_from_intent(intent, "test")
        return job

    def test_job_transition_draft_to_planned(self, job_manager, sample_job):
        """Test DRAFT -> PLANNED transition."""
        assert sample_job.status == JobStatus.DRAFT

        job_updated = job_manager.transition_to_planned(sample_job)

        assert job_updated.status == JobStatus.PLANNED

    def test_job_transition_planned_to_approved(self, job_manager, sample_job):
        """Test PLANNED -> APPROVED transition."""
        sample_job.status = JobStatus.PLANNED

        job_updated = job_manager.approve_job(sample_job, "plan-1")

        assert job_updated.status == JobStatus.APPROVED

    def test_job_transition_approved_to_running(self, job_manager, sample_job):
        """Test APPROVED -> RUNNING transition."""
        sample_job.status = JobStatus.APPROVED

        job_updated = job_manager.transition_to_running(sample_job)

        assert job_updated.status == JobStatus.RUNNING

    def test_job_transition_running_to_completed(self, job_manager, sample_job):
        """Test RUNNING -> COMPLETED transition."""
        sample_job.status = JobStatus.RUNNING

        job_updated = job_manager.complete_job(sample_job)

        assert job_updated.status == JobStatus.COMPLETED

    def test_job_transition_to_failed(self, job_manager, sample_job):
        """Test transition to FAILED status."""
        sample_job.status = JobStatus.RUNNING

        job_updated = job_manager.fail_job(sample_job)

        assert job_updated.status == JobStatus.FAILED

    def test_job_transition_to_halted(self, job_manager, sample_job):
        """Test transition to HALTED status."""
        sample_job.status = JobStatus.RUNNING

        job_updated = job_manager.halt_job(sample_job)

        assert job_updated.status == JobStatus.HALTED

    def test_job_invalid_transition(self, job_manager, sample_job):
        """Test invalid state transition raises error."""
        sample_job.status = JobStatus.DRAFT

        with pytest.raises(ValueError):
            job_manager.transition_to_running(sample_job)

    def test_job_cannot_approve_in_draft(self, job_manager, sample_job):
        """Test cannot approve job in DRAFT status."""
        assert sample_job.status == JobStatus.DRAFT

        with pytest.raises(ValueError):
            job_manager.approve_job(sample_job, "plan-1")

    def test_job_cannot_deny_in_draft(self, job_manager, sample_job):
        """Test cannot deny job in DRAFT status."""
        assert sample_job.status == JobStatus.DRAFT

        with pytest.raises(ValueError):
            job_manager.deny_job(sample_job, "plan-1")

    def test_job_approve_adds_approval_record(self, job_manager, sample_job):
        """Test approval adds record to job."""
        sample_job.status = JobStatus.PLANNED

        job_updated = job_manager.approve_job(sample_job, "plan-1", "test-user", "Good to go")

        assert len(job_updated.approvals) > 0
        approval = job_updated.approvals[0]
        assert approval["plan_id"] == "plan-1"
        assert approval["decision"] == "granted"

    def test_job_deny_adds_denial_record(self, job_manager, sample_job):
        """Test denial adds record to job."""
        sample_job.status = JobStatus.PLANNED

        job_updated = job_manager.deny_job(sample_job, "plan-1", "test-user", "Needs review")

        assert len(job_updated.approvals) > 0
        approval = job_updated.approvals[0]
        assert approval["plan_id"] == "plan-1"
        assert approval["decision"] == "denied"

    def test_job_is_approved(self, job_manager, sample_job):
        """Test is_approved check."""
        assert not job_manager.is_approved(sample_job)

        sample_job.status = JobStatus.APPROVED
        assert job_manager.is_approved(sample_job)

    def test_job_get_approval_log(self, job_manager, sample_job):
        """Test getting approval log from job."""
        sample_job.status = JobStatus.PLANNED
        sample_job = job_manager.approve_job(sample_job, "plan-1")

        log = job_manager.get_approval_log(sample_job)

        assert log is not None
        assert log.is_approved("plan-1")

    def test_complete_workflow_sequence(self, job_manager, sample_job):
        """Test complete workflow: DRAFT -> PLANNED -> APPROVED -> RUNNING -> COMPLETED."""
        # DRAFT -> PLANNED
        sample_job = job_manager.transition_to_planned(sample_job)
        assert sample_job.status == JobStatus.PLANNED

        # PLANNED -> APPROVED
        sample_job = job_manager.approve_job(sample_job, "plan-1")
        assert sample_job.status == JobStatus.APPROVED

        # APPROVED -> RUNNING
        sample_job = job_manager.transition_to_running(sample_job)
        assert sample_job.status == JobStatus.RUNNING

        # RUNNING -> COMPLETED
        sample_job = job_manager.complete_job(sample_job)
        assert sample_job.status == JobStatus.COMPLETED
