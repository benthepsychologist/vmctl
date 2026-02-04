"""Tests for disk management."""

from unittest.mock import MagicMock, patch

import pytest

from vmctl.config.models import VMConfig
from vmctl.core.disk import DiskManager
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
def disk_manager(vm_config: VMConfig) -> DiskManager:
    """Create disk manager for testing."""
    return DiskManager(vm_config)


class TestDiskManager:
    """Test DiskManager class."""

    def test_data_disk_name(self, disk_manager: DiskManager) -> None:
        """Test data disk name generation."""
        assert disk_manager.data_disk_name == "test-vm-disk"

    @patch("vmctl.core.disk.run_command")
    def test_snapshot(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test creating snapshot."""
        mock_run.return_value = CommandResult(0, "Snapshot created", "")

        snapshot_name = disk_manager.snapshot()

        assert snapshot_name.startswith("test-vm-backup-")
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "gcloud" in call_args
        assert "disks" in call_args
        assert "snapshot" in call_args

    @patch("vmctl.core.disk.run_command")
    def test_list_snapshots(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test listing snapshots."""
        mock_run.return_value = CommandResult(
            0,
            '[{"name": "test-vm-backup-123", "creationTimestamp": "2024-01-01", "diskSizeGb": "200"}]',
            "",
        )

        snapshots = disk_manager.list_snapshots()

        assert len(snapshots) == 1
        assert snapshots[0]["name"] == "test-vm-backup-123"
        assert snapshots[0]["size_gb"] == "200"

    @patch("vmctl.core.disk.run_command")
    def test_list_snapshots_empty(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test listing snapshots when none exist."""
        mock_run.return_value = CommandResult(0, "[]", "")

        snapshots = disk_manager.list_snapshots()

        assert snapshots == []

    @patch("vmctl.core.disk.run_command")
    def test_delete_snapshot(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test deleting snapshot."""
        mock_run.return_value = CommandResult(0, "Deleted", "")

        disk_manager.delete_snapshot("test-vm-backup-123")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "snapshots" in call_args
        assert "delete" in call_args
        assert "test-vm-backup-123" in call_args

    @patch("vmctl.core.disk.run_command")
    def test_snapshot_with_description(
        self, mock_run: MagicMock, disk_manager: DiskManager
    ) -> None:
        """Test creating snapshot with description."""
        mock_run.return_value = CommandResult(0, "Snapshot created", "")

        snapshot_name = disk_manager.snapshot(description="Before upgrade")

        assert snapshot_name.startswith("test-vm-backup-")
        call_args = mock_run.call_args[0][0]
        assert "--description=Before upgrade" in call_args

    @patch("vmctl.core.disk.run_command")
    def test_snapshot_error(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test snapshot creation error."""
        from vmctl.core.exceptions import DiskError, GCloudError

        mock_run.side_effect = GCloudError("Disk not found")

        with pytest.raises(DiskError, match="Failed to create snapshot"):
            disk_manager.snapshot()

    @patch("vmctl.core.disk.run_command")
    def test_list_snapshots_error(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test list snapshots with error."""
        from vmctl.core.exceptions import DiskError, GCloudError

        mock_run.side_effect = GCloudError("Permission denied")

        with pytest.raises(DiskError, match="Failed to list snapshots"):
            disk_manager.list_snapshots()

    @patch("vmctl.core.disk.run_command")
    def test_list_snapshots_empty_stdout(
        self, mock_run: MagicMock, disk_manager: DiskManager
    ) -> None:
        """Test list snapshots with empty stdout."""
        mock_run.return_value = CommandResult(0, "", "")

        snapshots = disk_manager.list_snapshots()

        assert snapshots == []

    @patch("vmctl.core.disk.run_command")
    def test_delete_snapshot_error(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test delete snapshot with error."""
        from vmctl.core.exceptions import DiskError, GCloudError

        mock_run.side_effect = GCloudError("Snapshot not found")

        with pytest.raises(DiskError, match="Failed to delete snapshot"):
            disk_manager.delete_snapshot("nonexistent")

    @patch("vmctl.core.disk.run_command")
    @patch("vmctl.core.vm.VMManager")
    def test_restore_vm_running(
        self,
        mock_vm_class: MagicMock,
        mock_run: MagicMock,
        disk_manager: DiskManager,
    ) -> None:
        """Test restore when VM is running (should stop it first)."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "RUNNING"
        mock_vm_class.return_value = mock_vm
        mock_run.return_value = CommandResult(0, "Success", "")

        disk_manager.restore("test-vm-backup-123")

        # Verify VM was stopped
        mock_vm.stop.assert_called_once()
        # Verify VM was started after restore
        mock_vm.start.assert_called_once()
        # Verify disk operations
        assert mock_run.call_count == 2  # delete disk, create disk

    @patch("vmctl.core.disk.run_command")
    @patch("vmctl.core.vm.VMManager")
    def test_restore_vm_stopped(
        self,
        mock_vm_class: MagicMock,
        mock_run: MagicMock,
        disk_manager: DiskManager,
    ) -> None:
        """Test restore when VM is already stopped."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = True
        mock_vm.status.return_value = "TERMINATED"
        mock_vm_class.return_value = mock_vm
        mock_run.return_value = CommandResult(0, "Success", "")

        disk_manager.restore("test-vm-backup-123")

        # Should not call stop
        mock_vm.stop.assert_not_called()
        # Should start VM after restore
        mock_vm.start.assert_called_once()

    @patch("vmctl.core.disk.run_command")
    @patch("vmctl.core.vm.VMManager")
    def test_restore_vm_not_exists(
        self,
        mock_vm_class: MagicMock,
        mock_run: MagicMock,
        disk_manager: DiskManager,
    ) -> None:
        """Test restore when VM doesn't exist."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm
        mock_run.return_value = CommandResult(0, "Success", "")

        disk_manager.restore("test-vm-backup-123")

        # Should not check status or stop if VM doesn't exist
        mock_vm.status.assert_not_called()
        mock_vm.stop.assert_not_called()
        # Should still create disk and start VM
        mock_vm.start.assert_called_once()

    @patch("vmctl.core.disk.run_command")
    @patch("vmctl.core.vm.VMManager")
    def test_restore_error(
        self,
        mock_vm_class: MagicMock,
        mock_run: MagicMock,
        disk_manager: DiskManager,
    ) -> None:
        """Test restore with error."""
        from vmctl.core.exceptions import DiskError, GCloudError

        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm
        mock_run.side_effect = GCloudError("Restore failed")

        with pytest.raises(DiskError, match="Failed to restore from snapshot"):
            disk_manager.restore("test-vm-backup-123")

    @patch("vmctl.core.disk.run_command")
    @patch("vmctl.core.vm.VMManager")
    def test_restore_calls_correct_commands(
        self,
        mock_vm_class: MagicMock,
        mock_run: MagicMock,
        disk_manager: DiskManager,
    ) -> None:
        """Test restore calls correct gcloud commands."""
        mock_vm = MagicMock()
        mock_vm.exists.return_value = False
        mock_vm_class.return_value = mock_vm
        mock_run.return_value = CommandResult(0, "Success", "")

        disk_manager.restore("test-vm-backup-123")

        # Check delete disk command
        delete_call = mock_run.call_args_list[0][0][0]
        assert "disks" in delete_call
        assert "delete" in delete_call
        assert "test-vm-disk" in delete_call
        assert "--quiet" in delete_call

        # Check create disk command
        create_call = mock_run.call_args_list[1][0][0]
        assert "disks" in create_call
        assert "create" in create_call
        assert "test-vm-disk" in create_call
        assert "--source-snapshot=test-vm-backup-123" in create_call

    @patch("vmctl.core.disk.run_command")
    def test_snapshot_includes_disk_name(
        self, mock_run: MagicMock, disk_manager: DiskManager
    ) -> None:
        """Test snapshot uses correct disk name."""
        mock_run.return_value = CommandResult(0, "Success", "")

        disk_manager.snapshot()

        call_args = mock_run.call_args[0][0]
        assert "test-vm-disk" in call_args

    @patch("vmctl.core.disk.run_command")
    def test_list_snapshots_filters_by_vm_name(
        self, mock_run: MagicMock, disk_manager: DiskManager
    ) -> None:
        """Test list snapshots filters by VM name."""
        mock_run.return_value = CommandResult(0, "[]", "")

        disk_manager.list_snapshots()

        call_args = mock_run.call_args[0][0]
        assert "--filter=name~^test-vm-backup-" in call_args

    @patch("vmctl.core.disk.run_command")
    def test_delete_snapshot_includes_quiet_flag(
        self, mock_run: MagicMock, disk_manager: DiskManager
    ) -> None:
        """Test delete snapshot includes --quiet flag."""
        mock_run.return_value = CommandResult(0, "Success", "")

        disk_manager.delete_snapshot("test-snapshot")

        call_args = mock_run.call_args[0][0]
        assert "--quiet" in call_args
