"""Workspace bootstrap and management."""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import hashlib

from pydantic import BaseModel, Field, ConfigDict


class WorkspaceConfig(BaseModel):
    """Workspace metadata and configuration."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "workspace_path": "/path/to/workspace",
            "created_at": "2026-02-04T12:00:00Z",
            "version": "1.0"
        }
    })

    workspace_path: str
    created_at: str
    version: str = "1.0"


class Workspace:
    """Manages workspace structure and validation."""

    SUBDIRS = ["context", "jobs", "artifacts", "logs", "cache", "scratch"]
    CONFIG_FILE = "workspace.json"

    def __init__(self, workspace_path: str):
        self.path = Path(workspace_path)
        self.config_file = self.path / self.CONFIG_FILE

    def initialize(self) -> WorkspaceConfig:
        """Create workspace structure and config.

        Returns:
            WorkspaceConfig: Configuration of initialized workspace

        Raises:
            FileExistsError: If workspace already exists
        """
        # Check if workspace is already initialized in this dir
        if (self.path / self.CONFIG_FILE).exists():
            raise FileExistsError(f"Workspace already exists at {self.path}")

        # Create root directory if needed
        self.path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        for subdir in self.SUBDIRS:
            (self.path / subdir).mkdir(exist_ok=True)

        # Create config
        config = WorkspaceConfig(
            workspace_path=str(self.path.absolute()),
            created_at=datetime.utcnow().isoformat() + "Z"
        )

        # Write config
        with open(self.config_file, "w") as f:
            json.dump(config.model_dump(), f, indent=2)

        return config

    def validate(self) -> bool:
        """Validate workspace structure.

        Returns:
            bool: True if valid, raises exception otherwise

        Raises:
            FileNotFoundError: If workspace doesn't exist
            ValueError: If structure invalid
        """
        if not self.path.exists():
            raise FileNotFoundError(f"Workspace not found at {self.path}")

        # Check config exists
        if not self.config_file.exists():
            raise ValueError(f"Config file missing: {self.config_file}")

        # Check all subdirectories exist
        for subdir in self.SUBDIRS:
            subdir_path = self.path / subdir
            if not subdir_path.is_dir():
                raise ValueError(f"Missing subdirectory: {subdir}")

        # Validate config is valid JSON/Pydantic
        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            WorkspaceConfig(**data)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid config: {e}")

        return True

    def load_config(self) -> WorkspaceConfig:
        """Load workspace config.

        Returns:
            WorkspaceConfig: Current workspace configuration
        """
        with open(self.config_file, "r") as f:
            data = json.load(f)
        return WorkspaceConfig(**data)

    @staticmethod
    def hash_content(content: str) -> str:
        """Generate deterministic hash of content.

        Args:
            content: Text to hash

        Returns:
            str: Hex hash
        """
        return hashlib.sha256(content.encode()).hexdigest()
