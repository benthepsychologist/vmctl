"""Configuration migration utilities for Codestation.

Handles automatic migration from legacy ~/.vmws/ to new ~/.codestation/ directory.
"""

import shutil
from pathlib import Path

from rich.console import Console

console = Console()


class ConfigMigration:
    """Handles config directory migration from ~/.vmws to ~/.codestation."""

    def __init__(self) -> None:
        """Initialize migration manager."""
        self.old_dir = Path.home() / ".vmws"
        self.new_dir = Path.home() / ".codestation"
        self.migration_marker = self.new_dir / ".migrated"

    def needs_migration(self) -> bool:
        """Check if migration is needed.

        Returns:
            True if old config exists and new config doesn't, or migration incomplete
        """
        # If new dir doesn't exist and old dir exists, we need migration
        if not self.new_dir.exists() and self.old_dir.exists():
            return True

        # If new dir exists but no migration marker, and old dir exists
        if self.new_dir.exists() and not self.migration_marker.exists() and self.old_dir.exists():
            return True

        return False

    def migrate(self) -> bool:
        """Migrate config from ~/.vmws to ~/.codestation.

        Returns:
            True if migration was performed, False if not needed
        """
        if not self.needs_migration():
            return False

        console.print("\n[cyan]Migrating configuration from ~/.vmws to ~/.codestation...[/cyan]")

        try:
            # Create new directory if it doesn't exist
            self.new_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files from old directory
            if self.old_dir.exists():
                for item in self.old_dir.iterdir():
                    src = item
                    dst = self.new_dir / item.name

                    if src.is_file():
                        shutil.copy2(src, dst)
                        console.print(f"  [dim]Copied {item.name}[/dim]")
                    elif src.is_dir():
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                        console.print(f"  [dim]Copied {item.name}/[/dim]")

            # Create migration marker
            self.migration_marker.write_text(
                "Configuration migrated from ~/.vmws\n"
                "Original directory preserved for rollback\n"
            )

            console.print("[green]✓ Migration complete![/green]")
            console.print("[dim]Your original ~/.vmws directory has been preserved.[/dim]\n")

            return True

        except Exception as e:
            console.print(f"[red]Migration failed: {e}[/red]")
            console.print("[yellow]Continuing with legacy ~/.vmws configuration[/yellow]\n")
            return False

    def is_migrated(self) -> bool:
        """Check if migration has been completed.

        Returns:
            True if migration marker exists
        """
        return self.migration_marker.exists()
