"""Tests for CLI backup commands."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from vmws.cli.commands.backup_commands import backup, restore, snapshots
from vmws.config.manager import ConfigManager
from vmws.config.models import VMConfig
from vmws.core.exceptions import DiskError


class TestBackupCommands:
    """Test backup CLI commands."""

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


class TestBackupCommand(TestBackupCommands):
    """Test backup command."""

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_backup_success_no_description(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful backup without description."""
        mock_disk = MagicMock()
        mock_disk.snapshot.return_value = "snapshot-test-vm-20240101-120000"
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(backup)
        assert result.exit_code == 0
        assert "Snapshot created successfully" in result.output
        assert "snapshot-test-vm-20240101-120000" in result.output
        mock_disk.snapshot.assert_called_once_with(None)

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_backup_success_with_description(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test successful backup with description."""
        mock_disk = MagicMock()
        mock_disk.snapshot.return_value = "snapshot-test-vm-20240101-120000"
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(backup, ["--description", "Before major update"])
        assert result.exit_code == 0
        assert "Snapshot created successfully" in result.output
        mock_disk.snapshot.assert_called_once_with("Before major update")

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_backup_disk_error(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test backup with DiskError."""
        mock_disk = MagicMock()
        mock_disk.snapshot.side_effect = DiskError("Test disk error")
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(backup)
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Test disk error" in result.output

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_backup_shows_next_steps(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test backup shows next steps in output."""
        mock_disk = MagicMock()
        mock_disk.snapshot.return_value = "snapshot-test"
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(backup)
        assert result.exit_code == 0
        assert "vmws snapshots" in result.output
        assert "vmws restore" in result.output


class TestRestoreCommand(TestBackupCommands):
    """Test restore command."""

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_restore_with_yes_flag(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test restore with --yes flag (no confirmation)."""
        mock_disk = MagicMock()
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(restore, ["snapshot-test-123", "--yes"])
        assert result.exit_code == 0
        assert "Restore completed successfully" in result.output
        mock_disk.restore.assert_called_once_with("snapshot-test-123")

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_restore_without_yes_confirmed(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test restore without --yes flag, user confirms."""
        mock_disk = MagicMock()
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(restore, ["snapshot-test-123"], input="y\n")
        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "Restore completed successfully" in result.output
        mock_disk.restore.assert_called_once_with("snapshot-test-123")

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_restore_without_yes_cancelled(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test restore without --yes flag, user cancels."""
        mock_disk = MagicMock()
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(restore, ["snapshot-test-123"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output
        mock_disk.restore.assert_not_called()

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_restore_disk_error(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test restore with DiskError."""
        mock_disk = MagicMock()
        mock_disk.restore.side_effect = DiskError("Snapshot not found")
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(restore, ["nonexistent-snapshot", "--yes"])
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Snapshot not found" in result.output

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_restore_shows_warning(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test restore shows warning without --yes."""
        mock_disk = MagicMock()
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(restore, ["snapshot-test"], input="n\n")
        assert result.exit_code == 0
        assert "WARNING" in result.output
        assert "replace the current data disk" in result.output
        assert "All current data on the VM will be lost" in result.output


class TestSnapshotsCommand(TestBackupCommands):
    """Test snapshots command."""

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_snapshots_empty_list(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test snapshots with no snapshots available."""
        mock_disk = MagicMock()
        mock_disk.list_snapshots.return_value = []
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(snapshots)
        assert result.exit_code == 0
        assert "No snapshots found" in result.output
        assert "vmws backup" in result.output

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_snapshots_single_snapshot(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test snapshots with one snapshot."""
        mock_disk = MagicMock()
        mock_disk.list_snapshots.return_value = [
            {
                "name": "snapshot-test-vm-20240101-120000",
                "created": "2024-01-01 12:00:00",
                "size_gb": "5.2",
            }
        ]
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(snapshots)
        assert result.exit_code == 0
        assert "Snapshots for test-vm" in result.output
        assert "snapshot-test-vm-20240101-120000" in result.output
        assert "2024-01-01 12:00:00" in result.output
        assert "5.2" in result.output
        assert "Total snapshots: 1" in result.output

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_snapshots_multiple_snapshots(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test snapshots with multiple snapshots."""
        mock_disk = MagicMock()
        mock_disk.list_snapshots.return_value = [
            {
                "name": "snapshot-test-vm-20240101-120000",
                "created": "2024-01-01 12:00:00",
                "size_gb": "5.2",
            },
            {
                "name": "snapshot-test-vm-20240102-120000",
                "created": "2024-01-02 12:00:00",
                "size_gb": "6.8",
            },
            {
                "name": "snapshot-test-vm-20240103-120000",
                "created": "2024-01-03 12:00:00",
                "size_gb": "7.5",
            },
        ]
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(snapshots)
        assert result.exit_code == 0
        assert "snapshot-test-vm-20240101-120000" in result.output
        assert "snapshot-test-vm-20240102-120000" in result.output
        assert "snapshot-test-vm-20240103-120000" in result.output
        assert "Total snapshots: 3" in result.output

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_snapshots_disk_error(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test snapshots with DiskError."""
        mock_disk = MagicMock()
        mock_disk.list_snapshots.side_effect = DiskError("Cannot list snapshots")
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(snapshots)
        assert result.exit_code == 1
        assert "Error" in result.output
        assert "Cannot list snapshots" in result.output

    @patch("vmws.cli.commands.backup_commands.DiskManager")
    def test_snapshots_shows_restore_help(
        self, mock_disk_class: MagicMock, runner: CliRunner, temp_config_dir: Path
    ) -> None:
        """Test snapshots shows restore help."""
        mock_disk = MagicMock()
        mock_disk.list_snapshots.return_value = [
            {"name": "snapshot-test", "created": "2024-01-01", "size_gb": "5.0"}
        ]
        mock_disk_class.return_value = mock_disk

        result = runner.invoke(snapshots)
        assert result.exit_code == 0
        assert "vmws restore" in result.output
