"""Tests for VM management."""

from unittest.mock import MagicMock, patch

import pytest

from vmws.config.models import VMConfig
from vmws.core.exceptions import VMError
from vmws.core.vm import VMManager
from vmws.utils.subprocess_runner import CommandResult


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

    @patch("vmws.core.vm.run_command")
    def test_exists_true(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test VM exists check when VM exists."""
        mock_run.return_value = CommandResult(0, "VM details", "")
        assert vm_manager.exists() is True

    @patch("vmws.core.vm.run_command")
    def test_exists_false(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test VM exists check when VM doesn't exist."""
        mock_run.return_value = CommandResult(1, "", "Not found")
        assert vm_manager.exists() is False

    @patch("vmws.core.vm.run_command")
    def test_status_running(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test getting VM status when running."""
        mock_run.return_value = CommandResult(0, "RUNNING", "")
        assert vm_manager.status() == "RUNNING"

    @patch("vmws.core.vm.run_command")
    def test_status_stopped(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test getting VM status when stopped."""
        mock_run.return_value = CommandResult(0, "TERMINATED", "")
        assert vm_manager.status() == "TERMINATED"

    @patch("vmws.core.vm.run_command")
    def test_status_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test VM status when command fails."""
        mock_run.return_value = CommandResult(1, "", "Error")
        with pytest.raises(VMError, match="Failed to get VM status"):
            vm_manager.status()

    @patch("vmws.core.vm.run_command")
    def test_start(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test starting VM."""
        mock_run.return_value = CommandResult(0, "Started", "")
        vm_manager.start()
        mock_run.assert_called_once()

    @patch("vmws.core.vm.run_command")
    def test_stop(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test stopping VM."""
        mock_run.return_value = CommandResult(0, "Stopped", "")
        vm_manager.stop()
        mock_run.assert_called_once()

    @patch("vmws.core.vm.run_command")
    def test_delete(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test deleting VM."""
        mock_run.return_value = CommandResult(0, "Deleted", "")
        vm_manager.delete()
        mock_run.assert_called_once()

    @patch("vmws.core.vm.run_command")
    def test_start_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test starting VM with error."""
        from vmws.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Start failed")
        with pytest.raises(VMError, match="Failed to start VM"):
            vm_manager.start()

    @patch("vmws.core.vm.run_command")
    def test_stop_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test stopping VM with error."""
        from vmws.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Stop failed")
        with pytest.raises(VMError, match="Failed to stop VM"):
            vm_manager.stop()

    @patch("vmws.core.vm.run_command")
    def test_delete_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test deleting VM with error."""
        from vmws.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Delete failed")
        with pytest.raises(VMError, match="Failed to delete VM"):
            vm_manager.delete()

    @patch("vmws.core.vm.run_command")
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

    @patch("vmws.core.vm.run_command")
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

    @patch("vmws.core.vm.run_command")
    def test_ssh_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test SSH with command failure."""
        mock_run.return_value = CommandResult(1, "", "SSH failed")
        with pytest.raises(VMError, match="SSH command failed"):
            vm_manager.ssh("bad-command")

    @patch("vmws.core.vm.run_command")
    def test_ssh_exception(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test SSH with exception."""
        from vmws.core.exceptions import GCloudError

        mock_run.side_effect = GCloudError("Network error")
        with pytest.raises(VMError, match="Failed to SSH to VM"):
            vm_manager.ssh()

    @patch("vmws.core.vm.run_command")
    def test_logs_default_file(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test retrieving logs with default file."""
        mock_run.return_value = CommandResult(0, "log contents", "")
        result = vm_manager.logs()

        assert result == "log contents"
        call_args = mock_run.call_args[0][0]
        assert "sudo cat /var/log/vm-auto-shutdown.log" in call_args

    @patch("vmws.core.vm.run_command")
    def test_logs_custom_file(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test retrieving logs with custom file."""
        mock_run.return_value = CommandResult(0, "custom log", "")
        result = vm_manager.logs("/var/log/custom.log")

        assert result == "custom log"
        call_args = mock_run.call_args[0][0]
        assert "sudo cat /var/log/custom.log" in call_args

    @patch("vmws.core.vm.run_command")
    def test_logs_error(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test retrieving logs with error."""
        mock_run.return_value = CommandResult(1, "", "File not found")
        with pytest.raises(VMError, match="Failed to retrieve logs"):
            vm_manager.logs()

    @patch("vmws.core.vm.run_command")
    def test_status_empty_output(self, mock_run: MagicMock, vm_manager: VMManager) -> None:
        """Test status with empty output."""
        mock_run.return_value = CommandResult(0, "", "")
        assert vm_manager.status() == "UNKNOWN"

    @patch("vmws.core.vm.run_command")
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

    @patch("vmws.core.vm.run_command")
    def test_delete_includes_delete_boot_disk(
        self, mock_run: MagicMock, vm_manager: VMManager
    ) -> None:
        """Test delete includes --delete-disks=boot flag."""
        mock_run.return_value = CommandResult(0, "", "")
        vm_manager.delete()

        call_args = mock_run.call_args[0][0]
        assert "--delete-disks=boot" in call_args
        assert "--quiet" in call_args
