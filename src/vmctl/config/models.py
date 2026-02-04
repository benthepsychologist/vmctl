"""Configuration models for vmctl."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class VMConfig(BaseModel):
    """VM configuration settings."""

    vm_name: str = Field(default="dev-workstation", description="Name of the VM instance")
    zone: str = Field(default="us-central1-a", description="Google Cloud zone")
    project: str | None = Field(default=None, description="Google Cloud project ID")
    workstation_disk: str | None = Field(
        default=None, description="Source workstation disk for migration"
    )
    region: str | None = Field(default=None, description="Google Cloud region")
    app_dir: str | None = Field(
        default=None, description="Remote compose directory for Docker commands"
    )

    @field_validator("vm_name")
    @classmethod
    def validate_vm_name(cls, v: str) -> str:
        """Validate VM name follows GCP naming rules."""
        if not v:
            raise ValueError("VM name cannot be empty")
        if not v[0].isalpha():
            raise ValueError("VM name must start with a letter")
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("VM name can only contain letters, numbers, and hyphens")
        if len(v) > 63:
            raise ValueError("VM name cannot exceed 63 characters")
        return v.lower()

    @field_validator("zone")
    @classmethod
    def validate_zone(cls, v: str) -> str:
        """Validate zone format."""
        if not v:
            raise ValueError("Zone cannot be empty")
        # Basic validation - zones are like us-central1-a
        parts = v.split("-")
        if len(parts) < 3:
            raise ValueError("Invalid zone format (expected: region-zone-letter)")
        return v

    def to_bash_format(self) -> str:
        """Convert config to bash source format for backward compatibility."""
        lines = [
            f'VM_NAME="{self.vm_name}"',
            f'ZONE="{self.zone}"',
            f'PROJECT="{self.project or ""}"',
            f'WORKSTATION_DISK="{self.workstation_disk or ""}"',
            f'REGION="{self.region or ""}"',
            f'APP_DIR="{self.app_dir or ""}"',
        ]
        return "\n".join(lines) + "\n"

    @classmethod
    def from_bash_format(cls, content: str) -> "VMConfig":
        """Parse bash source format config file."""
        # Initialize with None for all optional fields
        vm_name: str | None = None
        zone: str | None = None
        project: str | None = None
        workstation_disk: str | None = None
        region: str | None = None
        app_dir: str | None = None

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Parse bash variable assignment: VAR="value"
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                value_or_none = value if value else None

                # Map bash variable names to Python variables
                if key == "VM_NAME":
                    vm_name = value_or_none
                elif key == "ZONE":
                    zone = value_or_none
                elif key == "PROJECT":
                    project = value_or_none
                elif key == "WORKSTATION_DISK":
                    workstation_disk = value_or_none
                elif key == "REGION":
                    region = value_or_none
                elif key == "APP_DIR":
                    app_dir = value_or_none

        # Build config with explicit fields (use defaults if None)
        config_kwargs: dict[str, str | None] = {}
        if vm_name is not None:
            config_kwargs["vm_name"] = vm_name
        if zone is not None:
            config_kwargs["zone"] = zone
        if project is not None:
            config_kwargs["project"] = project
        if workstation_disk is not None:
            config_kwargs["workstation_disk"] = workstation_disk
        if region is not None:
            config_kwargs["region"] = region
        if app_dir is not None:
            config_kwargs["app_dir"] = app_dir

        return cls(**config_kwargs)  # type: ignore[arg-type]


class ConfigPaths:
    """Standard configuration paths."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize config paths.

        Args:
            config_dir: Override default config directory (~/.vmctl)
        """
        self.config_dir = config_dir or Path.home() / ".vmctl"
        self.config_file = self.config_dir / "config"

    def ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
