"""Configuration management commands."""

import click
from rich.console import Console
from rich.table import Table

from vmctl.config.manager import ConfigManager

console = Console()


@click.command()
@click.option("--vm-name", help="VM instance name")
@click.option("--zone", help="Google Cloud zone (e.g., us-central1-a)")
@click.option("--project", help="Google Cloud project ID")
@click.option("--workstation-disk", help="Source workstation disk for migration")
@click.option("--region", help="Google Cloud region")
@click.option("--show", is_flag=True, help="Show current configuration")
def config(
    vm_name: str | None,
    zone: str | None,
    project: str | None,
    workstation_disk: str | None,
    region: str | None,
    show: bool,
) -> None:
    """Configure VM settings.

    Examples:
        vmctl config --vm-name my-dev-vm --zone us-central1-a
        vmctl config --show
        vmctl config --project my-project
    """
    try:
        config_mgr = ConfigManager()

        # Show current config
        if show:
            if not config_mgr.config_exists():
                console.print("[yellow]No configuration found.[/yellow]")
                console.print("\nRun [blue]vmctl config --vm-name <name> --zone <zone>[/blue] to create one")
                return

            current_config = config_mgr.load()

            table = Table(title="VM Workstation Configuration", show_header=True)
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("VM Name", current_config.vm_name)
            table.add_row("Zone", current_config.zone)
            table.add_row("Project", current_config.project or "[dim](not set)[/dim]")
            table.add_row("Workstation Disk", current_config.workstation_disk or "[dim](not set)[/dim]")
            table.add_row("Region", current_config.region or "[dim](not set)[/dim]")

            console.print(table)
            console.print(f"\n[dim]Config file: {config_mgr.get_config_path()}[/dim]")
            return

        # Update config if any options provided
        if any([vm_name, zone, project, workstation_disk, region]):
            updated = config_mgr.update(
                vm_name=vm_name,
                zone=zone,
                project=project,
                workstation_disk=workstation_disk,
                region=region,
            )

            console.print("[green]✓ Configuration updated[/green]")

            # Show updated values
            table = Table(show_header=False)
            table.add_column("Setting", style="cyan")
            table.add_column("Value", style="green")

            if vm_name:
                table.add_row("VM Name", updated.vm_name)
            if zone:
                table.add_row("Zone", updated.zone)
            if project:
                table.add_row("Project", updated.project or "")
            if workstation_disk:
                table.add_row("Workstation Disk", updated.workstation_disk or "")
            if region:
                table.add_row("Region", updated.region or "")

            console.print(table)
            console.print(f"\n[dim]Saved to: {config_mgr.get_config_path()}[/dim]")

        else:
            # No options provided - show help
            console.print("[yellow]No options specified. Use --help for usage.[/yellow]")
            console.print("\nQuick start:")
            console.print("  [blue]vmctl config --vm-name my-dev-vm --zone us-central1-a[/blue]")
            console.print("\nShow current config:")
            console.print("  [blue]vmctl config --show[/blue]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None
