"""Configuration migration utilities for vmctl.

Handles automatic migration from legacy ~/.vmws/ or ~/.codestation/ to ~/.vmctl/ directory.
"""

import shutil
from pathlib import Path

from rich.console import Console

console = Console()


class ConfigMigration:
    """Handles config directory migration to ~/.vmctl."""

    def __init__(self) -> None:
        """Initialize migration manager."""
        self.legacy_dirs = [
            Path.home() / ".vmws",
            Path.home() / ".codestation",
        ]
        self.new_dir = Path.home() / ".vmctl"
        self.migration_marker = self.new_dir / ".migrated"

    def _find_legacy_dir(self) -> Path | None:
        """Find the most recent legacy config directory.

        Returns:
            Path to legacy dir if found, None otherwise
        """
        # Prefer .codestation over .vmws (more recent)
        for legacy_dir in reversed(self.legacy_dirs):
            if legacy_dir.exists():
                return legacy_dir
        return None

    def needs_migration(self) -> bool:
        """Check if migration is needed.

        Returns:
            True if legacy config exists and new config doesn't, or migration incomplete
        """
        legacy_dir = self._find_legacy_dir()
        if legacy_dir is None:
            return False

        # If new dir doesn't exist and legacy dir exists, we need migration
        if not self.new_dir.exists():
            return True

        # If new dir exists but no migration marker, and legacy dir exists
        if not self.migration_marker.exists():
            return True

        return False

    def migrate(self) -> bool:
        """Migrate config from legacy directory to ~/.vmctl.

        Returns:
            True if migration was performed, False if not needed
        """
        if not self.needs_migration():
            return False

        legacy_dir = self._find_legacy_dir()
        if legacy_dir is None:
            return False

        console.print(f"\n[cyan]Migrating configuration from {legacy_dir} to ~/.vmctl...[/cyan]")

        try:
            # Create new directory if it doesn't exist
            self.new_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files from legacy directory
            for item in legacy_dir.iterdir():
                # Skip migration markers from previous migrations
                if item.name == ".migrated":
                    continue

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
                f"Configuration migrated from {legacy_dir}\n"
                "Original directory preserved for rollback\n"
            )

            console.print("[green]✓ Migration complete![/green]")
            console.print(f"[dim]Your original {legacy_dir} directory has been preserved.[/dim]\n")

            return True

        except Exception as e:
            console.print(f"[red]Migration failed: {e}[/red]")
            console.print(f"[yellow]Continuing with legacy {legacy_dir} configuration[/yellow]\n")
            return False

    def is_migrated(self) -> bool:
        """Check if migration has been completed.

        Returns:
            True if migration marker exists
        """
        return self.migration_marker.exists()
