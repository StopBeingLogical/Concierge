"""Tests for task package models and registry."""

import json
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

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
    WorkerStatus,
)
from bit.registry import PackageRegistry
from bit.workspace import Workspace


class TestTaskPackage:
    """Tests for TaskPackage model."""

    def test_create_minimal_package(self):
        """Test creating a minimal task package."""
        pkg = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Basic Test",
            description="Basic test package",
            intent=IntentSpec(category="test"),
            input_contract=Contract(),
            output_contract=Contract(),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="test_worker", version="1.0.0"),
                    inputs=[],
                    outputs=[],
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )

        assert pkg.package_id == "test.basic"
        assert pkg.version == "1.0.0"
        assert pkg.title == "Basic Test"
        assert len(pkg.pipeline.steps) == 1

    def test_package_with_full_spec(self):
        """Test creating a package with full specification."""
        pkg = TaskPackage(
            package_id="audio.extract",
            version="1.0.0",
            title="Extract Audio Stems",
            description="Extract stems from audio files",
            intent=IntentSpec(
                category="audio",
                verbs=["extract", "separate"],
                entities=["stems"],
                confidence_threshold=0.8,
                match_rules=["must contain 'extract'"],
            ),
            input_contract=Contract(fields=[
                ContractField(
                    name="audio_file",
                    type="file",
                    description="Input audio file",
                    required=True,
                )
            ]),
            output_contract=Contract(fields=[
                ContractField(
                    name="stems",
                    type="folder",
                    description="Extracted stems",
                    required=True,
                )
            ]),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(
                        worker_id="audio_processor",
                        version="1.0.0",
                        status=WorkerStatus.AVAILABLE,
                    ),
                    inputs=["audio_file"],
                    outputs=["stems"],
                    params={"format": "wav"},
                )
            ]),
            approval=ApprovalPolicy(required=True, conditions=["large_compute"]),
            verification=Verification(required=True),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(cpu_cores=4, memory_mb=2048),
            metadata={"created_at": "2026-02-04T00:00:00Z"},
        )

        assert pkg.package_id == "audio.extract"
        assert pkg.intent.category == "audio"
        assert len(pkg.intent.verbs) == 2
        assert pkg.approval.required is True
        assert pkg.resources.cpu_cores == 4

    def test_package_to_canonical_dict(self):
        """Test canonical dict excludes metadata."""
        pkg = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Test",
            description="Test package",
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
            metadata={"created_at": "2026-02-04T00:00:00Z"},
        )

        canonical = pkg.to_canonical_dict()

        # Should not contain metadata
        assert "metadata" not in canonical
        # Should contain essential fields
        assert canonical["package_id"] == "test.basic"
        assert canonical["version"] == "1.0.0"

    def test_package_hash_deterministic(self):
        """Test that hash is deterministic for same content."""
        pkg1 = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Test",
            description="Test package",
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
        )

        pkg2 = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Test",
            description="Test package",
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
        )

        assert pkg1.compute_hash() == pkg2.compute_hash()

    def test_package_hash_changes_with_content(self):
        """Test that hash changes when content changes."""
        pkg1 = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Test",
            description="Test package",
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
        )

        pkg2 = TaskPackage(
            package_id="test.basic",
            version="1.0.1",  # Different version
            title="Test",
            description="Test package",
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
        )

        assert pkg1.compute_hash() != pkg2.compute_hash()


class TestPackageRegistry:
    """Tests for PackageRegistry."""

    @pytest.fixture
    def workspace(self):
        """Create temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    @pytest.fixture
    def registry(self, workspace):
        """Create registry for testing."""
        return PackageRegistry(workspace)

    def test_registry_init(self, workspace):
        """Test registry initialization creates directory."""
        registry = PackageRegistry(workspace)
        assert (Path(workspace) / "packages").exists()

    def test_add_package(self, registry):
        """Test adding a package to registry."""
        pkg = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Test",
            description="Test package",
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
        )

        path = registry.add_package(pkg)

        assert path.exists()
        assert "test" in str(path)
        assert "basic" in str(path)
        assert "v1.0.0" in str(path)

    def test_add_package_duplicate_raises_error(self, registry):
        """Test adding duplicate package raises error."""
        pkg = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Test",
            description="Test package",
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
        )

        registry.add_package(pkg)

        with pytest.raises(FileExistsError):
            registry.add_package(pkg)

    def test_get_package(self, registry):
        """Test retrieving a package."""
        pkg = TaskPackage(
            package_id="test.basic",
            version="1.0.0",
            title="Test",
            description="Test package",
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
        )

        registry.add_package(pkg)
        retrieved = registry.get_package("test.basic", "1.0.0")

        assert retrieved is not None
        assert retrieved.package_id == "test.basic"
        assert retrieved.version == "1.0.0"

    def test_get_package_not_found(self, registry):
        """Test retrieving non-existent package returns None."""
        result = registry.get_package("nonexistent.pkg", "1.0.0")
        assert result is None

    def test_list_packages(self, registry):
        """Test listing packages."""
        pkg1 = TaskPackage(
            package_id="test.pkg1",
            version="1.0.0",
            title="Package 1",
            description="Test package 1",
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
        )

        pkg2 = TaskPackage(
            package_id="audio.pkg2",
            version="1.0.0",
            title="Package 2",
            description="Test package 2",
            intent=IntentSpec(category="audio"),
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

        registry.add_package(pkg1)
        registry.add_package(pkg2)

        all_packages = registry.list_packages()
        assert len(all_packages) == 2

        test_packages = registry.list_packages(category="test")
        assert len(test_packages) == 1
        assert test_packages[0].package_id == "test.pkg1"

    def test_search_packages_by_verbs(self, registry):
        """Test searching packages by verbs."""
        pkg = TaskPackage(
            package_id="test.search",
            version="1.0.0",
            title="Search Test",
            description="Test package",
            intent=IntentSpec(
                category="test",
                verbs=["copy", "move"],
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

        registry.add_package(pkg)

        results = registry.search_packages(verbs=["copy"])
        assert len(results) == 1

        results = registry.search_packages(verbs=["delete"])
        assert len(results) == 0

    def test_search_packages_by_entities(self, registry):
        """Test searching packages by entities."""
        pkg = TaskPackage(
            package_id="test.search",
            version="1.0.0",
            title="Search Test",
            description="Test package",
            intent=IntentSpec(
                category="test",
                entities=["file", "folder"],
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

        registry.add_package(pkg)

        results = registry.search_packages(entities=["file"])
        assert len(results) == 1

        results = registry.search_packages(entities=["image"])
        assert len(results) == 0

    def test_validate_package_valid(self, registry):
        """Test validating a valid package."""
        pkg = TaskPackage(
            package_id="test.valid",
            version="1.0.0",
            title="Valid Package",
            description="Valid test package",
            intent=IntentSpec(category="test"),
            input_contract=Contract(fields=[
                ContractField(
                    name="input_data",
                    type="string",
                    description="Input",
                    required=True,
                )
            ]),
            output_contract=Contract(fields=[
                ContractField(
                    name="output_data",
                    type="string",
                    description="Output",
                    required=True,
                )
            ]),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="test", version="1.0.0"),
                    inputs=["input_data"],
                    outputs=["output_data"],
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )

        errors = registry.validate_package(pkg)
        assert len(errors) == 0

    def test_validate_package_invalid_package_id(self, registry):
        """Test validation fails for invalid package_id."""
        pkg = TaskPackage(
            package_id="invalid_no_dot",
            version="1.0.0",
            title="Invalid",
            description="Invalid package",
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
        )

        errors = registry.validate_package(pkg)
        assert len(errors) > 0
        assert "package_id" in errors[0].lower()

    def test_validate_package_no_pipeline_steps(self, registry):
        """Test validation fails with no pipeline steps."""
        pkg = TaskPackage(
            package_id="test.invalid",
            version="1.0.0",
            title="Invalid",
            description="Invalid package",
            intent=IntentSpec(category="test"),
            input_contract=Contract(),
            output_contract=Contract(),
            pipeline=Pipeline(steps=[]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )

        errors = registry.validate_package(pkg)
        assert len(errors) > 0

    def test_validate_package_undefined_input(self, registry):
        """Test validation fails with undefined step input."""
        pkg = TaskPackage(
            package_id="test.invalid",
            version="1.0.0",
            title="Invalid",
            description="Invalid package",
            intent=IntentSpec(category="test"),
            input_contract=Contract(),
            output_contract=Contract(),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="test", version="1.0.0"),
                    inputs=["undefined_input"],
                    outputs=["output"],
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )

        errors = registry.validate_package(pkg)
        assert len(errors) > 0
        assert "undefined" in errors[0].lower()

    def test_validate_package_unproduce_output(self, registry):
        """Test validation fails when output is not produced."""
        pkg = TaskPackage(
            package_id="test.invalid",
            version="1.0.0",
            title="Invalid",
            description="Invalid package",
            intent=IntentSpec(category="test"),
            input_contract=Contract(),
            output_contract=Contract(fields=[
                ContractField(
                    name="output_data",
                    type="string",
                    description="Output",
                    required=True,
                )
            ]),
            pipeline=Pipeline(steps=[
                PipelineStep(
                    step_id="step_1",
                    worker=Worker(worker_id="test", version="1.0.0"),
                    inputs=[],
                    outputs=["other_output"],
                )
            ]),
            approval=ApprovalPolicy(),
            verification=Verification(),
            failure_handling=FailureHandling(),
            resources=ResourceProfile(),
        )

        errors = registry.validate_package(pkg)
        assert len(errors) > 0
        assert "output_data" in errors[0].lower()

    def test_package_path_format(self, registry):
        """Test that package path follows correct format."""
        pkg = TaskPackage(
            package_id="audio.extract",
            version="2.1.3",
            title="Test",
            description="Test",
            intent=IntentSpec(category="audio"),
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

        path = registry.add_package(pkg)

        # Verify path structure
        assert "audio" in str(path)
        assert "extract" in str(path)
        assert "v2.1.3" in str(path)
        assert "package.yaml" in str(path)
