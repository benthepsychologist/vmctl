"""Tests for configuration management."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from vmctl.config.manager import ConfigManager
from vmctl.config.models import VMConfig


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

    def test_ssh_fields_defaults(self) -> None:
        """Test SSH fields default to None."""
        config = VMConfig()
        assert config.ssh_host is None
        assert config.ssh_user is None
        assert config.ssh_key is None
        assert config.ssh_port is None

    def test_ssh_fields_custom(self) -> None:
        """Test SSH fields with custom values."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            ssh_host="10.0.0.5",
            ssh_user="root",
            ssh_key="/home/user/.ssh/id_ed25519",
            ssh_port=2222,
        )
        assert config.ssh_host == "10.0.0.5"
        assert config.ssh_user == "root"
        assert config.ssh_key == "/home/user/.ssh/id_ed25519"
        assert config.ssh_port == 2222

    def test_ssh_fields_to_bash_format(self) -> None:
        """Test SSH fields in bash format output."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            ssh_host="10.0.0.5",
            ssh_user="root",
            ssh_key="/path/to/key",
            ssh_port=2222,
        )
        bash_output = config.to_bash_format()
        assert 'SSH_HOST="10.0.0.5"' in bash_output
        assert 'SSH_USER="root"' in bash_output
        assert 'SSH_KEY="/path/to/key"' in bash_output
        assert 'SSH_PORT="2222"' in bash_output

    def test_ssh_fields_from_bash_format(self) -> None:
        """Test parsing SSH fields from bash format."""
        bash_content = '''
VM_NAME="my-vm"
ZONE="us-central1-a"
PROJECT=""
SSH_HOST="34.42.144.205"
SSH_USER="root"
SSH_KEY="/home/user/.ssh/id_ed25519"
SSH_PORT="2222"
'''
        config = VMConfig.from_bash_format(bash_content)
        assert config.ssh_host == "34.42.144.205"
        assert config.ssh_user == "root"
        assert config.ssh_key == "/home/user/.ssh/id_ed25519"
        assert config.ssh_port == 2222

    def test_ssh_fields_from_bash_format_empty(self) -> None:
        """Test parsing SSH fields when empty (backward compat)."""
        bash_content = '''
VM_NAME="my-vm"
ZONE="us-central1-a"
SSH_HOST=""
SSH_USER=""
SSH_KEY=""
SSH_PORT=""
'''
        config = VMConfig.from_bash_format(bash_content)
        assert config.ssh_host is None
        assert config.ssh_user is None
        assert config.ssh_key is None
        assert config.ssh_port is None

    def test_ssh_fields_from_bash_format_missing(self) -> None:
        """Test old config files without SSH fields still parse."""
        bash_content = '''
VM_NAME="my-vm"
ZONE="us-central1-a"
PROJECT="my-project"
'''
        config = VMConfig.from_bash_format(bash_content)
        assert config.vm_name == "my-vm"
        assert config.ssh_host is None
        assert config.ssh_user is None

    def test_ssh_fields_bash_roundtrip(self) -> None:
        """Test bash format roundtrip with SSH fields."""
        original = VMConfig(
            vm_name="roundtrip-vm",
            zone="us-central1-a",
            project="test-project",
            ssh_host="10.0.0.5",
            ssh_user="devuser",
            ssh_key="/path/to/key",
            ssh_port=2222,
        )
        bash_str = original.to_bash_format()
        parsed = VMConfig.from_bash_format(bash_str)

        assert parsed.ssh_host == original.ssh_host
        assert parsed.ssh_user == original.ssh_user
        assert parsed.ssh_key == original.ssh_key
        assert parsed.ssh_port == original.ssh_port


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
