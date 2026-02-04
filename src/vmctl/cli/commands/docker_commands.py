"""Docker-based local and cloud deployment commands."""

import subprocess
from pathlib import Path

import click
from rich.console import Console

from vmctl.config.manager import ConfigManager
from vmctl.core.exceptions import VMError
from vmctl.core.vm import VMManager

console = Console()


def run_command(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr.

    Args:
        cmd: Command and arguments as list
        cwd: Working directory for command

    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"


def _get_vm_manager() -> tuple[VMManager, ConfigManager]:
    """Load config and create VM manager.

    Returns:
        Tuple of (VMManager, ConfigManager)

    Raises:
        click.Abort: If no configuration found
    """
    config_mgr = ConfigManager()
    if not config_mgr.config_exists():
        console.print("[red]No configuration found. Run 'vmctl config' first.[/red]")
        raise click.Abort()
    config = config_mgr.load()
    return VMManager(config), config_mgr


def _check_vm_running(vm: VMManager) -> None:
    """Check that VM exists and is running.

    Args:
        vm: VM manager instance

    Raises:
        click.Abort: If VM doesn't exist or isn't running
    """
    if not vm.exists():
        console.print(f"[red]VM {vm.config.vm_name} does not exist.[/red]")
        console.print("Create it first with: vmctl init-fresh")
        raise click.Abort()

    status = vm.status()
    if status != "RUNNING":
        console.print(f"[red]VM {vm.config.vm_name} is {status}.[/red]")
        console.print("Start it first with: vmctl start")
        raise click.Abort()


def _resolve_app_dir(app_dir: str | None, config_app_dir: str | None) -> str:
    """Resolve the target compose directory.

    Resolution order:
    1. Explicit --app-dir option
    2. Configured default app_dir on VM config

    Args:
        app_dir: Explicit app directory from --app-dir option
        config_app_dir: Default app directory from config

    Returns:
        Resolved app directory path

    Raises:
        click.Abort: If no app directory can be resolved
    """
    resolved = app_dir or config_app_dir
    if not resolved:
        console.print("[red]No app directory specified.[/red]")
        console.print("Either pass --app-dir or set app_dir in your vmctl config.")
        raise click.Abort()
    return resolved


# ============================================================================
# Local Docker Commands (existing)
# ============================================================================


@click.command()
@click.option(
    "--local",
    "mode",
    flag_value="local",
    default=True,
    help="Run locally with Docker (default)",
)
@click.option(
    "--cloud",
    "mode",
    flag_value="cloud",
    help="Deploy to Google Cloud with IAP authentication",
)
@click.option(
    "--user",
    help="Google account email for IAP authentication (cloud mode only)",
)
def up(mode: str, user: str | None) -> None:
    """Start code-server environment (local or cloud).

    Examples:
        vmctl up              # Start locally
        vmctl up --local      # Start locally (explicit)
        vmctl up --cloud --user you@gmail.com  # Deploy to cloud
    """
    if mode == "local":
        _up_local()
    elif mode == "cloud":
        if not user:
            console.print("[red]Error: --user required for cloud mode[/red]")
            console.print("Example: vmctl up --cloud --user you@gmail.com")
            raise click.Abort()
        _up_cloud(user)


@click.command()
@click.option(
    "--local",
    "mode",
    flag_value="local",
    default=True,
    help="Stop local Docker container (default)",
)
@click.option(
    "--cloud",
    "mode",
    flag_value="cloud",
    help="Stop cloud VM",
)
def down(mode: str) -> None:
    """Stop code-server environment (local or cloud).

    Examples:
        vmctl down            # Stop local
        vmctl down --local    # Stop local (explicit)
        vmctl down --cloud    # Stop cloud VM
    """
    if mode == "local":
        _down_local()
    elif mode == "cloud":
        _down_cloud()


def _up_local() -> None:
    """Start code-server locally with Docker Compose."""
    console.print("[bold cyan]Starting code-server locally...[/bold cyan]")

    # Find the project root (where docker-compose.yml lives)
    # This should be the vmctl repo root
    cwd = Path.cwd()
    compose_file = cwd / "docker-compose.yml"

    if not compose_file.exists():
        console.print(f"[red]Error: docker-compose.yml not found in {cwd}[/red]")
        console.print("Make sure you're running from the vmctl directory")
        raise click.Abort()

    # Run docker compose up -d
    exit_code, stdout, stderr = run_command(
        ["docker", "compose", "up", "-d"],
        cwd=cwd,
    )

    if exit_code != 0:
        console.print("[red]Failed to start code-server[/red]")
        if stderr:
            console.print(f"[red]{stderr}[/red]")
        raise click.Abort()

    # Wait a moment for container to start
    import time
    time.sleep(2)

    # Check if container is running
    exit_code, stdout, stderr = run_command(["docker", "ps", "--filter", "name=vmctl"])

    if "vmctl" in stdout:
        console.print("[green]✓[/green] code-server started successfully")
        console.print("[bold green]Access at: http://localhost:8080[/bold green]")
        console.print("\nTo stop: [cyan]vmctl down --local[/cyan]")
    else:
        console.print("[yellow]Warning: Container may not be running[/yellow]")
        console.print("Check logs with: docker logs vmctl")


def _down_local() -> None:
    """Stop local code-server Docker container."""
    console.print("[bold cyan]Stopping local code-server...[/bold cyan]")

    cwd = Path.cwd()
    compose_file = cwd / "docker-compose.yml"

    if not compose_file.exists():
        console.print(f"[red]Error: docker-compose.yml not found in {cwd}[/red]")
        raise click.Abort()

    exit_code, stdout, stderr = run_command(
        ["docker", "compose", "down"],
        cwd=cwd,
    )

    if exit_code != 0:
        console.print("[red]Failed to stop code-server[/red]")
        if stderr:
            console.print(f"[red]{stderr}[/red]")
        raise click.Abort()

    console.print("[green]✓[/green] code-server stopped")


def _up_cloud(user: str) -> None:
    """Deploy code-server to Google Cloud with IAP."""
    console.print(f"[bold cyan]Deploying to cloud for {user}...[/bold cyan]")
    console.print("[yellow]Cloud deployment not yet implemented[/yellow]")
    console.print("Coming in step 7!")
    # TODO: Implement in step 7


def _down_cloud() -> None:
    """Stop cloud VM."""
    console.print("[bold cyan]Stopping cloud VM...[/bold cyan]")
    console.print("[yellow]Cloud deployment not yet implemented[/yellow]")
    console.print("Coming in step 8!")
    # TODO: Implement in step 8


# ============================================================================
# Remote Docker Management Commands (Gate 2)
# ============================================================================


@click.command()
def provision() -> None:
    """Install Docker and set up base directories on the VM.

    This command provisions the remote VM with Docker and Docker Compose,
    preparing it to run containerized applications.

    Example:
        vmctl provision
    """
    try:
        vm, config_mgr = _get_vm_manager()
        _check_vm_running(vm)

        console.print(
            f"[bold cyan]Provisioning Docker on {vm.config.vm_name}...[/bold cyan]"
        )

        # Install Docker using the official convenience script
        # This works on Debian/Ubuntu-based systems
        provision_script = """
set -e

# Ensure curl/git exist (curl needed for Docker install; git for optional deploy sync)
if ! command -v curl >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y curl git
fi

# Check if Docker is already installed
if command -v docker >/dev/null 2>&1; then
    echo "Docker is already installed:"
    docker --version
else
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sudo sh
    echo "Docker installed successfully"
fi

# Add current user to docker group (won't take effect until next login)
sudo usermod -aG docker $USER

# Ensure Docker service is running
sudo systemctl enable docker
sudo systemctl start docker

# Create base directories for apps
sudo mkdir -p /opt/apps
sudo chown $USER:$USER /opt/apps

# Verify Docker is working (using sudo for fresh installs)
echo "Verifying Docker installation..."
sudo docker --version
sudo docker compose version

echo "Provisioning complete!"
"""

        success, stdout, stderr = vm.ssh_exec(provision_script)

        if success:
            console.print("[green]✓ Docker provisioned successfully[/green]")
            if stdout:
                console.print(f"[dim]{stdout}[/dim]")
            console.print("\n[yellow]Note:[/yellow] Log out and back in for docker "
                         "group membership to take effect.")
            console.print("Until then, commands use sudo automatically.")
        else:
            console.print("[red]Failed to provision Docker[/red]")
            if stderr:
                console.print(f"[red]{stderr}[/red]")
            raise click.Abort()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


@click.command()
@click.option(
    "--app-dir",
    help="Remote directory containing docker-compose.yml",
)
def deploy(app_dir: str | None) -> None:
    """Deploy application using docker compose up on the VM.

    Runs 'docker compose up -d --build' in the specified app directory.
    Uses sudo for Docker commands to ensure they work on fresh VMs.

    Resolution order for app directory:
    1. --app-dir option (explicit)
    2. app_dir from vmctl config (default)

    Examples:
        vmctl deploy                          # Use configured app_dir
        vmctl deploy --app-dir /opt/apps/myapp  # Explicit directory
    """
    try:
        vm, config_mgr = _get_vm_manager()
        _check_vm_running(vm)

        resolved_dir = _resolve_app_dir(app_dir, vm.config.app_dir)

        console.print(
            f"[bold cyan]Deploying app in {resolved_dir} on "
            f"{vm.config.vm_name}...[/bold cyan]"
        )

        # Run docker compose up with sudo for fresh VM compatibility
        deploy_cmd = f"""
set -e
cd "{resolved_dir}"

# Optional app-provided deploy hook (app-owned behavior)
if [ -f ./deploy.sh ]; then
    echo "Running pre-deploy hook: ./deploy.sh"
    bash ./deploy.sh
elif [ -d .git ]; then
    echo "Updating git checkout (ff-only)..."
    git pull --ff-only
else
    echo "No deploy.sh or .git found; skipping source update."
fi

# Check for any valid compose file
if [ ! -f docker-compose.yml ] && [ ! -f docker-compose.yaml ] && \
   [ ! -f compose.yml ] && [ ! -f compose.yaml ]; then
    echo "Error: No compose file found in {resolved_dir}"
    exit 1
fi

echo "Running docker compose up -d --build..."
sudo docker compose up -d --build

echo "Deployment complete. Running containers:"
sudo docker compose ps
"""

        success, stdout, stderr = vm.ssh_exec(deploy_cmd)

        if success:
            console.print("[green]✓ Application deployed successfully[/green]")
            if stdout:
                console.print(f"[dim]{stdout}[/dim]")
        else:
            console.print("[red]Failed to deploy application[/red]")
            if stderr:
                console.print(f"[red]{stderr}[/red]")
            raise click.Abort()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


@click.command(name="ps")
@click.option(
    "--app-dir",
    help="Remote directory containing docker-compose.yml",
)
@click.option(
    "--all",
    "-a",
    "show_all",
    is_flag=True,
    help="Show all containers (including stopped)",
)
def docker_ps(app_dir: str | None, show_all: bool) -> None:
    """Show Docker container status on the VM.

    Resolution order for app directory:
    1. --app-dir option (explicit)
    2. app_dir from vmctl config (default)

    Examples:
        vmctl ps                    # Show containers for configured app
        vmctl ps --all              # Include stopped containers
        vmctl ps --app-dir /opt/apps/myapp  # Specific directory
    """
    try:
        vm, config_mgr = _get_vm_manager()
        _check_vm_running(vm)

        resolved_dir = _resolve_app_dir(app_dir, vm.config.app_dir)

        console.print(
            f"[bold cyan]Container status in {resolved_dir}...[/bold cyan]"
        )

        all_flag = "-a" if show_all else ""
        ps_cmd = f"""
    cd "{resolved_dir}"
sudo docker compose ps {all_flag}
"""

        success, stdout, stderr = vm.ssh_exec(ps_cmd)

        if success:
            if stdout:
                console.print(stdout)
            else:
                console.print("[dim]No containers found[/dim]")
        else:
            console.print("[red]Failed to get container status[/red]")
            if stderr:
                console.print(f"[red]{stderr}[/red]")
            raise click.Abort()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


@click.command(name="logs")
@click.option(
    "--app-dir",
    help="Remote directory containing docker-compose.yml",
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output (Ctrl+C to stop)",
)
@click.option(
    "--tail",
    "-n",
    default=100,
    help="Number of lines to show from end of logs (default: 100)",
)
@click.argument("service", required=False)
def docker_logs(
    app_dir: str | None, follow: bool, tail: int, service: str | None
) -> None:
    """Show Docker compose logs from the VM.

    Resolution order for app directory:
    1. --app-dir option (explicit)
    2. app_dir from vmctl config (default)

    Examples:
        vmctl logs                  # Show logs for all services
        vmctl logs web              # Show logs for 'web' service
        vmctl logs -f               # Follow log output
        vmctl logs --tail 50        # Show last 50 lines
        vmctl logs --app-dir /opt/apps/myapp web  # Specific app and service
    """
    try:
        vm, config_mgr = _get_vm_manager()
        _check_vm_running(vm)

        resolved_dir = _resolve_app_dir(app_dir, vm.config.app_dir)

        service_str = service or ""
        follow_flag = "-f" if follow else ""

        console.print(
            f"[bold cyan]Logs from {resolved_dir}...[/bold cyan]"
        )

        logs_cmd = f"""
    cd "{resolved_dir}"
sudo docker compose logs {follow_flag} --tail {tail} {service_str}
"""

        success, stdout, stderr = vm.ssh_exec(logs_cmd)

        if success:
            if stdout:
                console.print(stdout)
            else:
                console.print("[dim]No logs found[/dim]")
        else:
            # Follow mode may exit with non-zero on Ctrl+C, which is expected
            if follow:
                console.print("\n[dim]Log streaming stopped[/dim]")
            else:
                console.print("[red]Failed to get logs[/red]")
                if stderr:
                    console.print(f"[red]{stderr}[/red]")
                raise click.Abort()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None
    except KeyboardInterrupt:
        console.print("\n[dim]Log streaming stopped[/dim]")


@click.command()
@click.option(
    "--app-dir",
    help="Remote directory containing docker-compose.yml",
)
@click.argument("service", required=False)
def restart(app_dir: str | None, service: str | None) -> None:
    """Restart Docker compose services on the VM.

    Resolution order for app directory:
    1. --app-dir option (explicit)
    2. app_dir from vmctl config (default)

    Examples:
        vmctl restart               # Restart all services
        vmctl restart web           # Restart 'web' service only
        vmctl restart --app-dir /opt/apps/myapp  # Specific directory
    """
    try:
        vm, config_mgr = _get_vm_manager()
        _check_vm_running(vm)

        resolved_dir = _resolve_app_dir(app_dir, vm.config.app_dir)

        service_str = service or ""
        service_msg = f" service '{service}'" if service else " all services"

        console.print(
            f"[bold cyan]Restarting{service_msg} in {resolved_dir} on "
            f"{vm.config.vm_name}...[/bold cyan]"
        )

        restart_cmd = f"""
    cd "{resolved_dir}"
sudo docker compose restart {service_str}
echo "Restart complete. Current status:"
sudo docker compose ps
"""

        success, stdout, stderr = vm.ssh_exec(restart_cmd)

        if success:
            console.print(f"[green]✓ Restarted{service_msg} successfully[/green]")
            if stdout:
                console.print(f"[dim]{stdout}[/dim]")
        else:
            console.print("[red]Failed to restart services[/red]")
            if stderr:
                console.print(f"[red]{stderr}[/red]")
            raise click.Abort()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None
