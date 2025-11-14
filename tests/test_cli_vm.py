"""Tests for CLI VM commands."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vmws.cli.commands.vm_commands import (
    connect,
    create,
    delete,
    init_fresh,
    logs,
    ssh,
    start,
    status,
    stop,
    tunnel,
)
from vmws.config.manager import ConfigManager
from vmws.config.models import VMConfig
from vmws.core.exceptions import VMError


class TestVMCommands:
    """Test VM CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Create temporary config directory with a test config."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".vmws"
            config_dir.mkdir(parents=True)
            monkeypatch.setenv("HOME", tmpdir)

            # Create a default config for tests
            config_mgr = ConfigManager()
            config_mgr.save(VMConfig(vm_name="test-vm", zone="us-central1-a"))

            yield config_dir


class TestCreateCommand(TestVMCommands):
    """Test create command."""

    def test_create_not_implemented(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test that create command shows not implemented message."""
        result = runner.invoke(create)
        assert result.exit_code == 0
        assert "not yet implemented" in result.output
        assert "bin/vmws create" in result.output


class TestInitFreshCommand(TestVMCommands):
    """Test init-fresh command."""

    def test_init_fresh_not_implemented(self, runner: CliRunner, temp_config_dir: Path) -> None:
        """Test that init-fresh command shows not implemented message."""
        result = runner.invoke(init_fresh)
        assert result.exit_code == 0
        assert "not yet implemented" in result.output
        assert "bin/vmws init-fresh" in result.output


class TestStartCommand(TestVMCommands):
    """Test start command."""

    def test_start_no_config(self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test start with no config file."""
        with TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("HOME", tmpdir)
            result = runner.invoke(start)
            assert result.exit_code == 1
            assert "No configuration found" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_start_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test start when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(start)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_start_already_running(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test start when VM is already running."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(start)
        assert result.exit_code == 0
        assert "already running" in result.output
        mock_vm.start.assert_not_called()

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_start_success(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful start."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(start)
        assert result.exit_code == 0
        mock_vm.start.assert_called_once()

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_start_vm_error(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test start with VMError."""
        mock_vm = MagicMock()
        mock_vm.exists.side_effect = VMError("Test error")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(start)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestStopCommand(TestVMCommands):
    """Test stop command."""

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_stop_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test stop when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(stop)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_stop_already_stopped(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test stop when VM is already stopped."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(stop)
        assert result.exit_code == 0
        assert "already stopped" in result.output
        mock_vm.stop.assert_not_called()

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_stop_success(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful stop."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(stop)
        assert result.exit_code == 0
        mock_vm.stop.assert_called_once()

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_stop_vm_error(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test stop with VMError."""
        mock_vm = MagicMock()
        mock_vm.exists.side_effect = VMError("Test error")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(stop)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestStatusCommand(TestVMCommands):
    """Test status command."""

    def test_status_no_config(self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test status with no config file."""
        with TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("HOME", tmpdir)
            result = runner.invoke(status)
            assert result.exit_code == 0
            assert "No configuration found" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_status_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test status when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(status)
        assert result.exit_code == 0
        assert "does not exist" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_status_running(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test status when VM is running."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(status)
        assert result.exit_code == 0
        assert "RUNNING" in result.output
        assert "vmws tunnel" in result.output
        assert "vmws ssh" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_status_stopped(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test status when VM is stopped."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(status)
        assert result.exit_code == 0
        assert "STOPPED" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_status_other_state(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test status with other VM states."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "STAGING"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(status)
        assert result.exit_code == 0
        assert "STAGING" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_status_vm_error(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test status with VMError."""
        mock_vm = MagicMock()
        mock_vm.exists.side_effect = VMError("Test error")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(status)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestSSHCommand(TestVMCommands):
    """Test ssh command."""

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_ssh_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test ssh when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(ssh)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_ssh_vm_not_running(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test ssh when VM is not running."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(ssh)
        assert result.exit_code == 1
        assert "TERMINATED" in result.output
        assert "vmws start" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_ssh_success_interactive(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful ssh without command (interactive)."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(ssh)
        assert result.exit_code == 0
        assert "Connecting" in result.output
        mock_vm.ssh.assert_called_once_with(None)

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_ssh_success_with_command(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful ssh with command."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(ssh, ["ls -la"])
        assert result.exit_code == 0
        mock_vm.ssh.assert_called_once_with("ls -la")

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_ssh_vm_error(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test ssh with VMError."""
        mock_vm = MagicMock()
        mock_vm.exists.side_effect = VMError("Test error")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(ssh)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestConnectCommand(TestVMCommands):
    """Test connect command (alias for ssh)."""

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_connect_delegates_to_ssh(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test that connect delegates to ssh command."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(connect)
        assert result.exit_code == 0
        mock_vm.ssh.assert_called_once()


class TestTunnelCommand(TestVMCommands):
    """Test tunnel command."""

    @patch("vmws.cli.commands.vm_commands.TunnelManager")
    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_tunnel_vm_not_exists(
        self,
        mock_vm_class: MagicMock,
        mock_tunnel_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test tunnel when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(tunnel)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("vmws.cli.commands.vm_commands.TunnelManager")
    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_tunnel_vm_not_running(
        self,
        mock_vm_class: MagicMock,
        mock_tunnel_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test tunnel when VM is not running."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(tunnel)
        assert result.exit_code == 1
        assert "TERMINATED" in result.output

    @patch("vmws.cli.commands.vm_commands.TunnelManager")
    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_tunnel_success_default_port(
        self,
        mock_vm_class: MagicMock,
        mock_tunnel_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test successful tunnel with default port."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        mock_tunnel = MagicMock()
        mock_tunnel_class.return_value = mock_tunnel

        result = runner.invoke(tunnel)
        assert result.exit_code == 0
        mock_tunnel_class.assert_called_once()
        # Verify default port 8080
        call_kwargs = mock_tunnel_class.call_args[1]
        assert call_kwargs["local_port"] == 8080
        mock_tunnel.start.assert_called_once_with(background=False)

    @patch("vmws.cli.commands.vm_commands.TunnelManager")
    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_tunnel_success_custom_port(
        self,
        mock_vm_class: MagicMock,
        mock_tunnel_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test successful tunnel with custom port."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        mock_tunnel = MagicMock()
        mock_tunnel_class.return_value = mock_tunnel

        result = runner.invoke(tunnel, ["--port", "9090"])
        assert result.exit_code == 0
        call_kwargs = mock_tunnel_class.call_args[1]
        assert call_kwargs["local_port"] == 9090

    @patch("vmws.cli.commands.vm_commands.TunnelManager")
    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_tunnel_keyboard_interrupt(
        self,
        mock_vm_class: MagicMock,
        mock_tunnel_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test tunnel handles keyboard interrupt gracefully."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm

        mock_tunnel = MagicMock()
        mock_tunnel.start.side_effect = KeyboardInterrupt()
        mock_tunnel_class.return_value = mock_tunnel

        result = runner.invoke(tunnel)
        assert result.exit_code == 0
        assert "Tunnel stopped" in result.output


class TestLogsCommand(TestVMCommands):
    """Test logs command."""

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_logs_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test logs when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(logs)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_logs_success_default_file(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful logs with default file."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.logs.return_value = "Test log content\nLine 2"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(logs)
        assert result.exit_code == 0
        assert "Test log content" in result.output
        mock_vm.logs.assert_called_once_with("/var/log/vm-auto-shutdown.log")

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_logs_success_custom_file(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful logs with custom file."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.logs.return_value = "Custom log content"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(logs, ["--file", "/var/log/custom.log"])
        assert result.exit_code == 0
        assert "Custom log content" in result.output
        mock_vm.logs.assert_called_once_with("/var/log/custom.log")

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_logs_vm_error(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test logs with VMError."""
        mock_vm = MagicMock()
        mock_vm.exists.side_effect = VMError("Test error")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(logs)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestDeleteCommand(TestVMCommands):
    """Test delete command."""

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_delete_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test delete when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(delete, ["--yes"])
        assert result.exit_code == 0
        assert "does not exist" in result.output

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_delete_with_yes_flag(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test delete with --yes flag (no confirmation)."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(delete, ["--yes"])
        assert result.exit_code == 0
        mock_vm.delete.assert_called_once()

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_delete_without_yes_confirmed(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test delete without --yes flag, user confirms."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(delete, input="y\n")
        assert result.exit_code == 0
        assert "WARNING" in result.output
        mock_vm.delete.assert_called_once()

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_delete_without_yes_cancelled(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test delete without --yes flag, user cancels."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(delete, input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_vm.delete.assert_not_called()

    @patch("vmws.cli.commands.vm_commands.VMManager")
    def test_delete_vm_error(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test delete with VMError."""
        mock_vm = MagicMock()
        mock_vm.exists.side_effect = VMError("Test error")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(delete, ["--yes"])
        assert result.exit_code == 1
        assert "Error" in result.output
