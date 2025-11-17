"""Tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from codestation.cli.main import cli
from codestation.config.models import VMConfig


@pytest.fixture
def runner() -> CliRunner:
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_config() -> VMConfig:
    """Create mock VM config."""
    return VMConfig(
        vm_name="test-vm",
        zone="us-central1-a",
        project="test-project",
    )


class TestCLIVersion:
    """Test CLI version command."""

    def test_version_option(self, runner: CliRunner) -> None:
        """Test --version flag shows version."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "cstation" in result.output.lower()


class TestCLIHelp:
    """Test CLI help commands."""

    def test_main_help(self, runner: CliRunner) -> None:
        """Test main CLI help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Codestation" in result.output
        assert "Quick Start:" in result.output

    def test_create_help(self, runner: CliRunner) -> None:
        """Test create command help."""
        result = runner.invoke(cli, ["create", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output.lower()

    def test_start_help(self, runner: CliRunner) -> None:
        """Test start command help."""
        result = runner.invoke(cli, ["start", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output.lower()

    def test_stop_help(self, runner: CliRunner) -> None:
        """Test stop command help."""
        result = runner.invoke(cli, ["stop", "--help"])
        assert result.exit_code == 0
        assert "stop" in result.output.lower()

    def test_status_help(self, runner: CliRunner) -> None:
        """Test status command help."""
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output.lower()

    def test_config_help(self, runner: CliRunner) -> None:
        """Test config command help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.output.lower()

    def test_backup_help(self, runner: CliRunner) -> None:
        """Test backup command help."""
        result = runner.invoke(cli, ["backup", "--help"])
        assert result.exit_code == 0
        assert "backup" in result.output.lower()


class TestCLICommands:
    """Test CLI command execution."""

    @patch("codestation.cli.commands.config_commands.ConfigManager")
    def test_config_command(
        self,
        mock_config_manager: MagicMock,
        runner: CliRunner,
        mock_config: VMConfig,
    ) -> None:
        """Test config command sets values."""
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.update.return_value = mock_config

        result = runner.invoke(
            cli,
            ["config", "--vm-name", "my-vm", "--zone", "us-west1-a"],
        )

        assert result.exit_code == 0
        mock_manager.update.assert_called_once()

    @patch("codestation.cli.commands.vm_commands.VMManager")
    @patch("codestation.cli.commands.vm_commands.ConfigManager")
    def test_status_command(
        self,
        mock_config_manager: MagicMock,
        mock_vm_manager: MagicMock,
        runner: CliRunner,
        mock_config: VMConfig,
    ) -> None:
        """Test status command."""
        mock_config_mgr = MagicMock()
        mock_config_manager.return_value = mock_config_mgr
        mock_config_mgr.load.return_value = mock_config

        mock_vm = MagicMock()
        mock_vm_manager.return_value = mock_vm
        mock_vm.status.return_value = "RUNNING"

        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        mock_vm.status.assert_called_once()

    @patch("codestation.cli.commands.backup_commands.DiskManager")
    @patch("codestation.cli.commands.backup_commands.ConfigManager")
    def test_backup_command(
        self,
        mock_config_manager: MagicMock,
        mock_disk_manager: MagicMock,
        runner: CliRunner,
        mock_config: VMConfig,
    ) -> None:
        """Test backup command."""
        mock_config_mgr = MagicMock()
        mock_config_manager.return_value = mock_config_mgr
        mock_config_mgr.load.return_value = mock_config

        mock_disk = MagicMock()
        mock_disk_manager.return_value = mock_disk
        mock_disk.snapshot.return_value = "snapshot-123"

        result = runner.invoke(cli, ["backup"])

        assert result.exit_code == 0
        mock_disk.snapshot.assert_called_once()


class TestCLIErrorHandling:
    """Test CLI error handling."""

    @patch("codestation.cli.commands.config_commands.ConfigManager")
    def test_config_missing_project(
        self,
        mock_config_manager: MagicMock,
        runner: CliRunner,
    ) -> None:
        """Test config command handles missing project."""
        mock_manager = MagicMock()
        mock_config_manager.return_value = mock_manager
        mock_manager.update.return_value = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            project=None,
        )

        # Should still succeed but warn about missing project
        result = runner.invoke(cli, ["config", "--vm-name", "test-vm"])
        assert result.exit_code == 0
