"""Backup and restore commands."""

import click
from rich.console import Console
from rich.table import Table

from codestation.config.manager import ConfigManager
from codestation.core.disk import DiskManager
from codestation.core.exceptions import DiskError

console = Console()


@click.command()
@click.option("--description", "-d", help="Snapshot description")
def backup(description: str | None) -> None:
    """Create incremental snapshot of VM data disk.

    Snapshots are incremental - only changed blocks are stored.
    This makes them very cost-effective for regular backups.

    Cost: ~$0.026/GB/month for incremental data
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        disk_mgr = DiskManager(config)
        snapshot_name = disk_mgr.snapshot(description)

        console.print("\n[green]Snapshot created successfully![/green]")
        console.print(f"[dim]Snapshot name: {snapshot_name}[/dim]")
        console.print("\nView all snapshots: [blue]cstation snapshots[/blue]")
        console.print("Restore from snapshot: [blue]cstation restore <snapshot-name>[/blue]")

    except DiskError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


@click.command()
@click.argument("snapshot_name")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def restore(snapshot_name: str, yes: bool) -> None:
    """Restore VM from a snapshot.

    WARNING: This will replace your current data disk!

    The VM will be stopped, the current data disk deleted,
    and a new disk created from the snapshot.

    SNAPSHOT_NAME: Name of snapshot to restore from
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        disk_mgr = DiskManager(config)

        if not yes:
            console.print(
                f"[red]⚠ WARNING: This will replace the current data disk "
                f"with snapshot {snapshot_name}[/red]"
            )
            console.print("[yellow]All current data on the VM will be lost![/yellow]")
            console.print("\n[dim]Make sure you have a recent backup if needed.[/dim]")

            if not click.confirm("Are you sure you want to continue?"):
                console.print("[dim]Cancelled[/dim]")
                return

        disk_mgr.restore(snapshot_name)

        console.print("\n[green]Restore completed successfully![/green]")
        console.print("\nYour VM is now running with data from the snapshot.")

    except DiskError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


@click.command()
def snapshots() -> None:
    """List all snapshots for this VM."""
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        disk_mgr = DiskManager(config)
        snapshot_list = disk_mgr.list_snapshots()

        if not snapshot_list:
            console.print("[yellow]No snapshots found for this VM.[/yellow]")
            console.print("\nCreate a backup: [blue]cstation backup[/blue]")
            return

        table = Table(title=f"Snapshots for {config.vm_name}", show_header=True)
        table.add_column("Snapshot Name", style="cyan")
        table.add_column("Created", style="green")
        table.add_column("Size (GB)", style="yellow", justify="right")

        for snap in snapshot_list:
            table.add_row(
                snap["name"],
                snap["created"],
                snap["size_gb"],
            )

        console.print(table)

        console.print(f"\n[dim]Total snapshots: {len(snapshot_list)}[/dim]")
        console.print("\nRestore from snapshot: [blue]cstation restore <snapshot-name>[/blue]")

    except DiskError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None
