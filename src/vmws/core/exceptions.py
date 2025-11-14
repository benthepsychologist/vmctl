"""Custom exceptions for VM Workstation Manager."""


class VMWSError(Exception):
    """Base exception for VMWS errors."""

    pass


class VMError(VMWSError):
    """VM operation errors."""

    pass


class ConfigError(VMWSError):
    """Configuration errors."""

    pass


class TunnelError(VMWSError):
    """Tunnel operation errors."""

    pass


class DiskError(VMWSError):
    """Disk operation errors."""

    pass


class GCloudError(VMWSError):
    """GCloud CLI errors."""

    pass
