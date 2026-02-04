"""Planner for matching job specs to task packages and generating execution plans."""

import re
import uuid
from datetime import datetime
from typing import Optional, Tuple

from bit.job import JobSpec, Job
from bit.packages import TaskPackage
from bit.registry import PackageRegistry
from bit.plan import ExecutionPlan, ResolvedInputs, ResolvedInput, ResourceRequirements


class Planner:
    """Matches job specs to task packages and generates execution plans."""

    def __init__(self, registry: PackageRegistry):
        """Initialize planner.

        Args:
            registry: PackageRegistry instance for package lookup
        """
        self.registry = registry

    def match_package(
        self,
        job_spec: JobSpec,
        category_hint: Optional[str] = None,
    ) -> Optional[Tuple[TaskPackage, float]]:
        """Find best-matching package for job spec.

        Args:
            job_spec: Job specification
            category_hint: Optional category hint (e.g., from intent)

        Returns:
            Tuple[TaskPackage, float]: Matched package and confidence score, or None if no match
        """
        # Extract keywords from intent
        keywords = self._extract_keywords(job_spec.intent)

        # Search for candidate packages
        candidates = self.registry.list_packages(category=category_hint)

        if not candidates:
            return None

        # Score each candidate
        best_package = None
        best_score = 0.0

        for package in candidates:
            score = self._compute_match_score(keywords, package)

            # Check confidence threshold
            if score >= package.intent.confidence_threshold:
                if score > best_score:
                    best_score = score
                    best_package = package

        return (best_package, best_score) if best_package else None

    def match_packages_with_ambiguity(
        self,
        job_spec: JobSpec,
        category_hint: Optional[str] = None,
    ) -> Optional[Tuple[list[Tuple[TaskPackage, float]], bool]]:
        """Find all matching packages with ambiguity detection.

        Returns:
            Tuple with list of (package, score) and ambiguity flag:
            - If unambiguous: ([(best_package, best_score)], False)
            - If ambiguous: ([(pkg1, score1), (pkg2, score2), ...], True)
            - If no match: None
        """
        # Extract keywords from intent
        keywords = self._extract_keywords(job_spec.intent)

        # Search for candidate packages
        candidates = self.registry.list_packages(category=category_hint)

        if not candidates:
            return None

        # Score all candidates
        scored = []
        for package in candidates:
            score = self._compute_match_score(keywords, package)

            # Check confidence threshold
            if score >= package.intent.confidence_threshold:
                scored.append((package, score))

        if not scored:
            return None

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Check for ambiguity (multiple matches with similar scores)
        is_ambiguous = len(scored) > 1 and (scored[0][1] - scored[1][1]) < 0.1

        return (scored, is_ambiguous)

    def generate_plan(
        self,
        job: Job,
        package: TaskPackage,
        matched_confidence: float,
    ) -> ExecutionPlan:
        """Generate execution plan from job spec and matched package.

        Args:
            job: Job object
            package: Matched TaskPackage
            matched_confidence: Confidence score of match

        Returns:
            ExecutionPlan: Execution plan ready for approval/execution
        """
        # Generate plan ID
        plan_id = f"plan-{uuid.uuid4()}"

        # Resolve inputs
        resolved_inputs = self._resolve_inputs(job.job_spec, package)

        # Compute resource requirements
        resources = self._compute_resources(package)

        # Create execution plan
        plan = ExecutionPlan(
            plan_id=plan_id,
            created_at=datetime.utcnow().isoformat() + "Z",
            job_id=job.job_id,
            package_id=package.package_id,
            package_version=package.version,
            matched_confidence=matched_confidence,
            resolved_inputs=resolved_inputs,
            pipeline=package.pipeline,
            resources=resources,
        )

        return plan

    @staticmethod
    def _extract_keywords(intent_text: str) -> list[str]:
        """Extract keywords from intent text.

        Args:
            intent_text: Intent description

        Returns:
            list[str]: List of keywords (normalized)
        """
        # Simple keyword extraction: lowercase, remove punctuation, split on whitespace
        text = intent_text.lower()
        # Remove common words
        stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "from", "is", "are", "be"}

        words = re.findall(r"\b\w+\b", text)
        keywords = [w for w in words if w not in stop_words and len(w) > 2]

        return keywords

    @staticmethod
    def _compute_match_score(keywords: list[str], package: TaskPackage) -> float:
        """Compute match score between keywords and package.

        Args:
            keywords: Extracted keywords
            package: Package to score

        Returns:
            float: Match score (0.0-1.0)
        """
        if not keywords:
            return 0.0

        # Prepare package data for matching
        package_words = set()
        package_words.update(package.intent.verbs)
        package_words.update(package.intent.entities)
        package_words.add(package.intent.category)

        # Convert to lowercase for comparison
        package_words = {w.lower() for w in package_words}

        # Count keyword matches
        matches = sum(1 for kw in keywords if kw in package_words)

        # Compute score (matches / total keywords)
        base_score = matches / len(keywords) if keywords else 0.0

        # Bonus for verb matches
        verb_matches = sum(1 for v in package.intent.verbs if v.lower() in keywords)
        verb_bonus = verb_matches * 0.2  # Each verb match adds 0.2

        # Combine scores (base can go 0-1, bonus can push up to 0.4+)
        score = min(1.0, base_score + verb_bonus)

        return score

    @staticmethod
    def _resolve_inputs(job_spec: JobSpec, package: TaskPackage) -> ResolvedInputs:
        """Resolve inputs from job spec.

        Args:
            job_spec: Job specification
            package: Package with input contract

        Returns:
            ResolvedInputs: Resolved input values
        """
        resolved = []

        # Map job inputs to package inputs
        job_inputs = {inp.name: inp.value for inp in job_spec.inputs}

        for field in package.input_contract.fields:
            # Look for matching input in job spec
            if field.name in job_inputs:
                resolved.append(ResolvedInput(
                    name=field.name,
                    type=field.type,
                    value=job_inputs[field.name],
                ))
            elif not field.required:
                # Optional input not provided - skip
                pass
            else:
                # Required input not provided - use placeholder
                resolved.append(ResolvedInput(
                    name=field.name,
                    type=field.type,
                    value=f"<unresolved:{field.name}>",
                ))

        return ResolvedInputs(inputs=resolved)

    @staticmethod
    def _compute_resources(package: TaskPackage) -> ResourceRequirements:
        """Compute aggregated resource requirements from package.

        Args:
            package: Package with resource specs

        Returns:
            ResourceRequirements: Aggregated requirements
        """
        # For now, just use package resource profile
        # In future, could sum across all pipeline steps
        return ResourceRequirements(
            total_cpu_cores=package.resources.cpu_cores,
            gpu_required=package.resources.gpu_required,
            total_memory_mb=package.resources.memory_mb,
            total_disk_mb=package.resources.disk_mb,
        )
