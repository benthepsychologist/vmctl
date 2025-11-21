"""Docker-based local and cloud deployment commands."""

import subprocess
from pathlib import Path

import click
from rich.console import Console

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
        cstation up              # Start locally
        cstation up --local      # Start locally (explicit)
        cstation up --cloud --user you@gmail.com  # Deploy to cloud
    """
    if mode == "local":
        _up_local()
    elif mode == "cloud":
        if not user:
            console.print("[red]Error: --user required for cloud mode[/red]")
            console.print("Example: cstation up --cloud --user you@gmail.com")
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
        cstation down            # Stop local
        cstation down --local    # Stop local (explicit)
        cstation down --cloud    # Stop cloud VM
    """
    if mode == "local":
        _down_local()
    elif mode == "cloud":
        _down_cloud()


def _up_local() -> None:
    """Start code-server locally with Docker Compose."""
    console.print("[bold cyan]Starting code-server locally...[/bold cyan]")

    # Find the project root (where docker-compose.yml lives)
    # This should be the codestation repo root
    cwd = Path.cwd()
    compose_file = cwd / "docker-compose.yml"

    if not compose_file.exists():
        console.print(f"[red]Error: docker-compose.yml not found in {cwd}[/red]")
        console.print("Make sure you're running from the codestation directory")
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
    exit_code, stdout, stderr = run_command(["docker", "ps", "--filter", "name=codestation"])

    if "codestation" in stdout:
        console.print("[green]✓[/green] code-server started successfully")
        console.print(f"[bold green]🚀 Access at: http://localhost:8080[/bold green]")
        console.print("\nTo stop: [cyan]cstation down --local[/cyan]")
    else:
        console.print("[yellow]Warning: Container may not be running[/yellow]")
        console.print("Check logs with: docker logs codestation")


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
