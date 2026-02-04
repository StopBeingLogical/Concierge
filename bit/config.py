"""Configuration management for Concierge."""

import json
from pathlib import Path
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


class WorkerConfig(BaseModel):
    """Configuration for a worker."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "worker_id": "audio_normalizer",
            "enabled": True,
            "timeout_seconds": 300,
            "retry_count": 3,
            "resource_limits": {"memory_mb": 2048}
        }
    })

    worker_id: str = Field(description="Worker ID")
    enabled: bool = Field(default=True, description="Whether worker is enabled")
    timeout_seconds: int = Field(default=300, description="Worker timeout")
    retry_count: int = Field(default=3, description="Max retries on failure")
    resource_limits: Dict[str, Any] = Field(default={}, description="Resource limits")


class PlannerConfig(BaseModel):
    """Configuration for the planner."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "confidence_threshold": 0.7,
            "max_candidates": 5,
            "enable_ambiguity_detection": True
        }
    })

    confidence_threshold: float = Field(default=0.7, description="Minimum match confidence")
    max_candidates: int = Field(default=5, description="Max candidate packages to consider")
    enable_ambiguity_detection: bool = Field(default=True, description="Enable ambiguity detection")


class RouterConfig(BaseModel):
    """Configuration for the router."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "max_parallel_steps": 1,
            "enable_event_logging": True,
            "event_log_format": "jsonl"
        }
    })

    max_parallel_steps: int = Field(default=1, description="Max parallel execution steps")
    enable_event_logging: bool = Field(default=True, description="Enable event logging")
    event_log_format: str = Field(default="jsonl", description="Event log format")


class ApprovalConfig(BaseModel):
    """Configuration for approval gates."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "require_approval_by_default": False,
            "auto_approve_threshold": 0.95,
            "approval_timeout_hours": 24
        }
    })

    require_approval_by_default: bool = Field(default=False, description="Require approval for all jobs")
    auto_approve_threshold: float = Field(default=0.95, description="Auto-approve above confidence")
    approval_timeout_hours: int = Field(default=24, description="Approval request timeout")


class CacheConfig(BaseModel):
    """Configuration for caching."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "enable_caching": True,
            "cache_ttl_seconds": 3600,
            "max_cache_size_mb": 1000
        }
    })

    enable_caching: bool = Field(default=True, description="Enable caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache time-to-live")
    max_cache_size_mb: int = Field(default=1000, description="Max cache size")


class ConciergeConfig(BaseModel):
    """Complete Concierge configuration."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "version": "1.0.0",
            "workspace_path": "/path/to/workspace",
            "planner": {},
            "router": {},
            "approval": {},
            "cache": {},
            "workers": {}
        }
    })

    version: str = Field(default="1.0.0", description="Config version")
    workspace_path: Optional[str] = Field(default=None, description="Workspace root path")
    planner: PlannerConfig = Field(default_factory=PlannerConfig, description="Planner configuration")
    router: RouterConfig = Field(default_factory=RouterConfig, description="Router configuration")
    approval: ApprovalConfig = Field(default_factory=ApprovalConfig, description="Approval configuration")
    cache: CacheConfig = Field(default_factory=CacheConfig, description="Cache configuration")
    workers: Dict[str, WorkerConfig] = Field(default={}, description="Worker configurations")


class ConfigManager:
    """Manages Concierge configuration."""

    CONFIG_FILE = "concierge.json"

    def __init__(self, workspace_path: str):
        """Initialize config manager.

        Args:
            workspace_path: Path to workspace root
        """
        self.workspace_path = Path(workspace_path)
        self.config_file = self.workspace_path / self.CONFIG_FILE

    def load(self) -> ConciergeConfig:
        """Load configuration from file.

        Returns:
            ConciergeConfig: Loaded configuration or defaults if not found
        """
        if not self.config_file.exists():
            return ConciergeConfig(workspace_path=str(self.workspace_path))

        try:
            with open(self.config_file, "r") as f:
                data = json.load(f)
            return ConciergeConfig(**data)
        except (json.JSONDecodeError, ValueError):
            return ConciergeConfig(workspace_path=str(self.workspace_path))

    def save(self, config: ConciergeConfig) -> Path:
        """Save configuration to file.

        Args:
            config: Configuration to save

        Returns:
            Path: Path to saved file
        """
        config_dict = config.model_dump(mode="json")

        with open(self.config_file, "w") as f:
            json.dump(config_dict, f, indent=2)

        return self.config_file

    def get_planner_config(self) -> PlannerConfig:
        """Get planner configuration.

        Returns:
            PlannerConfig: Planner settings
        """
        config = self.load()
        return config.planner

    def get_router_config(self) -> RouterConfig:
        """Get router configuration.

        Returns:
            RouterConfig: Router settings
        """
        config = self.load()
        return config.router

    def get_approval_config(self) -> ApprovalConfig:
        """Get approval configuration.

        Returns:
            ApprovalConfig: Approval settings
        """
        config = self.load()
        return config.approval

    def get_worker_config(self, worker_id: str) -> Optional[WorkerConfig]:
        """Get configuration for specific worker.

        Args:
            worker_id: Worker ID

        Returns:
            WorkerConfig: Worker configuration or None
        """
        config = self.load()
        return config.workers.get(worker_id)

    def update_planner_config(self, updates: Dict[str, Any]) -> None:
        """Update planner configuration.

        Args:
            updates: Configuration updates
        """
        config = self.load()

        # Update planner config
        planner_dict = config.planner.model_dump()
        planner_dict.update(updates)
        config.planner = PlannerConfig(**planner_dict)

        self.save(config)

    def update_worker_config(self, worker_id: str, updates: Dict[str, Any]) -> None:
        """Update worker configuration.

        Args:
            worker_id: Worker ID
            updates: Configuration updates
        """
        config = self.load()

        if worker_id in config.workers:
            worker_dict = config.workers[worker_id].model_dump()
            worker_dict.update(updates)
            config.workers[worker_id] = WorkerConfig(**worker_dict)
        else:
            config.workers[worker_id] = WorkerConfig(worker_id=worker_id, **updates)

        self.save(config)

    def enable_worker(self, worker_id: str) -> None:
        """Enable a worker.

        Args:
            worker_id: Worker ID
        """
        self.update_worker_config(worker_id, {"enabled": True})

    def disable_worker(self, worker_id: str) -> None:
        """Disable a worker.

        Args:
            worker_id: Worker ID
        """
        self.update_worker_config(worker_id, {"enabled": False})

    def is_worker_enabled(self, worker_id: str) -> bool:
        """Check if worker is enabled.

        Args:
            worker_id: Worker ID

        Returns:
            bool: True if enabled
        """
        worker_config = self.get_worker_config(worker_id)
        return worker_config is None or worker_config.enabled

    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current configuration.

        Returns:
            dict: Configuration summary
        """
        config = self.load()

        return {
            "workspace_path": config.workspace_path,
            "planner_threshold": config.planner.confidence_threshold,
            "router_max_parallel": config.router.max_parallel_steps,
            "approval_required_by_default": config.approval.require_approval_by_default,
            "caching_enabled": config.cache.enable_caching,
            "enabled_workers": sum(1 for w in config.workers.values() if w.enabled),
            "total_workers_configured": len(config.workers),
        }
