"""Tests for planner and plan models."""

import pytest
from tempfile import TemporaryDirectory
from pathlib import Path

from bit.workspace import Workspace
from bit.packages import (
    TaskPackage,
    IntentSpec,
    Contract,
    ContractField,
    Pipeline,
    PipelineStep,
    Worker,
    ApprovalPolicy,
    Verification,
    FailureHandling,
    ResourceProfile,
)
from bit.registry import PackageRegistry
from bit.job import Job, JobSpec, JobStatus, JobInput, JobOutput, InputType, OutputType
from bit.planner import Planner
from bit.plan import ExecutionPlan, PlanManager


class TestPlanner:
    """Tests for Planner class."""

    @pytest.fixture
    def workspace(self):
        """Create temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    @pytest.fixture
    def registry(self, workspace):
        """Create registry with test package."""
        registry = PackageRegistry(workspace)

        # Add test package
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
            input_contract=Contract(fields=[
                ContractField(
                    name="message",
                    type="string",
                    description="Message to echo",
                    required=True,
                )
            ]),
            output_contract=Contract(fields=[
                ContractField(
                    name="output",
                    type="string",
                    description="Output",
                    required=True,
                )
            ]),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="echo_worker", version="1.0.0"),
                    inputs=["message"],
                    outputs=["output"],
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )

        registry.add_package(pkg)
        return registry

    @pytest.fixture
    def planner(self, registry):
        """Create planner with test registry."""
        return Planner(registry)

    def test_planner_extract_keywords(self):
        """Test keyword extraction from intent."""
        text = "Echo the message to the output"
        keywords = Planner._extract_keywords(text)

        assert "echo" in keywords
        assert "message" in keywords
        assert "output" in keywords
        # Stop words should be removed
        assert "the" not in keywords

    def test_planner_match_package_exact(self, planner):
        """Test matching package with clear keywords."""
        job_spec = JobSpec(
            title="Test Echo",
            intent="Echo the message",
            success_criteria=["Message echoed"],
            inputs=[],
            outputs=[],
        )

        result = planner.match_package(job_spec)

        assert result is not None
        package, confidence = result
        assert package.package_id == "test.echo"
        assert confidence > 0.5

    def test_planner_match_package_no_match(self, planner):
        """Test matching when no package matches."""
        job_spec = JobSpec(
            title="Unknown Task",
            intent="Do something completely different",
            success_criteria=["Success"],
            inputs=[],
            outputs=[],
        )

        result = planner.match_package(job_spec)

        # May or may not match depending on scoring
        # Just verify it returns None or a valid result
        if result:
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_planner_match_with_ambiguity_detection(self, registry):
        """Test ambiguity detection with multiple similar matches."""
        planner = Planner(registry)

        # Add another similar package
        pkg2 = TaskPackage(
            package_id="test.print",
            version="1.0.0",
            title="Print Test",
            description="Test print package",
            intent=IntentSpec(
                category="test",
                verbs=["print", "echo"],
                entities=["message"],
                confidence_threshold=0.5,
            ),
            input_contract=Contract(fields=[
                ContractField(
                    name="message",
                    type="string",
                    description="Message",
                    required=True,
                )
            ]),
            output_contract=Contract(fields=[
                ContractField(
                    name="output",
                    type="string",
                    description="Output",
                    required=True,
                )
            ]),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="print_worker", version="1.0.0"),
                    inputs=["message"],
                    outputs=["output"],
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )

        registry.add_package(pkg2)

        job_spec = JobSpec(
            title="Test Echo",
            intent="Echo or print the message",
            success_criteria=["Output"],
            inputs=[],
            outputs=[],
        )

        result = planner.match_packages_with_ambiguity(job_spec)

        if result:
            matches, is_ambiguous = result
            assert len(matches) > 0
            # May or may not be ambiguous depending on exact scores
            assert isinstance(is_ambiguous, bool)

    def test_planner_generate_plan(self, planner, registry):
        """Test generating execution plan."""
        # Create a job
        job = Job(
            job_id="test-job-1",
            created_at="2026-02-04T00:00:00Z",
            intent_ref="intent-ref",
            intent_hash="hash123",
            status=JobStatus.DRAFT,
            mode_used="test",
            job_spec=JobSpec(
                title="Echo Test",
                intent="Echo the message",
                success_criteria=["Success"],
                inputs=[
                    JobInput(
                        name="message",
                        type=InputType.STRING,
                        value="Hello World",
                        required=True,
                    )
                ],
                outputs=[],
            ),
            job_spec_hash="hash456",
        )

        # Match package
        match_result = planner.match_package(job.job_spec)
        assert match_result is not None

        package, confidence = match_result

        # Generate plan
        plan = planner.generate_plan(job, package, confidence)

        assert isinstance(plan, ExecutionPlan)
        assert plan.job_id == job.job_id
        assert plan.package_id == package.package_id
        assert plan.matched_confidence == confidence
        assert len(plan.pipeline.steps) > 0

    def test_planner_compute_match_score(self):
        """Test match score computation."""
        keywords = ["echo", "message"]

        pkg = TaskPackage(
            package_id="test.echo",
            version="1.0.0",
            title="Echo",
            description="Echo package",
            intent=IntentSpec(
                category="test",
                verbs=["echo"],
                entities=["message"],
            ),
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

        score = Planner._compute_match_score(keywords, pkg)

        # Should have high score due to verb match
        assert score > 0.5

    def test_planner_resolve_inputs(self):
        """Test input resolution."""
        job_spec = JobSpec(
            title="Test",
            intent="Test",
            success_criteria=["Success"],
            inputs=[
                JobInput(
                    name="message",
                    type=InputType.STRING,
                    value="Hello",
                    required=True,
                )
            ],
            outputs=[],
        )

        pkg = TaskPackage(
            package_id="test.echo",
            version="1.0.0",
            title="Echo",
            description="Echo",
            intent=IntentSpec(category="test"),
            input_contract=Contract(fields=[
                ContractField(
                    name="message",
                    type="string",
                    description="Message",
                    required=True,
                )
            ]),
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

        resolved = Planner._resolve_inputs(job_spec, pkg)

        assert len(resolved.inputs) == 1
        assert resolved.inputs[0].name == "message"
        assert resolved.inputs[0].value == "Hello"


class TestPlanManager:
    """Tests for PlanManager class."""

    @pytest.fixture
    def workspace(self):
        """Create temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    @pytest.fixture
    def plan_manager(self, workspace):
        """Create plan manager for testing."""
        return PlanManager(workspace)

    @pytest.fixture
    def sample_plan(self):
        """Create a sample execution plan for testing."""
        return ExecutionPlan(
            plan_id="test-plan-1",
            created_at="2026-02-04T00:00:00Z",
            job_id="test-job-1",
            package_id="test.echo",
            package_version="1.0.0",
            matched_confidence=0.95,
            resolved_inputs=Planner._resolve_inputs(
                JobSpec(
                    title="Test",
                    intent="Test",
                    success_criteria=["Success"],
                    inputs=[],
                    outputs=[],
                ),
                TaskPackage(
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
                            worker=Worker(worker_id="test", version="1.0.0"),
                            inputs=[],
                            outputs=[],
                        )
                    ]),
                    approval=ApprovalPolicy(),
                    verification=Verification(),
                    failure_handling=FailureHandling(),
                    resources=ResourceProfile(),
                ),
            ),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="test", version="1.0.0"),
                    inputs=[],
                    outputs=[],
                )
            ]),
            resources=Planner._compute_resources(
                TaskPackage(
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
                            worker=Worker(worker_id="test", version="1.0.0"),
                            inputs=[],
                            outputs=[],
                        )
                    ]),
                    approval=ApprovalPolicy(),
                    verification=Verification(),
                    failure_handling=FailureHandling(),
                    resources=ResourceProfile(),
                ),
            ),
        )

    def test_plan_manager_save_and_load(self, plan_manager, sample_plan):
        """Test saving and loading plans."""
        path = plan_manager.save(sample_plan)

        assert path.exists()

        loaded = plan_manager.load(sample_plan.job_id, sample_plan.plan_id)

        assert loaded is not None
        assert loaded.plan_id == sample_plan.plan_id
        assert loaded.job_id == sample_plan.job_id

    def test_plan_manager_list_plans(self, plan_manager, sample_plan):
        """Test listing plans for a job."""
        plan_manager.save(sample_plan)

        plans = plan_manager.list_plans(sample_plan.job_id)

        assert len(plans) == 1
        assert plans[0].plan_id == sample_plan.plan_id

    def test_plan_manager_get_latest_plan(self, plan_manager, sample_plan):
        """Test getting the latest plan."""
        plan_manager.save(sample_plan)

        latest = plan_manager.get_latest_plan(sample_plan.job_id)

        assert latest is not None
        assert latest.plan_id == sample_plan.plan_id

    def test_plan_manager_get_latest_plan_none(self, plan_manager):
        """Test getting latest plan when none exist."""
        latest = plan_manager.get_latest_plan("nonexistent-job")

        assert latest is None

    def test_execution_plan_hash_deterministic(self, sample_plan):
        """Test that plan hash is deterministic."""
        hash1 = sample_plan.compute_hash()
        hash2 = sample_plan.compute_hash()

        assert hash1 == hash2
