"""Tests for CLI Docker management commands (Gate 2)."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vmctl.cli.commands.docker_commands import (
    deploy,
    docker_logs,
    docker_ps,
    provision,
    restart,
)
from vmctl.config.manager import ConfigManager
from vmctl.config.models import VMConfig
from vmctl.core.exceptions import VMError


class TestDockerCommands:
    """Base class for Docker command tests."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Create temporary config directory with a test config."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".vmctl"
            config_dir.mkdir(parents=True)
            monkeypatch.setenv("HOME", tmpdir)

            # Create a default config for tests
            config_mgr = ConfigManager()
            config_mgr.save(
                VMConfig(
                    vm_name="test-vm",
                    zone="us-central1-a",
                    project="test-project",
                    app_dir="/opt/apps/myapp",
                )
            )

            yield config_dir

    @pytest.fixture
    def temp_config_no_app_dir(self, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Create temporary config directory without app_dir."""
        with TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".vmctl"
            config_dir.mkdir(parents=True)
            monkeypatch.setenv("HOME", tmpdir)

            # Create config without app_dir
            config_mgr = ConfigManager()
            config_mgr.save(
                VMConfig(
                    vm_name="test-vm",
                    zone="us-central1-a",
                    project="test-project",
                )
            )

            yield config_dir


class TestProvisionCommand(TestDockerCommands):
    """Test provision command."""

    def test_provision_no_config(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test provision with no config file."""
        with TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("HOME", tmpdir)
            result = runner.invoke(provision)
            assert result.exit_code == 1
            assert "No configuration found" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_provision_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test provision when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm.config.vm_name = "test-vm"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(provision)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_provision_vm_not_running(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test provision when VM is not running."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm.config.vm_name = "test-vm"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(provision)
        assert result.exit_code == 1
        assert "TERMINATED" in result.output
        assert "vmctl start" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_provision_success(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test successful provision."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Docker installed successfully", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(provision)
        assert result.exit_code == 0
        assert "provisioned successfully" in result.output
        mock_vm.ssh_exec.assert_called_once()

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_provision_failure(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test provision failure."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (False, "", "Installation failed")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(provision)
        assert result.exit_code == 1
        assert "Failed to provision" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_provision_vm_error(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test provision with VMError."""
        mock_vm = MagicMock()
        mock_vm.exists.side_effect = VMError("Test error")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(provision)
        assert result.exit_code == 1
        assert "Error" in result.output


class TestDeployCommand(TestDockerCommands):
    """Test deploy command."""

    def test_deploy_no_config(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test deploy with no config file."""
        with TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("HOME", tmpdir)
            result = runner.invoke(deploy)
            assert result.exit_code == 1
            assert "No configuration found" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_deploy_no_app_dir(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_no_app_dir: Path
    ) -> None:
        """Test deploy with no app_dir configured or passed."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = None
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(deploy)
        assert result.exit_code == 1
        assert "No app directory specified" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_deploy_with_config_app_dir(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test deploy using app_dir from config."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "Deployment complete", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(deploy)
        assert result.exit_code == 0
        assert "deployed successfully" in result.output
        # Verify the command includes the app_dir
        call_args = mock_vm.ssh_exec.call_args
        assert "/opt/apps/myapp" in call_args[0][0]

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_deploy_with_explicit_app_dir(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test deploy with explicit --app-dir option."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "Deployment complete", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(deploy, ["--app-dir", "/opt/apps/other"])
        assert result.exit_code == 0
        # Verify explicit app-dir overrides config
        call_args = mock_vm.ssh_exec.call_args
        assert "/opt/apps/other" in call_args[0][0]

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_deploy_failure(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test deploy failure."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (False, "", "No compose file found")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(deploy)
        assert result.exit_code == 1
        assert "Failed to deploy" in result.output


class TestPsCommand(TestDockerCommands):
    """Test ps command."""

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_ps_success(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test successful ps command."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (
            True,
            "NAME  IMAGE  STATUS\nweb   nginx  running",
            "",
        )
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_ps)
        assert result.exit_code == 0
        assert "web" in result.output
        assert "nginx" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_ps_with_all_flag(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test ps with --all flag."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "NAME  IMAGE  STATUS", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_ps, ["--all"])
        assert result.exit_code == 0
        # Verify -a flag is passed
        call_args = mock_vm.ssh_exec.call_args
        assert "-a" in call_args[0][0]

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_ps_no_containers(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test ps with no containers."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_ps)
        assert result.exit_code == 0
        assert "No containers found" in result.output


class TestLogsCommand(TestDockerCommands):
    """Test logs command."""

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_logs_success(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test successful logs command."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (
            True,
            "2024-01-01 Log line 1\n2024-01-01 Log line 2",
            "",
        )
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_logs)
        assert result.exit_code == 0
        assert "Log line 1" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_logs_with_service(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test logs for specific service."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "Web service logs", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_logs, ["web"])
        assert result.exit_code == 0
        # Verify service name is passed
        call_args = mock_vm.ssh_exec.call_args
        assert "web" in call_args[0][0]

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_logs_with_tail(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test logs with custom tail count."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "Last 50 lines", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_logs, ["--tail", "50"])
        assert result.exit_code == 0
        # Verify tail count is passed
        call_args = mock_vm.ssh_exec.call_args
        assert "--tail 50" in call_args[0][0]

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_logs_no_logs(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test logs when no logs found."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_logs)
        assert result.exit_code == 0
        assert "No logs found" in result.output


class TestRestartCommand(TestDockerCommands):
    """Test restart command."""

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_restart_all_services(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test restart all services."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "Restart complete", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(restart)
        assert result.exit_code == 0
        assert "Restarted all services successfully" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_restart_specific_service(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test restart specific service."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "Restart complete", "")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(restart, ["web"])
        assert result.exit_code == 0
        assert "service 'web'" in result.output
        # Verify service name is passed
        call_args = mock_vm.ssh_exec.call_args
        assert "web" in call_args[0][0]

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_restart_failure(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test restart failure."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (False, "", "Service not found")
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(restart)
        assert result.exit_code == 1
        assert "Failed to restart" in result.output


class TestAppDirResolution(TestDockerCommands):
    """Test app_dir resolution across commands."""

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_explicit_app_dir_overrides_config(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test that explicit --app-dir overrides config value."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = "/opt/apps/myapp"
        mock_vm.ssh_exec.return_value = (True, "Output", "")
        mock_vm_class.return_value = mock_vm

        # Test with ps command
        result = runner.invoke(docker_ps, ["--app-dir", "/custom/path"])
        assert result.exit_code == 0
        call_args = mock_vm.ssh_exec.call_args
        assert "/custom/path" in call_args[0][0]
        assert "/opt/apps/myapp" not in call_args[0][0]

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_missing_app_dir_shows_helpful_error(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_no_app_dir: Path,
    ) -> None:
        """Test helpful error when app_dir is not set."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.config.app_dir = None
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(docker_ps)
        assert result.exit_code == 1
        assert "No app directory specified" in result.output
        assert "--app-dir" in result.output
        assert "vmctl config" in result.output


class TestVMConfigAppDir:
    """Test VMConfig app_dir serialization."""

    def test_config_with_app_dir_to_bash(self) -> None:
        """Test config with app_dir serializes to bash format."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            project="test-project",
            app_dir="/opt/apps/myapp",
        )
        bash_format = config.to_bash_format()
        assert 'APP_DIR="/opt/apps/myapp"' in bash_format

    def test_config_without_app_dir_to_bash(self) -> None:
        """Test config without app_dir serializes with empty value."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            project="test-project",
        )
        bash_format = config.to_bash_format()
        assert 'APP_DIR=""' in bash_format

    def test_config_from_bash_with_app_dir(self) -> None:
        """Test parsing bash config with app_dir."""
        bash_content = '''
VM_NAME="test-vm"
ZONE="us-central1-a"
PROJECT="test-project"
APP_DIR="/opt/apps/myapp"
'''
        config = VMConfig.from_bash_format(bash_content)
        assert config.app_dir == "/opt/apps/myapp"

    def test_config_from_bash_without_app_dir(self) -> None:
        """Test parsing bash config without app_dir."""
        bash_content = '''
VM_NAME="test-vm"
ZONE="us-central1-a"
PROJECT="test-project"
'''
        config = VMConfig.from_bash_format(bash_content)
        assert config.app_dir is None

    def test_config_from_bash_with_empty_app_dir(self) -> None:
        """Test parsing bash config with empty app_dir."""
        bash_content = '''
VM_NAME="test-vm"
ZONE="us-central1-a"
PROJECT="test-project"
APP_DIR=""
'''
        config = VMConfig.from_bash_format(bash_content)
        assert config.app_dir is None
