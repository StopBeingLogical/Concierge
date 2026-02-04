"""Task package registry and management."""

from pathlib import Path
from typing import Optional
import yaml

from bit.packages import TaskPackage


class PackageRegistry:
    """Filesystem-based task package registry."""

    REGISTRY_SUBDIR = "packages"

    def __init__(self, workspace_path: str):
        """Initialize package registry.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = Path(workspace_path)
        self.registry_dir = self.workspace_path / self.REGISTRY_SUBDIR
        self._ensure_registry_dir()

    def _ensure_registry_dir(self) -> None:
        """Ensure registry directory exists."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def _get_package_path(self, package_id: str, version: str) -> Path:
        """Get path to package.yaml file.

        Package structure:
        packages/<category>/<package_name>/v<version>/package.yaml

        Example:
        packages/audio/stem_extraction/v1.0.0/package.yaml

        Args:
            package_id: Package ID (e.g., audio.stem_extraction)
            version: Version string (e.g., 1.0.0)

        Returns:
            Path: Path to package.yaml
        """
        # Split package_id into category and name
        parts = package_id.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid package_id format: {package_id}. Expected: <category>.<name>")

        category, package_name = parts
        return self.registry_dir / category / package_name / f"v{version}" / "package.yaml"

    def add_package(self, package: TaskPackage) -> Path:
        """Add package to registry.

        Args:
            package: TaskPackage to add

        Returns:
            Path: Path to saved package.yaml

        Raises:
            FileExistsError: If package already exists
        """
        package_path = self._get_package_path(package.package_id, package.version)

        if package_path.exists():
            raise FileExistsError(f"Package already exists: {package.package_id} v{package.version}")

        # Create directory structure
        package_path.parent.mkdir(parents=True, exist_ok=True)

        # Save package
        with open(package_path, "w") as f:
            package_dict = package.model_dump(mode="json")
            yaml.dump(package_dict, f, default_flow_style=False, sort_keys=False, indent=2)

        return package_path

    def get_package(self, package_id: str, version: str) -> Optional[TaskPackage]:
        """Retrieve package by ID and version.

        Args:
            package_id: Package ID (e.g., audio.stem_extraction)
            version: Version string (e.g., 1.0.0)

        Returns:
            TaskPackage: Loaded package or None if not found
        """
        package_path = self._get_package_path(package_id, version)

        if not package_path.exists():
            return None

        try:
            with open(package_path, "r") as f:
                data = yaml.safe_load(f)
            return TaskPackage(**data)
        except (yaml.YAMLError, ValueError):
            return None

    def list_packages(self, category: Optional[str] = None) -> list[TaskPackage]:
        """List all packages, optionally filtered by category.

        Args:
            category: Optional category filter (e.g., "audio")

        Returns:
            list[TaskPackage]: All matching packages
        """
        packages = []

        if not self.registry_dir.exists():
            return []

        # Find all package.yaml files
        for package_file in self.registry_dir.glob("*/*/v*/package.yaml"):
            try:
                with open(package_file, "r") as f:
                    data = yaml.safe_load(f)
                package = TaskPackage(**data)

                # Filter by category if specified
                if category and package.intent.category != category:
                    continue

                packages.append(package)
            except (yaml.YAMLError, ValueError):
                # Skip corrupted files
                pass

        return packages

    def search_packages(
        self,
        category: Optional[str] = None,
        verbs: Optional[list[str]] = None,
        entities: Optional[list[str]] = None,
    ) -> list[TaskPackage]:
        """Search packages by multiple criteria.

        Args:
            category: Filter by intent category
            verbs: Filter by intent verbs (any match)
            entities: Filter by intent entities (any match)

        Returns:
            list[TaskPackage]: Matching packages
        """
        candidates = self.list_packages(category)
        results = []

        for package in candidates:
            # Check category
            if category and package.intent.category != category:
                continue

            # Check verbs
            if verbs:
                has_verb = any(verb in package.intent.verbs for verb in verbs)
                if not has_verb:
                    continue

            # Check entities
            if entities:
                has_entity = any(entity in package.intent.entities for entity in entities)
                if not has_entity:
                    continue

            results.append(package)

        return results

    def validate_package(self, package: TaskPackage) -> list[str]:
        """Validate package structure and integrity.

        Args:
            package: Package to validate

        Returns:
            list[str]: List of validation errors (empty if valid)
        """
        errors = []

        # Check package_id format
        if "." not in package.package_id:
            errors.append("package_id must contain category.name format (e.g., audio.processor)")

        # Check version format (basic semver)
        if not self._is_valid_semver(package.version):
            errors.append(f"version must be semver format (e.g., 1.0.0): {package.version}")

        # Check pipeline has steps
        if not package.pipeline.steps:
            errors.append("pipeline must contain at least one step")

        # Check step integrity
        for step in package.pipeline.steps:
            if not step.step_id:
                errors.append("Pipeline step must have step_id")
            if not step.worker.worker_id:
                errors.append("Pipeline step worker must have worker_id")

        # Check contracts
        input_names = {field.name for field in package.input_contract.fields}
        output_names = {field.name for field in package.output_contract.fields}

        # Check step inputs reference contract or other step outputs
        available_names = input_names.copy()
        for step in package.pipeline.steps:
            for input_name in step.inputs:
                if input_name not in available_names:
                    errors.append(f"Step {step.step_id} references undefined input: {input_name}")

            # Add outputs to available names for next steps
            available_names.update(step.outputs)

        # Check final outputs are produced
        for output_name in output_names:
            if output_name not in available_names:
                errors.append(f"Output {output_name} not produced by any pipeline step")

        return errors

    @staticmethod
    def _is_valid_semver(version: str) -> bool:
        """Check if version string is valid semver.

        Args:
            version: Version string

        Returns:
            bool: True if valid semver format
        """
        parts = version.split(".")
        if len(parts) < 3:
            return False

        for part in parts[:3]:
            try:
                int(part)
            except ValueError:
                return False

        return True
