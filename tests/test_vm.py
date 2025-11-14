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
