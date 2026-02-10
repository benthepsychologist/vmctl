"""Main CLI entry point for vmctl."""

import click
from rich.console import Console

from vmctl import __version__

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="vmctl")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """vmctl - Self-managed development environments on Google Cloud.

    Save 61-83% on cloud development costs by replacing Google Cloud Workstations
    with self-managed VMs.

    Quick Start:
        vmctl config          # Configure VM settings
        vmctl init-fresh      # Create new VM from scratch
        vmctl start           # Start VM
        vmctl tunnel          # Connect to code-server
        vmctl stop            # Stop VM to save money

    For more info: https://github.com/benthepsychologist/vmctl
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


# Import command groups
from vmctl.cli.commands import (
    backup_commands,
    config_commands,
    docker_commands,
    vm_commands,
)

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

cli.add_command(docker_commands.up)
cli.add_command(docker_commands.down)

# Docker management commands (Gate 2)
cli.add_command(docker_commands.provision)
cli.add_command(docker_commands.deploy)
cli.add_command(docker_commands.docker_ps)
cli.add_command(docker_commands.docker_logs)
cli.add_command(docker_commands.restart)

# Multi-app setup command (Gate 5)
cli.add_command(docker_commands.setup)

# Secrets management command (Gate 6)
cli.add_command(docker_commands.secrets)


if __name__ == "__main__":
    cli()
