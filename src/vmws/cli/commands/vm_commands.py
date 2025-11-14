"""VM lifecycle commands."""

import click
from rich.console import Console

from vmws.config.manager import ConfigManager
from vmws.core.exceptions import VMError
from vmws.core.tunnel import TunnelManager
from vmws.core.vm import VMManager

console = Console()


@click.command()
def create() -> None:
    """Create a new development VM from Cloud Workstation snapshot.

    This command:
    1. Takes a snapshot of your workstation disk
    2. Creates a new VM with fresh Debian 12
    3. Attaches your workstation data
    4. Installs Docker, code-server, neovim
    5. Sets up auto-shutdown

    Requires configuration with workstation disk info.
    """
    console.print("[red]⚠ The 'create' command is not yet implemented in Python version.[/red]")
    console.print("[yellow]This command will create a VM from an existing Cloud Workstation.[/yellow]")
    console.print("\nPlease use the bash version: [blue]bin/vmws create[/blue]")
    console.print("\nOr use: [green]vmws init-fresh[/green] to create a fresh VM without a workstation.")


@click.command(name="init-fresh")
def init_fresh() -> None:
    """Create a brand new development VM from scratch.

    This command:
    1. Creates a fresh Debian 12 VM
    2. Creates empty 200GB data disk
    3. Installs Docker, code-server, neovim
    4. Sets up auto-shutdown

    No existing workstation needed.
    """
    console.print("[red]⚠ The 'init-fresh' command is not yet implemented in Python version.[/red]")
    console.print("[yellow]This command will create a fresh VM without a Cloud Workstation.[/yellow]")
    console.print("\nPlease use the bash version: [blue]bin/vmws init-fresh[/blue]")


@click.command()
def start() -> None:
    """Start the VM if stopped."""
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        if not config_mgr.config_exists():
            console.print("[red]No configuration found. Run 'vmws config' first.[/red]")
            raise click.Abort()

        vm = VMManager(config)

        if not vm.exists():
            console.print(f"[red]VM {config.vm_name} does not exist.[/red]")
            console.print("[yellow]Create it first with 'vmws create' or 'vmws init-fresh'[/yellow]")
            raise click.Abort()

        status = vm.status()
        if status == "RUNNING":
            console.print(f"[yellow]VM {config.vm_name} is already running[/yellow]")
        else:
            vm.start()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
def stop() -> None:
    """Stop the VM to save money."""
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        vm = VMManager(config)

        if not vm.exists():
            console.print(f"[red]VM {config.vm_name} does not exist.[/red]")
            raise click.Abort()

        status = vm.status()
        if status == "TERMINATED":
            console.print(f"[yellow]VM {config.vm_name} is already stopped[/yellow]")
        else:
            vm.stop()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
def status() -> None:
    """Show VM status."""
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        if not config_mgr.config_exists():
            console.print("[yellow]No configuration found. Run 'vmws config' first.[/yellow]")
            return

        vm = VMManager(config)

        if not vm.exists():
            console.print(f"[red]VM {config.vm_name} does not exist[/red]")
            console.print("[dim]Create it with 'vmws create' or 'vmws init-fresh'[/dim]")
            return

        vm_status = vm.status()

        # Print status with color
        if vm_status == "RUNNING":
            console.print(f"[green]✓ VM {config.vm_name} is RUNNING[/green]")
        elif vm_status == "TERMINATED":
            console.print(f"[yellow]○ VM {config.vm_name} is STOPPED[/yellow]")
        else:
            console.print(f"[blue]● VM {config.vm_name} is {vm_status}[/blue]")

        # Show connection info if running
        if vm_status == "RUNNING":
            console.print("\n[dim]Connect with:[/dim]")
            console.print("  [blue]vmws tunnel[/blue]  → Open code-server")
            console.print("  [blue]vmws ssh[/blue]     → SSH into VM")

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.argument("command", required=False)
def connect(command: str | None) -> None:
    """SSH into the VM (alias for 'ssh')."""
    # Delegate to ssh command
    ctx = click.get_current_context()
    ctx.invoke(ssh, command=command)


@click.command()
@click.argument("command", required=False)
def ssh(command: str | None) -> None:
    """SSH into the VM.

    COMMAND: Optional command to run (if omitted, opens interactive shell)

    Examples:
        vmws ssh              # Interactive shell
        vmws ssh "ls -la"     # Run command
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        vm = VMManager(config)

        if not vm.exists():
            console.print(f"[red]VM {config.vm_name} does not exist.[/red]")
            raise click.Abort()

        vm_status = vm.status()
        if vm_status != "RUNNING":
            console.print(f"[red]VM is {vm_status}. Start it with 'vmws start'[/red]")
            raise click.Abort()

        console.print(f"[blue]Connecting to {config.vm_name}...[/blue]")
        vm.ssh(command)

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.option("--port", "-p", default=8080, help="Local port for tunnel")
def tunnel(port: int) -> None:
    """Start IAP tunnel to code-server.

    This opens a tunnel to the code-server running on your VM.
    Access it at http://localhost:8080 in your browser.

    The tunnel runs in the foreground. Press Ctrl+C to stop.
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        vm = VMManager(config)

        if not vm.exists():
            console.print(f"[red]VM {config.vm_name} does not exist.[/red]")
            raise click.Abort()

        vm_status = vm.status()
        if vm_status != "RUNNING":
            console.print(f"[red]VM is {vm_status}. Start it with 'vmws start'[/red]")
            raise click.Abort()

        tunnel_mgr = TunnelManager(config, local_port=port)
        tunnel_mgr.start(background=False)

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
    except KeyboardInterrupt:
        console.print("\n[yellow]Tunnel stopped[/yellow]")


@click.command()
@click.option("--file", "-f", default="/var/log/vm-auto-shutdown.log", help="Log file to view")
def logs(file: str) -> None:
    """View VM logs (default: auto-shutdown logs)."""
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        vm = VMManager(config)

        if not vm.exists():
            console.print(f"[red]VM {config.vm_name} does not exist.[/red]")
            raise click.Abort()

        console.print(f"[blue]Fetching logs from {file}...[/blue]")
        log_content = vm.logs(file)

        console.print("\n" + log_content)

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()


@click.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def delete(yes: bool) -> None:
    """Delete the VM and all resources.

    WARNING: This is destructive! Make sure you have backups.
    """
    try:
        config_mgr = ConfigManager()
        config = config_mgr.load()

        vm = VMManager(config)

        if not vm.exists():
            console.print(f"[yellow]VM {config.vm_name} does not exist.[/yellow]")
            return

        if not yes:
            console.print(f"[red]⚠ WARNING: This will delete VM {config.vm_name} and its boot disk![/red]")
            console.print("[yellow]Data disk will NOT be deleted (use gcloud to delete manually if needed)[/yellow]")
            if not click.confirm("Are you sure?"):
                console.print("[dim]Cancelled[/dim]")
                return

        vm.delete()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
