"""Disk and snapshot management operations."""

from datetime import datetime

from rich.console import Console

from codestation.config.models import VMConfig
from codestation.core.exceptions import DiskError
from codestation.utils.subprocess_runner import run_command

console = Console()


class DiskManager:
    """Manages disk snapshots and restores."""

    def __init__(self, config: VMConfig) -> None:
        """Initialize disk manager.

        Args:
            config: VM configuration
        """
        self.config = config
        self.data_disk_name = f"{config.vm_name}-disk"

    def snapshot(self, description: str | None = None) -> str:
        """Create incremental snapshot of data disk.

        Args:
            description: Optional snapshot description

        Returns:
            Snapshot name

        Raises:
            DiskError: If snapshot creation fails
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        snapshot_name = f"{self.config.vm_name}-backup-{timestamp}"

        console.print(f"[blue]Creating snapshot {snapshot_name}...[/blue]")

        try:
            cmd = [
                "gcloud",
                "compute",
                "disks",
                "snapshot",
                self.data_disk_name,
                f"--snapshot-names={snapshot_name}",
                f"--zone={self.config.zone}",
                f"--project={self.config.project}",
            ]

            if description:
                cmd.append(f"--description={description}")

            run_command(cmd, check=True)
            console.print(f"[green]✓ Snapshot {snapshot_name} created[/green]")
            return snapshot_name

        except Exception as e:
            raise DiskError(f"Failed to create snapshot: {e}") from e

    def list_snapshots(self) -> list[dict[str, str]]:
        """List all snapshots for this VM.

        Returns:
            List of snapshot info dicts with keys: name, creationTimestamp, diskSizeGb

        Raises:
            DiskError: If listing fails
        """
        try:
            result = run_command(
                [
                    "gcloud",
                    "compute",
                    "snapshots",
                    "list",
                    f"--filter=name~^{self.config.vm_name}-backup-",
                    f"--project={self.config.project}",
                    "--format=json",
                ],
                check=True,
            )

            # Parse JSON output
            import json

            snapshots = json.loads(result.stdout) if result.stdout else []
            return [
                {
                    "name": s.get("name", ""),
                    "created": s.get("creationTimestamp", ""),
                    "size_gb": s.get("diskSizeGb", ""),
                }
                for s in snapshots
            ]

        except Exception as e:
            raise DiskError(f"Failed to list snapshots: {e}") from e

    def restore(self, snapshot_name: str) -> None:
        """Restore VM from a snapshot.

        This involves:
        1. Stopping the VM (if running)
        2. Deleting the current data disk
        3. Creating new disk from snapshot
        4. Restarting the VM

        Args:
            snapshot_name: Name of snapshot to restore from

        Raises:
            DiskError: If restore fails
        """
        console.print(f"[yellow]⚠ Restoring from snapshot {snapshot_name}...[/yellow]")

        try:
            # Import here to avoid circular dependency
            from codestation.core.vm import VMManager

            vm = VMManager(self.config)

            # Check if VM is running and stop it
            if vm.exists():
                status = vm.status()
                if status == "RUNNING":
                    console.print("[blue]Stopping VM for restore...[/blue]")
                    vm.stop()

            # Delete current data disk
            console.print(f"[blue]Deleting current data disk {self.data_disk_name}...[/blue]")
            run_command(
                [
                    "gcloud",
                    "compute",
                    "disks",
                    "delete",
                    self.data_disk_name,
                    f"--zone={self.config.zone}",
                    f"--project={self.config.project}",
                    "--quiet",
                ],
                check=True,
            )

            # Create new disk from snapshot
            console.print(f"[blue]Creating disk from snapshot {snapshot_name}...[/blue]")
            run_command(
                [
                    "gcloud",
                    "compute",
                    "disks",
                    "create",
                    self.data_disk_name,
                    f"--source-snapshot={snapshot_name}",
                    f"--zone={self.config.zone}",
                    f"--project={self.config.project}",
                ],
                check=True,
            )

            # Restart VM
            console.print("[blue]Starting VM...[/blue]")
            vm.start()

            console.print(f"[green]✓ Successfully restored from {snapshot_name}[/green]")

        except Exception as e:
            raise DiskError(f"Failed to restore from snapshot: {e}") from e

    def delete_snapshot(self, snapshot_name: str) -> None:
        """Delete a snapshot.

        Args:
            snapshot_name: Name of snapshot to delete

        Raises:
            DiskError: If deletion fails
        """
        console.print(f"[red]Deleting snapshot {snapshot_name}...[/red]")

        try:
            run_command(
                [
                    "gcloud",
                    "compute",
                    "snapshots",
                    "delete",
                    snapshot_name,
                    f"--project={self.config.project}",
                    "--quiet",
                ],
                check=True,
            )
            console.print(f"[green]✓ Snapshot {snapshot_name} deleted[/green]")

        except Exception as e:
            raise DiskError(f"Failed to delete snapshot: {e}") from e
