"""Pytest configuration and shared fixtures."""

from collections.abc import Generator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from codestation.config.manager import ConfigManager
from codestation.config.models import VMConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config() -> VMConfig:
    """Create a standard test configuration."""
    return VMConfig(
        vm_name="test-vm",
        zone="us-central1-a",
        project="test-project",
        workstation_disk="workstation-disk-123",
        region="us-central1",
    )


@pytest.fixture
def minimal_config() -> VMConfig:
    """Create a minimal test configuration."""
    return VMConfig(
        vm_name="minimal-vm",
        zone="us-west1-a",
        project="minimal-project",
    )


@pytest.fixture
def config_manager(temp_dir: Path) -> ConfigManager:
    """Create a ConfigManager with temporary directory."""
    return ConfigManager(config_dir=temp_dir)


@pytest.fixture
def config_manager_with_config(
    temp_dir: Path, test_config: VMConfig
) -> ConfigManager:
    """Create a ConfigManager with pre-saved config."""
    manager = ConfigManager(config_dir=temp_dir)
    manager.save(test_config)
    return manager
