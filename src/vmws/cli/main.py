"""Main CLI entry point for VM Workstation Manager."""

import click
from rich.console import Console

from vmws import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="vmws")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """VM Workstation Manager - Self-managed development VMs for Google Cloud.

    Save 61-83% on cloud development costs by replacing Google Cloud Workstations
    with self-managed VMs.

    Quick Start:
        vmws config          # Configure VM settings
        vmws init-fresh      # Create new VM from scratch
        vmws start           # Start VM
        vmws tunnel          # Connect to code-server
        vmws stop            # Stop VM to save money

    For more info: https://github.com/benthepsychologist/vm-workstation-manager
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


# Import command groups
from vmws.cli.commands import backup_commands, config_commands, vm_commands

# Register command groups
cli.add_command(vm_commands.create)
cli.add_command(vm_commands.init_fresh)
cli.add_command(vm_commands.start)
cli.add_command(vm_commands.stop)
cli.add_command(vm_commands.status)
cli.add_command(vm_commands.connect)
cli.add_command(vm_commands.ssh)
cli.add_command(vm_commands.tunnel)
cli.add_command(vm_commands.logs)
cli.add_command(vm_commands.delete)

cli.add_command(config_commands.config)

cli.add_command(backup_commands.backup)
cli.add_command(backup_commands.restore)
cli.add_command(backup_commands.snapshots)


if __name__ == "__main__":
    cli()
