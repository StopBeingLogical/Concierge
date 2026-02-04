"""Tests for configuration management."""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from bit.workspace import Workspace
from bit.config import (
    ConciergeConfig,
    ConfigManager,
    PlannerConfig,
    RouterConfig,
    ApprovalConfig,
    CacheConfig,
    WorkerConfig,
)


class TestConfigModels:
    """Tests for configuration models."""

    def test_create_planner_config(self):
        """Test creating planner configuration."""
        config = PlannerConfig(confidence_threshold=0.8, max_candidates=10)

        assert config.confidence_threshold == 0.8
        assert config.max_candidates == 10

    def test_create_router_config(self):
        """Test creating router configuration."""
        config = RouterConfig(max_parallel_steps=4)

        assert config.max_parallel_steps == 4
        assert config.enable_event_logging is True

    def test_create_approval_config(self):
        """Test creating approval configuration."""
        config = ApprovalConfig(require_approval_by_default=True)

        assert config.require_approval_by_default is True

    def test_create_cache_config(self):
        """Test creating cache configuration."""
        config = CacheConfig(enable_caching=False)

        assert config.enable_caching is False

    def test_create_worker_config(self):
        """Test creating worker configuration."""
        config = WorkerConfig(
            worker_id="test_worker",
            timeout_seconds=600,
            retry_count=5,
        )

        assert config.worker_id == "test_worker"
        assert config.timeout_seconds == 600
        assert config.retry_count == 5

    def test_create_full_config(self):
        """Test creating complete configuration."""
        config = ConciergeConfig(
            version="1.0.0",
            workspace_path="/workspace",
            planner=PlannerConfig(confidence_threshold=0.75),
            router=RouterConfig(max_parallel_steps=2),
            workers={
                "worker1": WorkerConfig(worker_id="worker1"),
                "worker2": WorkerConfig(worker_id="worker2", enabled=False),
            },
        )

        assert config.version == "1.0.0"
        assert config.planner.confidence_threshold == 0.75
        assert len(config.workers) == 2


class TestConfigManager:
    """Tests for ConfigManager."""

    @pytest.fixture
    def workspace(self):
        """Create temporary workspace for testing."""
        with TemporaryDirectory() as tmpdir:
            ws = Workspace(tmpdir)
            ws.initialize()
            yield tmpdir

    @pytest.fixture
    def config_manager(self, workspace):
        """Create config manager for testing."""
        return ConfigManager(workspace)

    def test_load_default_config(self, config_manager):
        """Test loading default configuration."""
        config = config_manager.load()

        assert config is not None
        assert config.planner is not None
        assert config.router is not None

    def test_save_and_load_config(self, config_manager):
        """Test saving and loading configuration."""
        config = ConciergeConfig(
            version="1.0.0",
            planner=PlannerConfig(confidence_threshold=0.85),
        )

        config_manager.save(config)
        loaded = config_manager.load()

        assert loaded.planner.confidence_threshold == 0.85

    def test_get_planner_config(self, config_manager):
        """Test getting planner configuration."""
        config = config_manager.load()
        config.planner.confidence_threshold = 0.9
        config_manager.save(config)

        planner_config = config_manager.get_planner_config()

        assert planner_config.confidence_threshold == 0.9

    def test_get_router_config(self, config_manager):
        """Test getting router configuration."""
        router_config = config_manager.get_router_config()

        assert router_config is not None
        assert hasattr(router_config, 'max_parallel_steps')

    def test_get_approval_config(self, config_manager):
        """Test getting approval configuration."""
        approval_config = config_manager.get_approval_config()

        assert approval_config is not None
        assert hasattr(approval_config, 'require_approval_by_default')

    def test_update_planner_config(self, config_manager):
        """Test updating planner configuration."""
        config_manager.update_planner_config({
            "confidence_threshold": 0.85,
            "max_candidates": 8,
        })

        planner_config = config_manager.get_planner_config()

        assert planner_config.confidence_threshold == 0.85
        assert planner_config.max_candidates == 8

    def test_get_worker_config(self, config_manager):
        """Test getting worker configuration."""
        config = config_manager.load()
        config.workers["test_worker"] = WorkerConfig(worker_id="test_worker", timeout_seconds=500)
        config_manager.save(config)

        worker_config = config_manager.get_worker_config("test_worker")

        assert worker_config is not None
        assert worker_config.timeout_seconds == 500

    def test_get_worker_config_not_found(self, config_manager):
        """Test getting non-existent worker configuration."""
        worker_config = config_manager.get_worker_config("nonexistent")

        assert worker_config is None

    def test_update_worker_config(self, config_manager):
        """Test updating worker configuration."""
        config_manager.update_worker_config("new_worker", {
            "timeout_seconds": 600,
            "retry_count": 5,
        })

        worker_config = config_manager.get_worker_config("new_worker")

        assert worker_config is not None
        assert worker_config.timeout_seconds == 600
        assert worker_config.retry_count == 5

    def test_enable_worker(self, config_manager):
        """Test enabling a worker."""
        config = config_manager.load()
        config.workers["test_worker"] = WorkerConfig(
            worker_id="test_worker",
            enabled=False,
        )
        config_manager.save(config)

        config_manager.enable_worker("test_worker")

        assert config_manager.is_worker_enabled("test_worker") is True

    def test_disable_worker(self, config_manager):
        """Test disabling a worker."""
        config = config_manager.load()
        config.workers["test_worker"] = WorkerConfig(
            worker_id="test_worker",
            enabled=True,
        )
        config_manager.save(config)

        config_manager.disable_worker("test_worker")

        assert config_manager.is_worker_enabled("test_worker") is False

    def test_is_worker_enabled_default(self, config_manager):
        """Test worker enabled status defaults to True."""
        assert config_manager.is_worker_enabled("nonexistent") is True

    def test_get_config_summary(self, config_manager):
        """Test getting configuration summary."""
        config = config_manager.load()
        config.workers["worker1"] = WorkerConfig(worker_id="worker1", enabled=True)
        config.workers["worker2"] = WorkerConfig(worker_id="worker2", enabled=False)
        config_manager.save(config)

        summary = config_manager.get_config_summary()

        assert "workspace_path" in summary
        assert "planner_threshold" in summary
        assert summary["enabled_workers"] == 1
        assert summary["total_workers_configured"] == 2

    def test_config_persistence(self, config_manager):
        """Test that configuration persists across manager instances."""
        config_manager.update_planner_config({"confidence_threshold": 0.88})

        # Create new manager instance
        config_manager2 = ConfigManager(config_manager.workspace_path)
        planner_config = config_manager2.get_planner_config()

        assert planner_config.confidence_threshold == 0.88

    def test_worker_config_with_resource_limits(self, config_manager):
        """Test worker configuration with resource limits."""
        config_manager.update_worker_config("gpu_worker", {
            "resource_limits": {
                "memory_mb": 4096,
                "gpu_memory_mb": 8192,
            }
        })

        worker_config = config_manager.get_worker_config("gpu_worker")

        assert "memory_mb" in worker_config.resource_limits
        assert worker_config.resource_limits["memory_mb"] == 4096
