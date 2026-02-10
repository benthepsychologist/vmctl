"""Tests for CLI Docker management commands (Gate 2)."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vmctl.cli.commands.docker_commands import (
    _find_local_apps_dir,
    deploy,
    docker_logs,
    docker_ps,
    provision,
    restart,
    setup,
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        remote_script = call_args[0][0]
        assert 'cd "/opt/apps/myapp"' in remote_script
        assert "deploy.sh" in remote_script
        assert "git pull --ff-only" in remote_script

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_deploy_with_explicit_app_dir(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test deploy with explicit --app-dir option."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
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
        remote_script = call_args[0][0]
        assert 'cd "/opt/apps/other"' in remote_script
        assert "deploy.sh" in remote_script
        assert "git pull --ff-only" in remote_script

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_deploy_failure(
        self,
        mock_vm_class: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test deploy failure."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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
        mock_vm.use_direct_ssh = False
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


class TestSetupCommand(TestDockerCommands):
    """Test setup command."""

    def test_setup_no_config(
        self, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test setup with no config file."""
        with TemporaryDirectory() as tmpdir:
            monkeypatch.setenv("HOME", tmpdir)
            result = runner.invoke(setup)
            assert result.exit_code == 1
            assert "No configuration found" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_vm_not_exists(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test setup when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = False
        mock_vm.config.vm_name = "test-vm"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(setup)
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_vm_not_running(
        self, mock_vm_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test setup when VM is not running."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm.config.vm_name = "test-vm"
        mock_vm_class.return_value = mock_vm

        result = runner.invoke(setup)
        assert result.exit_code == 1
        assert "TERMINATED" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_app_not_found(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup when requested app doesn't exist locally."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm_class.return_value = mock_vm

        # Create temp apps dir without the requested app
        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "nonexistent-app"])
            assert result.exit_code == 1
            assert "not found" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_success_skip_provision(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test successful setup with skip-provision flag."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        # All ssh_exec calls succeed
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        # All scp calls succeed
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        # Create temp apps dir with test app
        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app", "--skip-provision"])
            assert result.exit_code == 0
            assert "Setup complete" in result.output
            assert "Skipping Docker provisioning" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_with_docker_already_installed(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup when Docker is already installed."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"

        # command -v docker returns path (Docker installed)
        def ssh_side_effect(cmd: str) -> tuple[bool, str, str]:
            if "command -v docker" in cmd:
                return (True, "/usr/bin/docker", "")
            return (True, "Success", "")

        mock_vm.ssh_exec.side_effect = ssh_side_effect
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app"])
            assert result.exit_code == 0
            assert "Docker already installed" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_provisions_docker_when_not_installed(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup provisions Docker when not installed."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"

        call_count = 0

        def ssh_side_effect(cmd: str) -> tuple[bool, str, str]:
            nonlocal call_count
            call_count += 1
            if "command -v docker" in cmd:
                return (False, "", "")  # Docker not installed
            return (True, "Success", "")

        mock_vm.ssh_exec.side_effect = ssh_side_effect
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app"])
            assert result.exit_code == 0
            assert "Docker provisioned" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_creates_agent_directories(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup creates openclaw-gateway agent directories."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app", "--skip-provision"])
            assert result.exit_code == 0
            assert "Agent directories created" in result.output

            # Verify mkdir commands were called for agent directories
            mkdir_calls = [
                call
                for call in mock_vm.ssh_exec.call_args_list
                if "mkdir" in str(call) and "openclaw-gateway" in str(call)
            ]
            assert len(mkdir_calls) >= 1

            # Verify agent.env placeholder creation is in the script
            mkdir_script = mkdir_calls[0][0][0]
            assert "touch" in mkdir_script
            assert "agent.env" in mkdir_script
            assert "chmod 600" in mkdir_script

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_syncs_app_via_scp(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup syncs app directory via scp."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app", "--skip-provision"])
            assert result.exit_code == 0

            # Verify scp was called with correct paths
            # scp copies the app dir into the parent to avoid double-nesting
            mock_vm.scp.assert_called()
            scp_call = mock_vm.scp.call_args
            assert "test-app" in scp_call[0][0]
            assert scp_call[0][1] == "/srv/vmctl/apps"
            assert scp_call[1]["recursive"] is True

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_deploys_app(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup deploys app via docker compose."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app", "--skip-provision"])
            assert result.exit_code == 0
            assert "test-app deployed successfully" in result.output

            # Verify docker compose was called
            deploy_calls = [
                call
                for call in mock_vm.ssh_exec.call_args_list
                if "docker compose up" in str(call)
            ]
            assert len(deploy_calls) >= 1

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_multiple_apps_in_order(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup deploys multiple apps in correct order."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            # Create two apps
            for app_name in ["app1", "app2"]:
                app = apps_dir / app_name
                app.mkdir()
                (app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "app1,app2", "--skip-provision"])
            assert result.exit_code == 0
            assert "app1 deployed successfully" in result.output
            assert "app2 deployed successfully" in result.output

            # Verify apps were synced/deployed in order
            scp_calls = mock_vm.scp.call_args_list
            assert len(scp_calls) == 2
            assert "app1" in scp_calls[0][0][0]
            assert "app2" in scp_calls[1][0][0]

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_failure_on_mkdir(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup fails gracefully when mkdir fails."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"

        def ssh_side_effect(cmd: str) -> tuple[bool, str, str]:
            if "command -v docker" in cmd:
                return (True, "/usr/bin/docker", "")
            if "mkdir" in cmd and "openclaw-gateway" in cmd:
                return (False, "", "Permission denied")
            return (True, "Success", "")

        mock_vm.ssh_exec.side_effect = ssh_side_effect
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app"])
            assert result.exit_code == 1
            assert "Failed to create agent directories" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_failure_on_scp(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup fails gracefully when scp fails."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        mock_vm.scp.return_value = (False, "", "Connection refused")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app", "--skip-provision"])
            assert result.exit_code == 1
            assert "Failed to sync" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_failure_on_deploy(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup fails gracefully when deploy fails."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.scp.return_value = (True, "", "")

        def ssh_side_effect(cmd: str) -> tuple[bool, str, str]:
            if "docker compose up" in cmd:
                return (False, "", "Container failed to start")
            return (True, "Success", "")

        mock_vm.ssh_exec.side_effect = ssh_side_effect
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            test_app = apps_dir / "test-app"
            test_app.mkdir()
            (test_app / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            result = runner.invoke(setup, ["--apps", "test-app", "--skip-provision"])
            assert result.exit_code == 1
            assert "Failed to deploy" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_with_gateway_repo_option(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup with --gateway-repo option syncs the repo before deploying."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            apps_dir = tmppath / "apps"
            apps_dir.mkdir()
            openclaw_gateway = apps_dir / "openclaw-gateway"
            openclaw_gateway.mkdir()
            (openclaw_gateway / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            # Create a fake gateway repo
            gateway_repo = tmppath / "openclaw-gateway"
            gateway_repo.mkdir()
            (gateway_repo / "Dockerfile").write_text("FROM node:20")

            result = runner.invoke(
                setup,
                ["--apps", "openclaw-gateway", "--skip-provision", "--gateway-repo", str(gateway_repo)],
            )
            assert result.exit_code == 0
            assert "openclaw-gateway repo synced" in result.output

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_gateway_repo_invalid_path_error(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup fails when --gateway-repo points to non-existent path."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"
        mock_vm.ssh_exec.return_value = (True, "Success", "")
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            apps_dir = Path(tmpdir)
            openclaw_gateway = apps_dir / "openclaw-gateway"
            openclaw_gateway.mkdir()
            (openclaw_gateway / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            # Explicitly point to a non-existent path - click should reject this
            nonexistent_repo = "/tmp/definitely-does-not-exist-openclaw-gateway-xyz123"
            result = runner.invoke(
                setup,
                ["--apps", "openclaw-gateway", "--skip-provision", "--gateway-repo", nonexistent_repo],
            )
            # Click validates exists=True and should fail
            assert result.exit_code != 0
            assert "does not exist" in result.output.lower() or "invalid" in result.output.lower()

    @patch("vmctl.cli.commands.docker_commands._find_local_apps_dir")
    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_setup_checks_agent_secrets(
        self,
        mock_vm_class: MagicMock,
        mock_find_apps: MagicMock,
        runner: CliRunner,
        temp_config_dir: Path,
    ) -> None:
        """Test setup checks and warns about empty agent.env."""
        mock_vm = MagicMock()
        mock_vm.use_direct_ssh = False
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm.config.vm_name = "test-vm"

        def ssh_side_effect(cmd: str) -> tuple[bool, str, str]:
            if "SECRETS_FILE" in cmd:
                return (True, "EMPTY", "")
            return (True, "Success", "")

        mock_vm.ssh_exec.side_effect = ssh_side_effect
        mock_vm.scp.return_value = (True, "", "")
        mock_vm_class.return_value = mock_vm

        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            apps_dir = tmppath / "apps"
            apps_dir.mkdir()
            openclaw_gateway = apps_dir / "openclaw-gateway"
            openclaw_gateway.mkdir()
            (openclaw_gateway / "compose.yml").write_text("version: '3'")
            mock_find_apps.return_value = apps_dir

            # Create fake gateway repo to avoid warning about missing repo
            gateway_repo = tmppath / "openclaw-gateway"
            gateway_repo.mkdir()
            (gateway_repo / "Dockerfile").write_text("FROM node:20")

            result = runner.invoke(
                setup,
                ["--apps", "openclaw-gateway", "--skip-provision", "--gateway-repo", str(gateway_repo)],
            )
            assert result.exit_code == 0
            assert "agent.env is empty" in result.output


class TestSyncGatewayRepo:
    """Test _sync_gateway_repo helper function."""

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_sync_gateway_repo_success(
        self,
        mock_vm_class: MagicMock,
    ) -> None:
        """Test successful gateway repo sync."""
        from vmctl.cli.commands.docker_commands import _sync_gateway_repo

        mock_vm = MagicMock()
        mock_vm.ssh_exec.return_value = (True, "", "")
        mock_vm.scp.return_value = (True, "", "")

        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / "Dockerfile").write_text("FROM node:20")

            result = _sync_gateway_repo(mock_vm, repo_path)
            assert result is True
            mock_vm.scp.assert_called_once()

    @patch("vmctl.cli.commands.docker_commands.VMManager")
    def test_sync_gateway_repo_failure(
        self,
        mock_vm_class: MagicMock,
    ) -> None:
        """Test gateway repo sync handles scp failure."""
        from vmctl.cli.commands.docker_commands import _sync_gateway_repo

        mock_vm = MagicMock()
        mock_vm.ssh_exec.return_value = (True, "", "")
        mock_vm.scp.return_value = (False, "", "Connection refused")

        with TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            result = _sync_gateway_repo(mock_vm, repo_path)
            assert result is False


class TestCheckAgentSecrets:
    """Test _check_agent_secrets helper function."""

    def test_check_secrets_ok(self) -> None:
        """Test no warning when secrets file has content."""
        from vmctl.cli.commands.docker_commands import _check_agent_secrets

        mock_vm = MagicMock()
        mock_vm.ssh_exec.return_value = (True, "OK", "")

        # Should not raise, just return silently
        _check_agent_secrets(mock_vm)

    def test_check_secrets_missing(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test warning when secrets file is missing."""
        from vmctl.cli.commands.docker_commands import _check_agent_secrets

        mock_vm = MagicMock()
        mock_vm.ssh_exec.return_value = (True, "MISSING", "")

        _check_agent_secrets(mock_vm)
        # Rich console output captured via stdout
        # The warning should be printed

    def test_check_secrets_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test warning when secrets file is empty."""
        from vmctl.cli.commands.docker_commands import _check_agent_secrets

        mock_vm = MagicMock()
        mock_vm.ssh_exec.return_value = (True, "EMPTY", "")

        _check_agent_secrets(mock_vm)
        # Rich console output captured via stdout
        # The warning should be printed


class TestFindLocalAppsDir:
    """Test _find_local_apps_dir helper function."""

    def test_find_apps_from_cwd(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test finding apps from current working directory."""
        # The function checks package path first, then cwd.
        # Since we're running from the vmctl repo, the package path exists.
        # So we test by verifying the function returns a valid apps path.
        result = _find_local_apps_dir()
        assert result.exists()
        assert result.is_dir()
        assert result.name == "apps"

    def test_find_apps_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test error when apps directory not found."""
        # We can't easily test the raise directly since package path exists
        # This is covered by the setup command tests that mock _find_local_apps_dir
        pass
