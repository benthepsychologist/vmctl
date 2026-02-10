"""Docker-based local and cloud deployment commands."""

import subprocess
from pathlib import Path

import click
from rich.console import Console
from rich.markup import escape

from vmctl.config.manager import ConfigManager
from vmctl.core.exceptions import VMError
from vmctl.core.vm import VMManager

console = Console()

# Default apps to deploy in order (dependencies first)
DEFAULT_APPS = ["openclaw-gateway", "workstation"]

# Base directory for vmctl on the VM
VM_BASE_DIR = "/srv/vmctl"


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

    For direct SSH mode, performs a connectivity check instead of
    querying GCE instance status.

    Args:
        vm: VM manager instance

    Raises:
        click.Abort: If VM doesn't exist or isn't running
    """
    if vm.use_direct_ssh:
        success, _, stderr = vm.ssh_exec("echo ok")
        if not success:
            console.print(
                f"[red]Cannot connect to {vm.config.ssh_host} via SSH.[/red]"
            )
            if stderr:
                console.print(f"[dim]{escape(stderr)}[/dim]")
            raise click.Abort()
        return

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
            console.print(f"[red]{escape(stderr)}[/red]")
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
            console.print(f"[red]{escape(stderr)}[/red]")
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
                console.print(f"[dim]{escape(stdout)}[/dim]")
            console.print("\n[yellow]Note:[/yellow] Log out and back in for docker "
                         "group membership to take effect.")
            console.print("Until then, commands use sudo automatically.")
        else:
            console.print("[red]Failed to provision Docker[/red]")
            if stderr:
                console.print(f"[red]{escape(stderr)}[/red]")
            raise click.Abort()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


def _build_deploy_script(app_dir: str) -> str:
    """Build the shell script for deploying a compose app.

    This is the single source of truth for deploy logic, used by both
    the ``deploy`` CLI command and the ``setup`` multi-app orchestrator.

    Args:
        app_dir: Remote directory containing the compose file

    Returns:
        Shell script string
    """
    return f"""
set -e
cd "{app_dir}"

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
if [ ! -f docker-compose.yml ] && [ ! -f docker-compose.yaml ] && \\
   [ ! -f compose.yml ] && [ ! -f compose.yaml ]; then
    echo "Error: No compose file found in {app_dir}"
    exit 1
fi

echo "Running docker compose up -d --build..."
sudo docker compose up -d --build

echo "Deployment complete. Running containers:"
sudo docker compose ps
"""


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

        success, stdout, stderr = vm.ssh_exec(_build_deploy_script(resolved_dir))

        if success:
            console.print("[green]✓ Application deployed successfully[/green]")
            if stdout:
                console.print(f"[dim]{escape(stdout)}[/dim]")
        else:
            console.print("[red]Failed to deploy application[/red]")
            if stderr:
                console.print(f"[red]{escape(stderr)}[/red]")
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
                console.print(f"[red]{escape(stderr)}[/red]")
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
                    console.print(f"[red]{escape(stderr)}[/red]")
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
                console.print(f"[dim]{escape(stdout)}[/dim]")
        else:
            console.print("[red]Failed to restart services[/red]")
            if stderr:
                console.print(f"[red]{escape(stderr)}[/red]")
            raise click.Abort()

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


# ============================================================================
# Multi-App Setup Command (Gate 5)
# ============================================================================


def _find_local_apps_dir() -> Path:
    """Find the local apps directory.

    Searches in order:
    1. Repository root relative to this source file (development / editable install)
    2. Current working directory (fallback)

    Returns:
        Path to apps directory

    Raises:
        click.Abort: If apps directory not found
    """
    searched: list[Path] = []

    # Walk up from this source file to find the repo root (has pyproject.toml or .git)
    anchor = Path(__file__).resolve().parent
    for parent in [anchor, *anchor.parents]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            repo_apps = parent / "apps"
            searched.append(repo_apps)
            if repo_apps.exists() and repo_apps.is_dir():
                return repo_apps
            break  # found repo root but no apps/ — stop climbing

    # Try current working directory (for running outside the repo tree)
    cwd_apps = Path.cwd() / "apps"
    if cwd_apps not in searched:
        searched.append(cwd_apps)
    if cwd_apps.exists() and cwd_apps.is_dir():
        return cwd_apps

    console.print("[red]Error: apps directory not found.[/red]")
    console.print("Searched in:")
    for p in searched:
        console.print(f"  - {p}")
    console.print("\nHint: pass --apps-dir to specify the apps directory explicitly.")
    raise click.Abort()


def _setup_molt_directories(vm: VMManager) -> bool:
    """Pre-create required openclaw-gateway agent directories on VM.

    Creates the directory structure that openclaw-gateway expects:
    /srv/vmctl/agent/openclaw-gateway/{repo,outbox,state,secrets}

    Args:
        vm: VM manager instance

    Returns:
        True if successful, False otherwise
    """

    mkdir_script = f"""
set -e
sudo mkdir -p {VM_BASE_DIR}/agent/openclaw-gateway/repo
sudo mkdir -p {VM_BASE_DIR}/agent/openclaw-gateway/outbox
sudo mkdir -p {VM_BASE_DIR}/agent/openclaw-gateway/state
sudo mkdir -p {VM_BASE_DIR}/agent/openclaw-gateway/secrets
sudo mkdir -p {VM_BASE_DIR}/apps

# Create placeholder agent.env if it doesn't exist (required by openclaw-gateway deploy.sh)
if [ ! -f {VM_BASE_DIR}/agent/openclaw-gateway/secrets/agent.env ]; then
    sudo touch {VM_BASE_DIR}/agent/openclaw-gateway/secrets/agent.env
    sudo chmod 600 {VM_BASE_DIR}/agent/openclaw-gateway/secrets/agent.env
fi

# Set ownership to current user for app deployment
sudo chown -R $USER:$USER {VM_BASE_DIR}

# Make state and outbox world-writable for container access
# (Container runs as root, host directories owned by $USER)
# Use -R to fix any subdirectories created by previous container runs
sudo chmod -R 777 {VM_BASE_DIR}/agent/openclaw-gateway/outbox
sudo chmod -R 777 {VM_BASE_DIR}/agent/openclaw-gateway/state

echo "Agent directories created:"
ls -la {VM_BASE_DIR}/agent/openclaw-gateway/
"""

    success, stdout, stderr = vm.ssh_exec(mkdir_script)

    if success:
        console.print("[green]✓ Agent directories created[/green]")
        if stdout:
            console.print(f"[dim]{escape(stdout)}[/dim]")
    else:
        console.print("[red]Failed to create agent directories[/red]")
        if stderr:
            console.print(f"[red]{escape(stderr)}[/red]")

    return success


def _sync_app(vm: VMManager, local_apps_dir: Path, app_name: str) -> bool:
    """Sync a single app directory to the VM.

    Args:
        vm: VM manager instance
        local_apps_dir: Path to local apps directory
        app_name: Name of the app to sync

    Returns:
        True if successful, False otherwise
    """
    local_app_path = local_apps_dir / app_name
    if not local_app_path.exists():
        console.print(f"[red]App directory not found: {local_app_path}[/red]")
        return False

    remote_app_path = f"{VM_BASE_DIR}/apps/{app_name}"
    remote_apps_parent = f"{VM_BASE_DIR}/apps"

    console.print(f"[bold cyan]Syncing {app_name}...[/bold cyan]")

    # Ensure the parent apps directory exists
    success, _, stderr = vm.ssh_exec(f"mkdir -p {remote_apps_parent}")
    if not success:
        console.print(f"[red]Failed to create remote directory: {escape(stderr)}[/red]")
        return False

    # Remove old app dir to avoid scp double-nesting (scp -r copies dir INTO
    # an existing target, creating target/dir/... instead of replacing contents)
    vm.ssh_exec(f"rm -rf {remote_app_path}")

    # Copy the app directory into the parent; scp creates app_name/ from the basename
    success, stdout, stderr = vm.scp(
        str(local_app_path), remote_apps_parent, recursive=True
    )

    if success:
        console.print(f"[green]✓ {app_name} synced to {remote_app_path}[/green]")
    else:
        console.print(f"[red]Failed to sync {app_name}[/red]")
        if stderr:
            console.print(f"[red]{escape(stderr)}[/red]")

    return success


def _deploy_app(vm: VMManager, app_name: str) -> bool:
    """Deploy a single app on the VM using the shared deploy logic.

    Args:
        vm: VM manager instance
        app_name: Name of the app to deploy

    Returns:
        True if successful, False otherwise
    """
    remote_app_path = f"{VM_BASE_DIR}/apps/{app_name}"

    console.print(f"[bold cyan]Deploying {app_name}...[/bold cyan]")

    success, stdout, stderr = vm.ssh_exec(_build_deploy_script(remote_app_path))

    if success:
        console.print(f"[green]✓ {app_name} deployed successfully[/green]")
        if stdout:
            console.print(f"[dim]{escape(stdout)}[/dim]")
    else:
        console.print(f"[red]Failed to deploy {app_name}[/red]")
        if stderr:
            console.print(f"[red]{escape(stderr)}[/red]")

    return success


def _sync_gateway_repo(vm: VMManager, local_repo_path: Path) -> bool:
    """Sync openclaw-gateway repo to VM for container build context.

    The gateway container builds from source code in
    /srv/vmctl/agent/openclaw-gateway/repo. This function syncs the local
    openclaw-gateway repository to that location.

    Args:
        vm: VM manager instance
        local_repo_path: Path to local openclaw-gateway repo

    Returns:
        True if successful, False otherwise
    """
    remote_repo_path = f"{VM_BASE_DIR}/agent/openclaw-gateway/repo"

    console.print("[bold cyan]Syncing openclaw-gateway repo...[/bold cyan]")

    # Remove old repo contents to avoid scp nesting issues
    vm.ssh_exec(f"rm -rf {remote_repo_path}/*")

    # Copy repo contents to the remote repo directory
    # Important: scp copies directory INTO target, so we need to copy to parent
    # and let the directory name become part of the target path
    # e.g., scp /workspace/openclaw-gateway /srv/vmctl/agent/openclaw-gateway/
    # creates /srv/vmctl/agent/openclaw-gateway/openclaw-gateway/
    # But we want files directly in repo/, so we rename after copy
    repo_name = local_repo_path.name  # e.g., "openclaw-gateway"
    parent_path = f"{VM_BASE_DIR}/agent/openclaw-gateway"
    success, stdout, stderr = vm.scp(str(local_repo_path), parent_path, recursive=True)

    if success:
        # Move contents from nested dir to repo/ and remove the nested dir
        vm.ssh_exec(f"rm -rf {remote_repo_path}/* && mv {parent_path}/{repo_name}/* {remote_repo_path}/ && rm -rf {parent_path}/{repo_name}")

    if success:
        console.print("[green]✓ openclaw-gateway repo synced[/green]")
    else:
        console.print("[red]Failed to sync openclaw-gateway repo[/red]")
        if stderr:
            console.print(f"[red]{escape(stderr)}[/red]")

    return success


def _check_agent_secrets(vm: VMManager) -> None:
    """Warn if agent.env is empty or missing.

    This is a non-blocking check that prints a warning if the secrets
    file is missing or empty. The container will still start but services
    may fail to authenticate.

    Args:
        vm: VM manager instance
    """
    check_script = f"""
    SECRETS_FILE="{VM_BASE_DIR}/agent/openclaw-gateway/secrets/agent.env"
    if [ ! -f "$SECRETS_FILE" ]; then
        echo "MISSING"
    elif [ ! -s "$SECRETS_FILE" ]; then
        echo "EMPTY"
    else
        echo "OK"
    fi
    """
    success, stdout, _ = vm.ssh_exec(check_script)
    if success:
        status = stdout.strip()
        if status == "MISSING":
            console.print(
                "[yellow]⚠ agent.env not found - "
                "openclaw-gateway services may fail to authenticate[/yellow]"
            )
        elif status == "EMPTY":
            console.print(
                "[yellow]⚠ agent.env is empty - "
                "populate with Discord/Telegram tokens and API keys[/yellow]"
            )


def _grant_bigquery_permissions(project: str, vm_name: str, zone: str) -> bool:
    """Grant BigQuery permissions to the VM's compute service account.

    Attempts to grant roles/bigquery.dataEditor and roles/bigquery.jobUser
    to the default compute service account. This requires the caller
    (gcloud authenticated user) to have IAM admin permissions.

    Args:
        project: GCP project ID
        vm_name: VM instance name
        zone: VM zone

    Returns:
        True if permissions were granted successfully, False otherwise
    """
    import subprocess

    console.print("[bold cyan]Checking BigQuery permissions...[/bold cyan]")

    # Get the VM's service account
    try:
        result = subprocess.run(
            [
                "gcloud", "compute", "instances", "describe", vm_name,
                f"--zone={zone}", f"--project={project}",
                "--format=value(serviceAccounts[0].email)"
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        sa_email = result.stdout.strip()
        if not sa_email:
            console.print("[yellow]⚠ Could not determine VM service account[/yellow]")
            return False

        console.print(f"[dim]VM service account: {sa_email}[/dim]")
    except subprocess.CalledProcessError as e:
        console.print(f"[yellow]⚠ Could not get VM info: {e.stderr}[/yellow]")
        return False

    # Try to grant BigQuery permissions
    roles = ["roles/bigquery.dataEditor", "roles/bigquery.jobUser"]
    all_granted = True

    for role in roles:
        try:
            result = subprocess.run(
                [
                    "gcloud", "projects", "add-iam-policy-binding", project,
                    f"--member=serviceAccount:{sa_email}",
                    f"--role={role}",
                    "--quiet",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            console.print(f"[green]✓ Granted {role}[/green]")
        except subprocess.CalledProcessError as e:
            all_granted = False
            if "does not have permission" in e.stderr or "403" in e.stderr:
                console.print(f"[yellow]⚠ Cannot grant {role} - need IAM admin access[/yellow]")
            else:
                console.print(f"[yellow]⚠ Failed to grant {role}: {e.stderr.strip()}[/yellow]")

    if not all_granted:
        console.print("\n[yellow]BigQuery permissions could not be granted automatically.[/yellow]")
        console.print("Run these commands as a project owner:\n")
        console.print(f"  gcloud projects add-iam-policy-binding {project} \\")
        console.print(f"    --member='serviceAccount:{sa_email}' \\")
        console.print(f"    --role='roles/bigquery.dataEditor'\n")
        console.print(f"  gcloud projects add-iam-policy-binding {project} \\")
        console.print(f"    --member='serviceAccount:{sa_email}' \\")
        console.print(f"    --role='roles/bigquery.jobUser'\n")

    return all_granted


@click.command()
@click.option(
    "--apps",
    help="Comma-separated list of apps to deploy (default: openclaw-gateway,workstation)",
)
@click.option(
    "--apps-dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to local apps directory (auto-detected if omitted)",
)
@click.option(
    "--skip-provision",
    is_flag=True,
    help="Skip Docker provisioning (assumes Docker is already installed)",
)
@click.option(
    "--gateway-repo",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to local openclaw-gateway repo to sync (default: /workspace/openclaw-gateway)",
)
def setup(
    apps: str | None,
    apps_dir: str | None,
    skip_provision: bool,
    gateway_repo: str | None,
) -> None:
    """Set up the VM with multiple apps in one operation.

    This command orchestrates the full deployment of multiple apps:
    1. Optionally provisions Docker on the VM
    2. Creates required agent directories
    3. Syncs app directories from local to VM via scp
    4. Deploys apps in dependency order

    Apps are deployed to /srv/vmctl/apps/{app-name}/ on the VM.
    Agent directories are created at /srv/vmctl/agent/openclaw-gateway/.

    Examples:
        vmctl setup                           # Deploy default apps
        vmctl setup --apps openclaw-gateway   # Deploy specific app
        vmctl setup --skip-provision          # Skip Docker install
        vmctl setup --apps-dir /path/to/apps  # Explicit apps directory
    """
    try:
        vm, _ = _get_vm_manager()
        _check_vm_running(vm)

        # Parse apps list, dropping empty entries from trailing commas
        if apps:
            app_list = [a.strip() for a in apps.split(",") if a.strip()]
        else:
            app_list = DEFAULT_APPS

        console.print(
            f"[bold cyan]Setting up VM {vm.config.vm_name} with apps: "
            f"{', '.join(app_list)}[/bold cyan]"
        )

        # Find local apps directory
        local_apps_dir = Path(apps_dir) if apps_dir else _find_local_apps_dir()
        console.print(f"[dim]Using local apps from: {local_apps_dir}[/dim]")

        # Validate all apps exist locally before starting
        for app_name in app_list:
            app_path = local_apps_dir / app_name
            if not app_path.exists():
                console.print(
                    f"[red]Error: App '{app_name}' not found at {app_path}[/red]"
                )
                raise click.Abort()

        # Step 1: Provision Docker if not skipped
        if not skip_provision:
            console.print("\n[bold]Step 1: Provisioning Docker...[/bold]")
            # Check if Docker is already installed
            check_result, stdout, _ = vm.ssh_exec("command -v docker")
            if check_result and stdout.strip():
                console.print("[green]✓ Docker already installed[/green]")
            else:
                # Run provision
                provision_script = """
set -e

# Ensure curl/git exist
if ! command -v curl >/dev/null 2>&1 || ! command -v git >/dev/null 2>&1; then
    sudo apt-get update -y
    sudo apt-get install -y curl git
fi

# Install Docker
echo "Installing Docker..."
curl -fsSL https://get.docker.com | sudo sh
echo "Docker installed successfully"

# Add current user to docker group
sudo usermod -aG docker $USER

# Ensure Docker service is running
sudo systemctl enable docker
sudo systemctl start docker

# Verify Docker is working
echo "Verifying Docker installation..."
sudo docker --version
sudo docker compose version

echo "Provisioning complete!"
"""
                success, stdout, stderr = vm.ssh_exec(provision_script)
                if not success:
                    console.print("[red]Failed to provision Docker[/red]")
                    if stderr:
                        console.print(f"[red]{escape(stderr)}[/red]")
                    raise click.Abort()
                console.print("[green]✓ Docker provisioned[/green]")
        else:
            console.print("\n[bold]Step 1: Skipping Docker provisioning[/bold]")

        # Step 2: Create agent directories
        console.print("\n[bold]Step 2: Creating agent directories...[/bold]")
        if not _setup_molt_directories(vm):
            raise click.Abort()

        # Step 3: Sync openclaw-gateway repo if deploying openclaw-gateway
        step_offset = 2
        if "openclaw-gateway" in app_list:
            step_offset = 3
            console.print("\n[bold]Step 3: Syncing openclaw-gateway repo...[/bold]")
            repo_path = Path(gateway_repo) if gateway_repo else Path("/workspace/openclaw-gateway")
            if repo_path.exists():
                if not _sync_gateway_repo(vm, repo_path):
                    raise click.Abort()
            else:
                console.print(
                    f"[yellow]⚠ openclaw-gateway repo not found at {repo_path}[/yellow]"
                )
                console.print(
                    "[yellow]Container build may fail - no Dockerfile in build context[/yellow]"
                )

        # Step 4+: Sync and deploy each app in order
        for i, app_name in enumerate(app_list, start=1):
            console.print(f"\n[bold]Step {step_offset + i}a: Syncing {app_name}...[/bold]")
            if not _sync_app(vm, local_apps_dir, app_name):
                raise click.Abort()

            console.print(f"\n[bold]Step {step_offset + i}b: Deploying {app_name}...[/bold]")
            if not _deploy_app(vm, app_name):
                raise click.Abort()

            # Check secrets and permissions after deploying openclaw-gateway
            if app_name == "openclaw-gateway":
                _check_agent_secrets(vm)
                # Try to grant BigQuery permissions (non-blocking)
                if vm.config.project:
                    _grant_bigquery_permissions(
                        vm.config.project, vm.config.vm_name, vm.config.zone
                    )

        # Final status
        console.print("\n" + "=" * 60)
        console.print("[bold green]✓ Setup complete![/bold green]")
        console.print(f"Apps deployed to: {VM_BASE_DIR}/apps/")
        console.print(f"Agent directories: {VM_BASE_DIR}/agent/openclaw-gateway/")

        # Warn about agent.env configuration if openclaw-gateway was deployed
        if "openclaw-gateway" in app_list:
            console.print(
                "\n[yellow]Note:[/yellow] Configure secrets before using openclaw-gateway:"
            )
            console.print(
                "  vmctl secrets -s AZURE_OPENAI_API_KEY=... -s AZURE_OPENAI_HOST=..."
            )
            console.print("  vmctl secrets --list        # View current secrets")
            console.print("  vmctl secrets --edit        # Edit interactively")

        console.print("\nUseful commands:")
        for app_name in app_list:
            remote_path = f"{VM_BASE_DIR}/apps/{app_name}"
            console.print(f"  vmctl ps --app-dir {remote_path}")
        console.print("=" * 60)

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None


# ============================================================================
# Secrets Management Command
# ============================================================================


@click.command()
@click.option(
    "--set",
    "-s",
    "secrets_to_set",
    multiple=True,
    metavar="KEY=VALUE",
    help="Set a secret (can be used multiple times). Example: -s AZURE_OPENAI_API_KEY=abc123",
)
@click.option(
    "--list",
    "-l",
    "list_secrets",
    is_flag=True,
    help="List currently set secret keys (values hidden)",
)
@click.option(
    "--edit",
    "-e",
    "edit_secrets",
    is_flag=True,
    help="Open agent.env in an editor on the VM",
)
def secrets(
    secrets_to_set: tuple[str, ...],
    list_secrets: bool,
    edit_secrets: bool,
) -> None:
    """Manage openclaw-gateway secrets (agent.env).

    Examples:

        # Set Azure OpenAI credentials
        vmctl secrets -s AZURE_OPENAI_API_KEY=your-key -s AZURE_OPENAI_HOST=your-resource.openai.azure.com

        # List current secrets (keys only)
        vmctl secrets --list

        # Edit secrets interactively on VM
        vmctl secrets --edit
    """
    try:
        vm, _ = _get_vm_manager()
        _check_vm_running(vm)

        secrets_file = f"{VM_BASE_DIR}/agent/openclaw-gateway/secrets/agent.env"

        if list_secrets:
            # List secret keys (not values)
            console.print(f"[bold cyan]Secrets in {secrets_file}:[/bold cyan]")
            list_cmd = f"""
if [ -f "{secrets_file}" ]; then
    grep -E '^[A-Z_]+=' "{secrets_file}" 2>/dev/null | cut -d= -f1 | sort
else
    echo "(file not found)"
fi
"""
            success, stdout, stderr = vm.ssh_exec(list_cmd)
            if success and stdout.strip():
                for key in stdout.strip().split("\n"):
                    if key and key != "(file not found)":
                        console.print(f"  {key}=***")
                    elif key == "(file not found)":
                        console.print("[yellow]  (no secrets file found)[/yellow]")
            else:
                console.print("[yellow]  (no secrets set)[/yellow]")
            return

        if edit_secrets:
            # Open editor on VM - this requires interactive SSH
            console.print(f"[bold cyan]Opening {secrets_file} for editing...[/bold cyan]")
            console.print("[dim]Use Ctrl+X to save and exit nano[/dim]")

            # Use interactive SSH for editing
            import subprocess as sp

            if vm.use_direct_ssh:
                ssh_cmd = [
                    "ssh",
                    "-t",  # Force TTY allocation
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-i", vm.config.ssh_key,
                    f"{vm.config.ssh_user}@{vm.config.ssh_host}",
                    f"sudo nano {secrets_file}",
                ]
            else:
                ssh_cmd = [
                    "gcloud", "compute", "ssh",
                    vm.config.vm_name,
                    f"--zone={vm.config.zone}",
                    f"--project={vm.config.project}",
                    "--",
                    f"sudo nano {secrets_file}",
                ]

            sp.run(ssh_cmd, check=False)
            console.print("[green]✓ Done editing secrets[/green]")
            console.print(
                "\n[yellow]Restart openclaw-gateway to apply changes:[/yellow]"
            )
            console.print("  vmctl restart --app-dir /srv/vmctl/apps/openclaw-gateway")
            return

        if secrets_to_set:
            # Validate and set secrets
            parsed_secrets: list[tuple[str, str]] = []
            for secret in secrets_to_set:
                if "=" not in secret:
                    console.print(
                        f"[red]Invalid secret format: {secret}[/red]"
                    )
                    console.print("Expected format: KEY=VALUE")
                    raise click.Abort()
                key, value = secret.split("=", 1)
                if not key:
                    console.print("[red]Secret key cannot be empty[/red]")
                    raise click.Abort()
                parsed_secrets.append((key, value))

            console.print(
                f"[bold cyan]Setting {len(parsed_secrets)} secret(s)...[/bold cyan]"
            )

            for key, value in parsed_secrets:
                # Use sed to update or append the secret
                # Escape special characters in value for sed
                escaped_value = value.replace("'", "'\"'\"'")
                set_cmd = f"""
SECRET_KEY="{key}"
SECRET_VALUE='{escaped_value}'
SECRETS_FILE="{secrets_file}"

# Create file if it doesn't exist
sudo touch "$SECRETS_FILE"
sudo chmod 600 "$SECRETS_FILE"

# Remove existing key if present (case-sensitive exact match)
sudo sed -i "/^$SECRET_KEY=/d" "$SECRETS_FILE"

# Append new value
echo "$SECRET_KEY=$SECRET_VALUE" | sudo tee -a "$SECRETS_FILE" > /dev/null

echo "Set $SECRET_KEY"
"""
                success, stdout, stderr = vm.ssh_exec(set_cmd)
                if success:
                    console.print(f"  [green]✓ {key}[/green]")
                else:
                    console.print(f"  [red]✗ {key}: {stderr}[/red]")
                    raise click.Abort()

            console.print("\n[green]✓ Secrets updated[/green]")
            console.print(
                "\n[yellow]Restart openclaw-gateway to apply changes:[/yellow]"
            )
            console.print("  vmctl restart --app-dir /srv/vmctl/apps/openclaw-gateway")
            return

        # No action specified - show help
        console.print("Usage: vmctl secrets [OPTIONS]")
        console.print("\nOptions:")
        console.print("  -s, --set KEY=VALUE  Set a secret (repeatable)")
        console.print("  -l, --list           List secret keys")
        console.print("  -e, --edit           Edit secrets interactively")
        console.print("\nExamples:")
        console.print(
            "  vmctl secrets -s AZURE_OPENAI_API_KEY=xxx -s AZURE_OPENAI_HOST=yyy"
        )
        console.print("  vmctl secrets --list")

    except VMError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort() from None
