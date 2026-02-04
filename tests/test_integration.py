"""End-to-end integration tests for complete workflow."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from bit.workspace import Workspace
from bit.modes import SessionManager
from bit.intent import IntentSynthesizer, IntentManager
from bit.job import JobManager, JobStatus
from bit.packages import TaskPackage, IntentSpec, Contract, Pipeline, PipelineStep, Worker, ApprovalPolicy, Verification, FailureHandling, ResourceProfile
from bit.registry import PackageRegistry
from bit.planner import Planner
from bit.plan import PlanManager
from bit.router import Router
from bit.logs import LogReader


class TestCompleteWorkflow:
    """Integration tests for complete workflow."""

    @pytest.fixture
    def workspace(self):
        """Create and initialize a workspace."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    def test_end_to_end_workflow(self, workspace):
        """Test complete workflow: intent → job → plan → approve → run."""
        # 1. Set up mode
        session = SessionManager(workspace)
        state = session.set_mode("code")
        assert state.active_mode == "code"

        # 2. Create intent
        intent_text = "Echo the message test for workflow"
        intent_synth = IntentSynthesizer.synthesize(intent_text, "code")
        intent_manager = IntentManager(workspace)
        intent_manager.save(intent_synth)

        # 3. Create job from intent
        job_manager = JobManager(workspace)
        job = job_manager.create_from_intent(intent_synth, "code")
        assert job.status == JobStatus.DRAFT
        job_manager.save(job)

        # 4. Set up package registry with test echo package
        registry = PackageRegistry(workspace)
        pkg = TaskPackage(
            package_id="test.echo",
            version="1.0.0",
            title="Echo Test",
            description="Test echo package",
            intent=IntentSpec(
                category="test",
                verbs=["echo", "test"],
                entities=["message"],
                confidence_threshold=0.5,
            ),
            input_contract=Contract(),
            output_contract=Contract(),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="echo_worker", version="1.0.0"),
                    inputs=[],
                    outputs=["output"],
                    params={"timestamp": True},
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )
        registry.add_package(pkg)

        # 5. Transition job to PLANNED
        job = job_manager.transition_to_planned(job)
        assert job.status == JobStatus.PLANNED
        job_manager.save(job)

        # 6. Generate plan
        planner = Planner(registry)
        match_result = planner.match_package(job.job_spec)
        assert match_result is not None

        package, confidence = match_result
        assert confidence > 0.0

        plan = planner.generate_plan(job, package, confidence)
        plan_manager = PlanManager(workspace)
        plan_manager.save(plan)

        # 7. Approve job
        job = job_manager.approve_job(job, plan.plan_id, approver="test_user", note="Approved for testing")
        assert job.status == JobStatus.APPROVED
        job_manager.save(job)

        # 8. Transition to RUNNING
        job = job_manager.transition_to_running(job)
        assert job.status == JobStatus.RUNNING
        job_manager.save(job)

        # 9. Execute plan
        router = Router(workspace)
        success, run_record = router.execute_plan(plan)

        assert success is True
        assert run_record.status == "completed"

        # 10. Verify completion
        job = job_manager.complete_job(job)
        assert job.status == JobStatus.COMPLETED
        job_manager.save(job)

        # 11. Check logs
        log_reader = LogReader(workspace)
        status = log_reader.get_job_status(job.job_id)

        assert status["status"] == "completed"
        assert "current_step" in status or "latest_event" in status

    def test_multi_step_pipeline(self, workspace):
        """Test workflow with multiple pipeline steps."""
        # Set up workspace
        session = SessionManager(workspace)
        session.set_mode("code")

        # Create a multi-step package
        registry = PackageRegistry(workspace)
        pkg = TaskPackage(
            package_id="test.multi",
            version="1.0.0",
            title="Multi-Step Test",
            description="Test package with multiple steps",
            intent=IntentSpec(category="test", verbs=["test", "multi"]),
            input_contract=Contract(),
            output_contract=Contract(),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="echo_worker", version="1.0.0"),
                    inputs=[],
                    outputs=["output1"],
                    params={"timestamp": False},
                ),
                PipelineStep(
                    step_id="step_2",
                    worker=Worker(worker_id="echo_worker", version="1.0.0"),
                    inputs=[],
                    outputs=["output2"],
                    params={"timestamp": False},
                ),
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )
        registry.add_package(pkg)

        # Create intent and job
        intent = IntentSynthesizer.synthesize("Multi-step test", "code")
        intent_manager = IntentManager(workspace)
        intent_manager.save(intent)

        job_manager = JobManager(workspace)
        job = job_manager.create_from_intent(intent, "code")
        job_manager.save(job)

        # Plan and execute
        planner = Planner(registry)
        match = planner.match_package(job.job_spec)
        assert match is not None

        package, confidence = match
        plan = planner.generate_plan(job, package, confidence)
        plan_manager = PlanManager(workspace)
        plan_manager.save(plan)

        router = Router(workspace)
        success, run_record = router.execute_plan(plan)

        assert success is True
        assert run_record.status == "completed"

        # Verify both steps executed
        log_reader = LogReader(workspace)
        summary = log_reader.get_run_summary(job.job_id, run_record.run_id)

        assert summary["steps_started"] == 2
        assert summary["steps_completed"] == 2

    def test_approval_denial_workflow(self, workspace):
        """Test workflow with plan denial and retry."""
        # Set up
        session = SessionManager(workspace)
        session.set_mode("code")

        registry = PackageRegistry(workspace)
        pkg = TaskPackage(
            package_id="test.echo",
            version="1.0.0",
            title="Echo",
            description="Echo",
            intent=IntentSpec(category="test"),
            input_contract=Contract(),
            output_contract=Contract(),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="echo_worker", version="1.0.0"),
                    inputs=[],
                    outputs=[],
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )
        registry.add_package(pkg)

        # Create job
        intent = IntentSynthesizer.synthesize("Test", "code")
        intent_manager = IntentManager(workspace)
        intent_manager.save(intent)

        job_manager = JobManager(workspace)
        job = job_manager.create_from_intent(intent, "code")
        job = job_manager.transition_to_planned(job)
        job_manager.save(job)

        # Generate first plan
        planner = Planner(registry)
        match = planner.match_package(job.job_spec)
        package, confidence = match

        plan1 = planner.generate_plan(job, package, confidence)
        plan_manager = PlanManager(workspace)
        plan_manager.save(plan1)

        # Deny first plan
        job = job_manager.deny_job(job, plan1.plan_id, approver="reviewer", reason="Needs adjustment")
        assert job.status == JobStatus.PLANNED  # Should stay in PLANNED
        job_manager.save(job)

        # Generate second plan
        plan2 = planner.generate_plan(job, package, confidence)
        plan_manager.save(plan2)

        # Approve second plan
        job = job_manager.approve_job(job, plan2.plan_id, approver="reviewer", note="Approved on retry")
        assert job.status == JobStatus.APPROVED
        job_manager.save(job)

        # Verify approval log
        approval_log = job_manager.get_approval_log(job)
        all_approvals = approval_log.get_all(plan1.plan_id)

        assert len(all_approvals) == 1
        assert all_approvals[0].decision.value == "denied"

    def test_job_listing_and_discovery(self, workspace):
        """Test listing and discovering jobs."""
        # Create multiple jobs
        session = SessionManager(workspace)
        session.set_mode("code")

        job_manager = JobManager(workspace)
        intent_manager = IntentManager(workspace)

        for i in range(3):
            intent = IntentSynthesizer.synthesize(f"Test job {i}", "code")
            intent_manager.save(intent)

            job = job_manager.create_from_intent(intent, "code")
            job_manager.save(job)

        # List jobs
        jobs = job_manager.list_jobs()

        assert len(jobs) == 3
        # Should be sorted by created_at descending
        assert jobs[0].created_at >= jobs[1].created_at

    def test_package_registry_search(self, workspace):
        """Test searching package registry."""
        registry = PackageRegistry(workspace)

        # Add multiple packages
        for i, (category, verbs) in enumerate([
            ("audio", ["extract", "analyze"]),
            ("audio", ["convert", "encode"]),
            ("video", ["edit", "process"]),
        ]):
            pkg = TaskPackage(
                package_id=f"{category}.pkg{i}",
                version="1.0.0",
                title=f"Package {i}",
                description="Test",
                intent=IntentSpec(category=category, verbs=verbs),
                input_contract=Contract(),
                output_contract=Contract(),
                pipeline=Pipeline(steps=[
                    PipelineStep(
                        step_id="step_1",
                        worker=Worker(worker_id="test", version="1.0.0"),
                        inputs=[],
                        outputs=[],
                    )
                ]),
                approval=ApprovalPolicy(),
                verification=Verification(),
                failure_handling=FailureHandling(),
                resources=ResourceProfile(),
            )
            registry.add_package(pkg)

        # Search by category
        audio_packages = registry.list_packages(category="audio")
        assert len(audio_packages) == 2

        video_packages = registry.list_packages(category="video")
        assert len(video_packages) == 1

        # Search by verb
        extract_packages = registry.search_packages(verbs=["extract"])
        assert len(extract_packages) == 1
        assert extract_packages[0].package_id == "audio.pkg0"

    def test_state_machine_invalid_transitions(self, workspace):
        """Test that invalid state transitions raise errors."""
        job_manager = JobManager(workspace)
        intent_manager = IntentManager(workspace)

        intent = IntentSynthesizer.synthesize("Test", "code")
        intent_manager.save(intent)

        job = job_manager.create_from_intent(intent, "code")
        assert job.status == JobStatus.DRAFT

        # Cannot skip to APPROVED from DRAFT
        with pytest.raises(ValueError):
            job_manager.approve_job(job, "plan-1")

        # Cannot skip to RUNNING from DRAFT
        with pytest.raises(ValueError):
            job_manager.transition_to_running(job)

        # Transition properly
        job = job_manager.transition_to_planned(job)
        assert job.status == JobStatus.PLANNED

        # Cannot complete from PLANNED
        with pytest.raises(ValueError):
            job_manager.complete_job(job)
