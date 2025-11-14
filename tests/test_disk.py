"""Tests for disk management."""

from unittest.mock import MagicMock, patch

import pytest

from vmws.config.models import VMConfig
from vmws.core.disk import DiskManager
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
def disk_manager(vm_config: VMConfig) -> DiskManager:
    """Create disk manager for testing."""
    return DiskManager(vm_config)


class TestDiskManager:
    """Test DiskManager class."""

    def test_data_disk_name(self, disk_manager: DiskManager) -> None:
        """Test data disk name generation."""
        assert disk_manager.data_disk_name == "test-vm-disk"

    @patch("vmws.core.disk.run_command")
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

    @patch("vmws.core.disk.run_command")
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

    @patch("vmws.core.disk.run_command")
    def test_list_snapshots_empty(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test listing snapshots when none exist."""
        mock_run.return_value = CommandResult(0, "[]", "")

        snapshots = disk_manager.list_snapshots()

        assert snapshots == []

    @patch("vmws.core.disk.run_command")
    def test_delete_snapshot(self, mock_run: MagicMock, disk_manager: DiskManager) -> None:
        """Test deleting snapshot."""
        mock_run.return_value = CommandResult(0, "Deleted", "")

        disk_manager.delete_snapshot("test-vm-backup-123")

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "snapshots" in call_args
        assert "delete" in call_args
        assert "test-vm-backup-123" in call_args
