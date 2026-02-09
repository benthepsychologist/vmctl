"""Configuration manager for vmctl."""

import subprocess
from pathlib import Path

from vmctl.config.migration import ConfigMigration
from vmctl.config.models import ConfigPaths, VMConfig


class ConfigManager:
    """Manages vmctl configuration."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize configuration manager.

        Args:
            config_dir: Override default config directory (~/.vmctl)
        """
        self.paths = ConfigPaths(config_dir)
        self._config: VMConfig | None = None
        self._migration_checked = False

    def load(self) -> VMConfig:
        """Load configuration from file or create default.

        Automatically performs migration from ~/.vmws if needed.

        Returns:
            VMConfig instance with loaded or default values
        """
        # Run migration check once per manager instance
        if not self._migration_checked:
            migration = ConfigMigration()
            if migration.needs_migration():
                migration.migrate()
            self._migration_checked = True

        if self._config is not None:
            return self._config

        if self.paths.config_file.exists():
            content = self.paths.config_file.read_text()
            self._config = VMConfig.from_bash_format(content)
        else:
            # Create default config with project from gcloud if available
            project = self._get_gcloud_project()
            self._config = VMConfig(project=project)

        return self._config

    def save(self, config: VMConfig) -> None:
        """Save configuration to file.

        Args:
            config: VMConfig instance to save
        """
        self.paths.ensure_config_dir()
        self.paths.config_file.write_text(config.to_bash_format())
        self._config = config

    def update(
        self,
        vm_name: str | None = None,
        zone: str | None = None,
        project: str | None = None,
        workstation_disk: str | None = None,
        region: str | None = None,
        ssh_host: str | None = None,
        ssh_user: str | None = None,
        ssh_key: str | None = None,
        ssh_port: int | None = None,
    ) -> VMConfig:
        """Update configuration fields and save.

        Args:
            vm_name: VM instance name
            zone: Google Cloud zone
            project: Google Cloud project ID
            workstation_disk: Source workstation disk
            region: Google Cloud region
            ssh_host: Direct SSH hostname or IP
            ssh_user: SSH username for direct SSH
            ssh_key: Path to SSH identity file
            ssh_port: SSH port

        Returns:
            Updated VMConfig instance
        """
        current = self.load()

        # Only update fields that are provided
        updated_data = current.model_dump()
        if vm_name is not None:
            updated_data["vm_name"] = vm_name
        if zone is not None:
            updated_data["zone"] = zone
        if project is not None:
            updated_data["project"] = project
        if workstation_disk is not None:
            updated_data["workstation_disk"] = workstation_disk
        if region is not None:
            updated_data["region"] = region
        if ssh_host is not None:
            updated_data["ssh_host"] = ssh_host
        if ssh_user is not None:
            updated_data["ssh_user"] = ssh_user
        if ssh_key is not None:
            updated_data["ssh_key"] = ssh_key
        if ssh_port is not None:
            updated_data["ssh_port"] = ssh_port

        updated_config = VMConfig(**updated_data)
        self.save(updated_config)
        return updated_config

    def _get_gcloud_project(self) -> str | None:
        """Get default project from gcloud config.

        Returns:
            Project ID or None if gcloud not configured
        """
        try:
            result = subprocess.run(
                ["gcloud", "config", "get-value", "project"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            project = result.stdout.strip()
            # gcloud returns (unset) if no project configured
            return project if project and project != "(unset)" else None
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

    def get_config_path(self) -> Path:
        """Get path to config file.

        Returns:
            Path to config file
        """
        return self.paths.config_file

    def config_exists(self) -> bool:
        """Check if config file exists.

        Returns:
            True if config file exists
        """
        return self.paths.config_file.exists()
