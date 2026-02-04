"""Tests for CLI config commands."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from vmctl.cli.commands.config_commands import config
from vmctl.config.manager import ConfigManager
from vmctl.config.models import VMConfig


class TestConfigCommand:
    """Test config CLI command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Create temporary config directory."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".vmctl"
            config_dir.mkdir(parents=True)
            # Mock the home directory to use temp dir
            monkeypatch.setenv("HOME", tmpdir)
            yield config_dir

    def test_config_no_args_no_config(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test config command with no args and no existing config."""
        result = runner.invoke(config)
        assert result.exit_code == 0
        assert "No options specified" in result.output
        assert "vmctl config --vm-name" in result.output

    def test_config_show_no_config(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test --show with no existing config."""
        result = runner.invoke(config, ["--show"])
        assert result.exit_code == 0
        assert "No configuration found" in result.output

    def test_config_create_minimal(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test creating config with minimal required options."""
        result = runner.invoke(config, ["--vm-name", "test-vm", "--zone", "us-west1-a"])
        assert result.exit_code == 0
        assert "Configuration updated" in result.output
        assert "test-vm" in result.output
        assert "us-west1-a" in result.output

        # Verify config was saved
        config_mgr = ConfigManager()
        saved_config = config_mgr.load()
        assert saved_config.vm_name == "test-vm"
        assert saved_config.zone == "us-west1-a"

    def test_config_create_full(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test creating config with all options."""
        result = runner.invoke(
            config,
            [
                "--vm-name",
                "full-vm",
                "--zone",
                "us-east1-b",
                "--project",
                "my-project",
                "--workstation-disk",
                "disk-123",
                "--region",
                "us-east1",
            ],
        )
        assert result.exit_code == 0
        assert "Configuration updated" in result.output

        # Verify all values saved
        config_mgr = ConfigManager()
        saved_config = config_mgr.load()
        assert saved_config.vm_name == "full-vm"
        assert saved_config.zone == "us-east1-b"
        assert saved_config.project == "my-project"
        assert saved_config.workstation_disk == "disk-123"
        assert saved_config.region == "us-east1"

    def test_config_update_existing(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test updating existing config."""
        # Create initial config
        config_mgr = ConfigManager()
        config_mgr.save(
            VMConfig(vm_name="old-vm", zone="us-central1-a", project="old-project")
        )

        # Update just the VM name
        result = runner.invoke(config, ["--vm-name", "new-vm"])
        assert result.exit_code == 0
        assert "Configuration updated" in result.output

        # Verify only vm_name changed - create new manager to avoid cache
        new_config_mgr = ConfigManager()
        saved_config = new_config_mgr.load()
        assert saved_config.vm_name == "new-vm"
        assert saved_config.zone == "us-central1-a"  # unchanged
        assert saved_config.project == "old-project"  # unchanged

    def test_config_show_existing(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test --show with existing config."""
        # Create config
        config_mgr = ConfigManager()
        config_mgr.save(
            VMConfig(
                vm_name="show-vm",
                zone="europe-west1-b",
                project="show-project",
                workstation_disk="disk-456",
                region="europe-west1",
            )
        )

        result = runner.invoke(config, ["--show"])
        assert result.exit_code == 0
        assert "VM Workstation Configuration" in result.output
        assert "show-vm" in result.output
        assert "europe-west1-b" in result.output
        assert "show-project" in result.output
        assert "disk-456" in result.output
        assert "europe-west1" in result.output

    def test_config_show_partial(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test --show with partial config (some None values)."""
        config_mgr = ConfigManager()
        config_mgr.save(VMConfig(vm_name="minimal-vm", zone="asia-east1-a"))

        result = runner.invoke(config, ["--show"])
        assert result.exit_code == 0
        assert "minimal-vm" in result.output
        assert "asia-east1-a" in result.output
        assert "(not set)" in result.output  # Should show for None values

    def test_config_invalid_vm_name(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test config with invalid VM name."""
        result = runner.invoke(config, ["--vm-name", "123-invalid", "--zone", "us-central1-a"])
        # Should fail validation in the config model
        assert result.exit_code != 0

    def test_config_error_handling(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test error handling in config command."""
        # Mock ConfigManager to raise exception
        with patch("vmctl.cli.commands.config_commands.ConfigManager") as mock_mgr:
            mock_mgr.side_effect = Exception("Test error")
            result = runner.invoke(config, ["--show"])
            assert result.exit_code != 0
            assert "Error" in result.output

    def test_config_update_zone_only(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test updating just the zone."""
        config_mgr = ConfigManager()
        config_mgr.save(VMConfig(vm_name="test-vm", zone="us-central1-a"))

        result = runner.invoke(config, ["--zone", "us-west1-c"])
        assert result.exit_code == 0

        # Create new manager to avoid cache
        new_config_mgr = ConfigManager()
        saved_config = new_config_mgr.load()
        assert saved_config.zone == "us-west1-c"
        assert saved_config.vm_name == "test-vm"  # unchanged

    def test_config_update_project_only(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test updating just the project."""
        config_mgr = ConfigManager()
        config_mgr.save(VMConfig(vm_name="test-vm", zone="us-central1-a"))

        result = runner.invoke(config, ["--project", "new-project"])
        assert result.exit_code == 0

        # Create new manager to avoid cache
        new_config_mgr = ConfigManager()
        saved_config = new_config_mgr.load()
        assert saved_config.project == "new-project"

    def test_config_path_displayed(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test that config path is displayed in output."""
        result = runner.invoke(config, ["--vm-name", "path-test", "--zone", "us-central1-a"])
        assert result.exit_code == 0
        assert "Saved to:" in result.output
        assert ".vmctl/config" in result.output
