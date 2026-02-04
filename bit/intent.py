"""Intent synthesis and management."""

import json
import re
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from bit.workspace import Workspace


class Intent(BaseModel):
    """Intent artifact schema."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "intent_id": "550e8400-e29b-41d4-a716-446655440000",
            "mode": "code",
            "distilled_intent": "Create user authentication system",
            "success_criteria": "Users can log in with email and password",
            "constraints": ["Must use OAuth2", "Cannot store plain passwords"],
            "created_at": "2026-02-04T12:00:00Z",
            "intent_hash": "abc123def456..."
        }
    })

    intent_id: str = Field(description="UUID v5 deterministic ID based on content")
    mode: str = Field(description="Mode this intent was created in")
    distilled_intent: str = Field(description="Concise summary of intent (first sentence or truncated)")
    success_criteria: str = Field(description="How to measure success")
    constraints: list[str] = Field(description="Limiting factors or requirements")
    created_at: str = Field(description="ISO 8601 timestamp")
    intent_hash: str = Field(description="SHA256 hash of canonical intent content")

    def to_canonical_dict(self) -> dict:
        """Return dict for hashing (excludes metadata like id, hash, timestamp).

        Returns:
            dict: Canonical representation with sorted keys for deterministic hashing
        """
        return {
            "mode": self.mode,
            "distilled_intent": self.distilled_intent,
            "success_criteria": self.success_criteria,
            "constraints": sorted(self.constraints),
        }


class IntentSynthesizer:
    """Rule-based synthesis of intents from text."""

    # Deterministic namespace for UUID v5
    INTENT_NAMESPACE = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")

    # Pattern for identifying sentences
    SENTENCE_PATTERN = re.compile(r"[^.!?]*[.!?]+")

    # Patterns for extracting success criteria
    SUCCESS_PATTERNS = [
        r"(?:should|must|needs to|will)\s+([^.!?]+[.!?])",
        r"success (?:is|criteria|means)\s*[:-]?\s*([^.!?]+[.!?])",
        r"(?:to achieve|goal is)\s+([^.!?]+[.!?])",
    ]

    # Patterns for extracting constraints
    CONSTRAINT_PATTERNS = [
        r"must (?:use|implement|have)\s+([^,.]+)",
        r"cannot\s+([^,.]+)",
        r"within\s+([^,.]+)",
        r"only\s+([^,.]+)",
        r"(?:no|never)\s+([^,.]+)",
    ]

    @staticmethod
    def synthesize(text: str, mode: str) -> Intent:
        """Synthesize intent from user text.

        Args:
            text: User-provided intent description
            mode: Current mode name

        Returns:
            Intent: Synthesized intent artifact
        """
        # Extract components
        distilled = IntentSynthesizer._extract_distilled_intent(text)
        success = IntentSynthesizer._extract_success_criteria(text)
        constraints = IntentSynthesizer._extract_constraints(text)

        # Create canonical representation for hashing
        canonical = {
            "mode": mode,
            "distilled_intent": distilled,
            "success_criteria": success,
            "constraints": sorted(constraints),
        }

        # Generate hash using canonical JSON
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
        intent_hash = Workspace.hash_content(canonical_json)

        # Generate deterministic UUID from hash
        intent_id = str(uuid.uuid5(
            IntentSynthesizer.INTENT_NAMESPACE,
            intent_hash
        ))

        # Create intent
        intent = Intent(
            intent_id=intent_id,
            mode=mode,
            distilled_intent=distilled,
            success_criteria=success,
            constraints=constraints,
            created_at=datetime.now(UTC).isoformat().replace('+00:00', 'Z'),
            intent_hash=intent_hash,
        )

        return intent

    @staticmethod
    def _extract_distilled_intent(text: str) -> str:
        """Extract distilled intent (first sentence or truncate).

        Args:
            text: User text

        Returns:
            str: Distilled intent (max 100 chars)
        """
        # Try to get first sentence
        text = text.strip()
        match = IntentSynthesizer.SENTENCE_PATTERN.search(text)

        if match:
            first_sentence = match.group().strip()
        else:
            # No sentence found, use beginning of text
            first_sentence = text

        # Truncate to 100 chars if needed
        if len(first_sentence) > 100:
            first_sentence = first_sentence[:100].rstrip() + "..."

        return first_sentence

    @staticmethod
    def _extract_success_criteria(text: str) -> str:
        """Extract success criteria from text using pattern matching.

        Args:
            text: User text

        Returns:
            str: Extracted success criteria or placeholder
        """
        for pattern in IntentSynthesizer.SUCCESS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # Default: generate from distilled intent
        distilled = IntentSynthesizer._extract_distilled_intent(text)
        return f"Successfully complete: {distilled}"

    @staticmethod
    def _extract_constraints(text: str) -> list[str]:
        """Extract constraints from text using pattern matching.

        Args:
            text: User text

        Returns:
            list[str]: Extracted constraints
        """
        constraints = set()

        for pattern in IntentSynthesizer.CONSTRAINT_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                constraint = match.group(1).strip()
                # Clean up constraint
                constraint = re.sub(r"[,;.!?]$", "", constraint)
                if constraint and len(constraint) > 2:  # Skip very short matches
                    constraints.add(constraint)

        return sorted(list(constraints))


class IntentManager:
    """Manages intent storage and retrieval."""

    ARTIFACTS_SUBDIR = "artifacts"
    INTENT_PREFIX = "intent_"

    def __init__(self, workspace_path: str):
        """Initialize intent manager.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = Path(workspace_path)
        self.artifacts_dir = self.workspace_path / self.ARTIFACTS_SUBDIR

    def _ensure_artifacts_dir(self) -> None:
        """Ensure artifacts directory exists."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def _get_intent_path(self, intent_hash: str) -> Path:
        """Get path for intent file (use first 16 chars of hash).

        Args:
            intent_hash: Full SHA256 hash

        Returns:
            Path: Path to intent file
        """
        hash_prefix = intent_hash[:16]
        return self.artifacts_dir / f"{self.INTENT_PREFIX}{hash_prefix}.json"

    def save(self, intent: Intent) -> Path:
        """Save intent to artifacts directory.

        Args:
            intent: Intent to save

        Returns:
            Path: Path to saved file
        """
        self._ensure_artifacts_dir()

        intent_path = self._get_intent_path(intent.intent_hash)

        with open(intent_path, "w") as f:
            json.dump(intent.model_dump(), f, indent=2)

        return intent_path

    def load(self, intent_hash: str) -> Optional[Intent]:
        """Load intent by hash (full or partial).

        Args:
            intent_hash: Full or partial hash (at least 16 chars for partial)

        Returns:
            Intent: Loaded intent or None if not found
        """
        # Try exact match first with 16-char prefix
        if len(intent_hash) >= 16:
            intent_path = self._get_intent_path(intent_hash)
            if intent_path.exists():
                try:
                    with open(intent_path, "r") as f:
                        data = json.load(f)
                    return Intent(**data)
                except (json.JSONDecodeError, ValueError):
                    return None

        # Try searching by partial hash
        search_prefix = intent_hash[:min(16, len(intent_hash))]
        pattern = f"{self.INTENT_PREFIX}{search_prefix}*.json"

        matching_files = list(self.artifacts_dir.glob(pattern))
        if matching_files:
            # Return first match
            try:
                with open(matching_files[0], "r") as f:
                    data = json.load(f)
                return Intent(**data)
            except (json.JSONDecodeError, ValueError):
                return None

        return None

    def list_intents(self) -> list[Intent]:
        """List all intents in workspace, sorted by created_at descending.

        Returns:
            list[Intent]: All intents, newest first
        """
        if not self.artifacts_dir.exists():
            return []

        intents = []
        for intent_file in self.artifacts_dir.glob(f"{self.INTENT_PREFIX}*.json"):
            try:
                with open(intent_file, "r") as f:
                    data = json.load(f)
                intent = Intent(**data)
                intents.append(intent)
            except (json.JSONDecodeError, ValueError):
                # Skip corrupted files
                pass

        # Sort by created_at descending (newest first)
        intents.sort(key=lambda i: i.created_at, reverse=True)
        return intents

    def verify_hash(self, intent: Intent) -> bool:
        """Verify intent hash is correct.

        Args:
            intent: Intent to verify

        Returns:
            bool: True if hash is valid
        """
        canonical_json = json.dumps(intent.to_canonical_dict(), sort_keys=True, separators=(",", ":"))
        computed_hash = Workspace.hash_content(canonical_json)
        return computed_hash == intent.intent_hash
