"""Tests for configuration management."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from vmws.config.manager import ConfigManager
from vmws.config.models import VMConfig


class TestVMConfig:
    """Test VMConfig model."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = VMConfig()
        assert config.vm_name == "dev-workstation"
        assert config.zone == "us-central1-a"
        assert config.project is None
        assert config.workstation_disk is None
        assert config.region is None

    def test_custom_values(self) -> None:
        """Test custom configuration values."""
        config = VMConfig(
            vm_name="my-vm",
            zone="us-west1-b",
            project="my-project",
            workstation_disk="workstation-disk-123",
            region="us-west1",
        )
        assert config.vm_name == "my-vm"
        assert config.zone == "us-west1-b"
        assert config.project == "my-project"
        assert config.workstation_disk == "workstation-disk-123"
        assert config.region == "us-west1"

    def test_vm_name_validation(self) -> None:
        """Test VM name validation."""
        # Valid names
        VMConfig(vm_name="my-vm")
        VMConfig(vm_name="vm123")
        VMConfig(vm_name="a-b-c-1-2-3")

        # Invalid names
        with pytest.raises(ValueError, match="cannot be empty"):
            VMConfig(vm_name="")

        with pytest.raises(ValueError, match="must start with a letter"):
            VMConfig(vm_name="123vm")

        with pytest.raises(ValueError, match="can only contain"):
            VMConfig(vm_name="vm_with_underscores")

        with pytest.raises(ValueError, match="cannot exceed 63 characters"):
            VMConfig(vm_name="a" * 64)

    def test_zone_validation(self) -> None:
        """Test zone validation."""
        # Valid zones
        VMConfig(zone="us-central1-a")
        VMConfig(zone="europe-west1-b")

        # Invalid zones
        with pytest.raises(ValueError, match="cannot be empty"):
            VMConfig(zone="")

        with pytest.raises(ValueError, match="Invalid zone format"):
            VMConfig(zone="us-central")

    def test_to_bash_format(self) -> None:
        """Test conversion to bash source format."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-east1-c",
            project="test-project",
            workstation_disk="disk-123",
            region="us-east1",
        )
        bash_output = config.to_bash_format()

        assert 'VM_NAME="test-vm"' in bash_output
        assert 'ZONE="us-east1-c"' in bash_output
        assert 'PROJECT="test-project"' in bash_output
        assert 'WORKSTATION_DISK="disk-123"' in bash_output
        assert 'REGION="us-east1"' in bash_output

    def test_from_bash_format(self) -> None:
        """Test parsing from bash source format."""
        bash_content = '''
VM_NAME="my-dev-vm"
ZONE="us-west2-a"
PROJECT="my-gcp-project"
WORKSTATION_DISK=""
REGION="us-west2"
'''
        config = VMConfig.from_bash_format(bash_content)

        assert config.vm_name == "my-dev-vm"
        assert config.zone == "us-west2-a"
        assert config.project == "my-gcp-project"
        assert config.workstation_disk is None
        assert config.region == "us-west2"

    def test_bash_roundtrip(self) -> None:
        """Test bash format roundtrip conversion."""
        original = VMConfig(
            vm_name="roundtrip-vm",
            zone="asia-east1-a",
            project="roundtrip-project",
        )

        bash_str = original.to_bash_format()
        parsed = VMConfig.from_bash_format(bash_str)

        assert parsed.vm_name == original.vm_name
        assert parsed.zone == original.zone
        assert parsed.project == original.project


class TestConfigManager:
    """Test ConfigManager."""

    def test_load_nonexistent_creates_default(self) -> None:
        """Test loading config when file doesn't exist creates default."""
        with TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=Path(tmpdir))
            config = manager.load()

            assert config.vm_name == "dev-workstation"
            assert config.zone == "us-central1-a"

    def test_save_and_load(self) -> None:
        """Test saving and loading configuration."""
        with TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=Path(tmpdir))

            # Save config
            config = VMConfig(
                vm_name="save-test-vm",
                zone="us-central1-b",
                project="save-test-project",
            )
            manager.save(config)

            # Load in new manager instance
            manager2 = ConfigManager(config_dir=Path(tmpdir))
            loaded = manager2.load()

            assert loaded.vm_name == "save-test-vm"
            assert loaded.zone == "us-central1-b"
            assert loaded.project == "save-test-project"

    def test_update(self) -> None:
        """Test updating configuration."""
        with TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=Path(tmpdir))

            # Initial config
            manager.save(VMConfig(vm_name="initial-vm"))

            # Update some fields
            updated = manager.update(
                vm_name="updated-vm",
                zone="europe-west1-a",
            )

            assert updated.vm_name == "updated-vm"
            assert updated.zone == "europe-west1-a"

            # Verify persisted
            manager2 = ConfigManager(config_dir=Path(tmpdir))
            loaded = manager2.load()
            assert loaded.vm_name == "updated-vm"
            assert loaded.zone == "europe-west1-a"

    def test_config_exists(self) -> None:
        """Test checking if config exists."""
        with TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=Path(tmpdir))

            assert not manager.config_exists()

            manager.save(VMConfig())

            assert manager.config_exists()

    def test_get_config_path(self) -> None:
        """Test getting config file path."""
        with TemporaryDirectory() as tmpdir:
            manager = ConfigManager(config_dir=Path(tmpdir))
            path = manager.get_config_path()

            assert path == Path(tmpdir) / "config"
