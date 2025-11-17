"""Backward compatibility shim for legacy 'vmws' command.

Provides the 'vmws' command as an alias to 'cstation' with a deprecation warning.
"""

import sys

from rich.console import Console

from codestation.cli.main import cli

console = Console()


def vmws_compat() -> None:
    """Legacy 'vmws' command entry point with deprecation warning.

    This function is registered as the 'vmws' entry point in pyproject.toml
    to maintain backward compatibility for users who have 'vmws' in their scripts.
    """
    # Show deprecation warning
    console.print(
        "\n[yellow]⚠ WARNING: The 'vmws' command is deprecated and will be removed in v4.0.0[/yellow]"
    )
    console.print("[yellow]Please use 'cstation' instead.[/yellow]\n")
    console.print("[dim]Update your scripts: vmws → cstation[/dim]")
    console.print("[dim]This compatibility alias will continue to work for now.[/dim]\n")

    # Forward to the main cstation CLI
    try:
        cli(prog_name="vmws")
    except SystemExit:
        # Let click handle its own exits
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
