"""Tests for VM management."""

from unittest.mock import MagicMock, patch

import pytest

from vmctl.config.models import VMConfig
from vmctl.core.exceptions import VMError
from vmctl.core.vm import VMManager
from vmctl.utils.subprocess_runner import CommandResult


@pytest.fixture
def vm_config() -> VMConfig:
    """Create test VM config."""
    return VMConfig(
        vm_name="test-vm",
        zone="us-central1-a",
        project="test-project",
    )


@pytest.fixture
def vm_manager(vm_config: VMConfig) -> VMManager:
    """Create VM manager for testing."""
    return VMManager(vm_config)


class TestVMManager:
    """Test VMManager class."""

    @patch("vmctl.core.vm.run_command")
    def test_exists_true(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test VM exists check when VM exists."""
        mock_run.return_value = CommandResult(0, "VM details", "")
        assert vm_manager.exists() is True

    @patch("vmctl.core.vm.run_command")
    def test_exists_false(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test VM exists check when VM doesn't exist."""
        mock_run.return_value = CommandResult(1, "", "Not found")
        assert vm_manager.exists() is False

    @patch("vmctl.core.vm.run_command")
    def test_status_running(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test getting VM status when running."""
        mock_run.return_value = CommandResult(0, "RUNNING", "")
        assert vm_manager.status() == "RUNNING"

    @patch("vmctl.core.vm.run_command")
    def test_status_stopped(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test getting VM status when stopped."""
        mock_run.return_value = CommandResult(0, "TERMINATED", "")
        assert vm_manager.status() == "TERMINATED"

    @patch("vmctl.core.vm.run_command")
    def test_status_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test VM status when command fails."""
        mock_run.return_value = CommandResult(1, "", "Error")
        with pytest.raises(VMError, match="Failed to get VM status"):
            vm_manager.status()

    @patch("vmctl.core.vm.run_command")
    def test_start(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test starting VM."""
        mock_run.return_value = CommandResult(0, "Started", "")
        vm_manager.start()
        mock_run.assert_called_once()

    @patch("vmctl.core.vm.run_command")
    def test_stop(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test stopping VM."""
        mock_run.return_value = CommandResult(0, "Stopped", "")
        vm_manager.stop()
        mock_run.assert_called_once()

    @patch("vmctl.core.vm.run_command")
    def test_delete(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test deleting VM."""
        mock_run.return_value = CommandResult(0, "Deleted", "")
        vm_manager.delete()
        mock_run.assert_called_once()

    @patch("vmctl.core.vm.run_command")
    def test_start_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test starting VM with error."""
        from vmctl.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Start failed")
        with pytest.raises(VMError, match="Failed to start VM"):
            vm_manager.start()

    @patch("vmctl.core.vm.run_command")
    def test_stop_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test stopping VM with error."""
        from vmctl.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Stop failed")
        with pytest.raises(VMError, match="Failed to stop VM"):
            vm_manager.stop()

    @patch("vmctl.core.vm.run_command")
    def test_delete_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test deleting VM with error."""
        from vmctl.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Delete failed")
        with pytest.raises(VMError, match="Failed to delete VM"):
            vm_manager.delete()

    @patch("vmctl.core.vm.run_command")
    def test_ssh_interactive(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test SSH without command (interactive)."""
        mock_run.return_value = CommandResult(0, "", "")
        vm_manager.ssh()

        expected_cmd = [
            "gcloud",
            "compute",
            "ssh",
            "test-vm",
            "--zone=us-central1-a",
            "--project=test-project",
            "--tunnel-through-iap",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_ssh_with_command(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test SSH with command."""
        mock_run.return_value = CommandResult(0, "output", "")
        vm_manager.ssh("ls -la")

        expected_cmd = [
            "gcloud",
            "compute",
            "ssh",
            "test-vm",
            "--zone=us-central1-a",
            "--project=test-project",
            "--tunnel-through-iap",
            "--command",
            "ls -la",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_ssh_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test SSH with command failure."""
        mock_run.return_value = CommandResult(1, "", "SSH failed")
        with pytest.raises(VMError, match="SSH command failed"):
            vm_manager.ssh("bad-command")

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exception(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test SSH with exception."""
        from vmctl.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Network error")
        with pytest.raises(VMError, match="Failed to SSH to VM"):
            vm_manager.ssh()

    @patch("vmctl.core.vm.run_command")
    def test_logs_default_file(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test retrieving logs with default file."""
        mock_run.return_value = CommandResult(0, "log contents", "")
        result = vm_manager.logs()

        assert result == "log contents"
        call_args = mock_run.call_args[0][0]
        assert "sudo cat /var/log/vm-auto-shutdown.log" in call_args

    @patch("vmctl.core.vm.run_command")
    def test_logs_custom_file(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test retrieving logs with custom file."""
        mock_run.return_value = CommandResult(0, "custom log", "")
        result = vm_manager.logs("/var/log/custom.log")

        assert result == "custom log"
        call_args = mock_run.call_args[0][0]
        assert "sudo cat /var/log/custom.log" in call_args

    @patch("vmctl.core.vm.run_command")
    def test_logs_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test retrieving logs with error."""
        mock_run.return_value = CommandResult(1, "", "File not found")
        with pytest.raises(VMError, match="Failed to retrieve logs"):
            vm_manager.logs()

    @patch("vmctl.core.vm.run_command")
    def test_status_empty_output(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test status with empty output."""
        mock_run.return_value = CommandResult(0, "", "")
        assert vm_manager.status() == "UNKNOWN"

    @patch("vmctl.core.vm.run_command")
    def test_exists_verifies_command(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test exists calls correct gcloud command."""
        mock_run.return_value = CommandResult(0, "output", "")
        vm_manager.exists()

        expected_cmd = [
            "gcloud",
            "compute",
            "instances",
            "describe",
            "test-vm",
            "--zone=us-central1-a",
            "--project=test-project",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_delete_includes_delete_boot_disk(
        self, mock_run: MagicMock, vm_manager: VMManager
    ) -> None:
        """Test delete includes --delete-disks=boot flag."""
        mock_run.return_value = CommandResult(0, "", "")
        vm_manager.delete()

        call_args = mock_run.call_args[0][0]
        assert "--delete-disks=boot" in call_args
        assert "--quiet" in call_args

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exec_success(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test ssh_exec with successful command."""
        mock_run.return_value = CommandResult(0, "output text", "")
        success, stdout, stderr = vm_manager.ssh_exec("echo hello")

        assert success is True
        assert stdout == "output text"
        assert stderr == ""

        expected_cmd = [
            "gcloud",
            "compute",
            "ssh",
            "test-vm",
            "--zone=us-central1-a",
            "--project=test-project",
            "--tunnel-through-iap",
            "--command",
            "echo hello",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exec_failure(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test ssh_exec with failed command."""
        mock_run.return_value = CommandResult(1, "", "command not found")
        success, stdout, stderr = vm_manager.ssh_exec("bad-command")

        assert success is False
        assert stdout == ""
        assert stderr == "command not found"

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exec_multiline_script(
        self, mock_run: MagicMock, vm_manager: VMManager
    ) -> None:
        """Test ssh_exec with multiline script."""
        mock_run.return_value = CommandResult(0, "line1\nline2", "")
        script = """
set -e
echo "hello"
echo "world"
"""
        success, stdout, stderr = vm_manager.ssh_exec(script)

        assert success is True
        assert stdout == "line1\nline2"
        # Verify the script was passed as the command
        call_args = mock_run.call_args[0][0]
        assert "--command" in call_args
        assert script in call_args

    @patch("vmctl.core.vm.run_command")
    def test_scp_file_success(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test scp single file to VM."""
        mock_run.return_value = CommandResult(0, "", "")
        success, stdout, stderr = vm_manager.scp("/local/file.txt", "/remote/file.txt")

        assert success is True
        assert stdout == ""
        assert stderr == ""

        expected_cmd = [
            "gcloud",
            "compute",
            "scp",
            "/local/file.txt",
            "test-vm:/remote/file.txt",
            "--zone=us-central1-a",
            "--project=test-project",
            "--tunnel-through-iap",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_scp_directory_recursive(
        self, mock_run: MagicMock, vm_manager: VMManager
    ) -> None:
        """Test scp directory with recursive flag."""
        mock_run.return_value = CommandResult(0, "", "")
        success, stdout, stderr = vm_manager.scp(
            "/local/dir", "/remote/dir", recursive=True
        )

        assert success is True

        expected_cmd = [
            "gcloud",
            "compute",
            "scp",
            "--recurse",
            "/local/dir",
            "test-vm:/remote/dir",
            "--zone=us-central1-a",
            "--project=test-project",
            "--tunnel-through-iap",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_scp_failure(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test scp with failure."""
        mock_run.return_value = CommandResult(1, "", "Permission denied")
        success, stdout, stderr = vm_manager.scp("/local/file.txt", "/remote/file.txt")

        assert success is False
        assert stderr == "Permission denied"


@pytest.fixture
def direct_ssh_config() -> VMConfig:
    """Create test VM config with direct SSH enabled."""
    return VMConfig(
        vm_name="test-vm",
        zone="us-central1-a",
        project="test-project",
        ssh_host="10.0.0.5",
        ssh_user="devuser",
    )


@pytest.fixture
def direct_ssh_manager(direct_ssh_config: VMConfig) -> VMManager:
    """Create VM manager with direct SSH for testing."""
    return VMManager(direct_ssh_config)


class TestVMManagerDirectSSH:
    """Test VMManager with direct SSH transport."""

    def test_use_direct_ssh_when_host_set(
        self, direct_ssh_manager: VMManager
    ) -> None:
        """Test use_direct_ssh is True when ssh_host is configured."""
        assert direct_ssh_manager.use_direct_ssh is True

    def test_use_gcloud_when_host_not_set(self, vm_manager: VMManager) -> None:
        """Test use_direct_ssh is False when ssh_host is not set."""
        assert vm_manager.use_direct_ssh is False

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exec_direct(
        self, mock_run: MagicMock, direct_ssh_manager: VMManager
    ) -> None:
        """Test ssh_exec uses plain ssh when direct SSH configured."""
        mock_run.return_value = CommandResult(0, "output", "")
        success, stdout, stderr = direct_ssh_manager.ssh_exec("echo hello")

        assert success is True
        assert stdout == "output"
        expected_cmd = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "devuser@10.0.0.5",
            "echo hello",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exec_direct_with_key(self, mock_run: MagicMock) -> None:
        """Test ssh_exec includes -i flag when ssh_key is set."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            project="test-project",
            ssh_host="10.0.0.5",
            ssh_user="root",
            ssh_key="/path/to/key",
        )
        vm = VMManager(config)
        mock_run.return_value = CommandResult(0, "", "")
        vm.ssh_exec("hostname")

        cmd = mock_run.call_args[0][0]
        assert "-i" in cmd
        assert "/path/to/key" in cmd

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exec_direct_with_port(self, mock_run: MagicMock) -> None:
        """Test ssh_exec includes -p flag when ssh_port is set."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            project="test-project",
            ssh_host="10.0.0.5",
            ssh_user="root",
            ssh_port=2222,
        )
        vm = VMManager(config)
        mock_run.return_value = CommandResult(0, "", "")
        vm.ssh_exec("hostname")

        cmd = mock_run.call_args[0][0]
        assert "-p" in cmd
        assert "2222" in cmd

    @patch("vmctl.core.vm.run_command")
    def test_ssh_exec_direct_no_user(self, mock_run: MagicMock) -> None:
        """Test ssh_exec with host only (no user)."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            project="test-project",
            ssh_host="10.0.0.5",
        )
        vm = VMManager(config)
        mock_run.return_value = CommandResult(0, "", "")
        vm.ssh_exec("hostname")

        cmd = mock_run.call_args[0][0]
        assert "10.0.0.5" in cmd
        # Should not have user@ prefix
        assert "devuser@10.0.0.5" not in cmd

    @patch("vmctl.core.vm.run_command")
    def test_scp_direct(
        self, mock_run: MagicMock, direct_ssh_manager: VMManager
    ) -> None:
        """Test scp uses plain scp when direct SSH configured."""
        mock_run.return_value = CommandResult(0, "", "")
        success, _, _ = direct_ssh_manager.scp("/local/file", "/remote/file")

        assert success is True
        expected_cmd = [
            "scp",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            "/local/file",
            "devuser@10.0.0.5:/remote/file",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=False)

    @patch("vmctl.core.vm.run_command")
    def test_scp_direct_recursive(
        self, mock_run: MagicMock, direct_ssh_manager: VMManager
    ) -> None:
        """Test scp with recursive flag uses -r (not --recurse)."""
        mock_run.return_value = CommandResult(0, "", "")
        direct_ssh_manager.scp("/local/dir", "/remote/dir", recursive=True)

        cmd = mock_run.call_args[0][0]
        assert "-r" in cmd
        assert "--recurse" not in cmd

    @patch("vmctl.core.vm.run_command")
    def test_scp_direct_with_port(self, mock_run: MagicMock) -> None:
        """Test scp uses uppercase -P for port."""
        config = VMConfig(
            vm_name="test-vm",
            zone="us-central1-a",
            project="test-project",
            ssh_host="10.0.0.5",
            ssh_user="root",
            ssh_port=2222,
        )
        vm = VMManager(config)
        mock_run.return_value = CommandResult(0, "", "")
        vm.scp("/local/file", "/remote/file")

        cmd = mock_run.call_args[0][0]
        assert "-P" in cmd
        assert "2222" in cmd
        # SSH uses lowercase -p, SCP uses uppercase -P
        p_index = cmd.index("-P")
        assert cmd[p_index + 1] == "2222"

    @patch("vmctl.core.vm.run_command")
    def test_ssh_interactive_direct(
        self, mock_run: MagicMock, direct_ssh_manager: VMManager
    ) -> None:
        """Test interactive ssh uses plain ssh."""
        mock_run.return_value = CommandResult(0, "", "")
        direct_ssh_manager.ssh()

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ssh"
        assert "devuser@10.0.0.5" in cmd
        assert "gcloud" not in cmd

    @patch("vmctl.core.vm.run_command")
    def test_ssh_interactive_direct_with_command(
        self, mock_run: MagicMock, direct_ssh_manager: VMManager
    ) -> None:
        """Test ssh with command uses plain ssh."""
        mock_run.return_value = CommandResult(0, "", "")
        direct_ssh_manager.ssh("ls -la")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ssh"
        assert "ls -la" in cmd
        # Direct SSH puts command as last arg, not --command
        assert "--command" not in cmd

    @patch("vmctl.core.vm.run_command")
    def test_logs_direct(
        self, mock_run: MagicMock, direct_ssh_manager: VMManager
    ) -> None:
        """Test logs method works via direct SSH."""
        mock_run.return_value = CommandResult(0, "log content here", "")
        result = direct_ssh_manager.logs()

        assert result == "log content here"
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ssh"
        assert "sudo cat /var/log/vm-auto-shutdown.log" in cmd
