"""Custom exceptions for Codestation."""


class CodestationError(Exception):
    """Base exception for Codestation errors."""

    pass


class VMError(CodestationError):
    """VM operation errors."""

    pass


class ConfigError(CodestationError):
    """Configuration errors."""

    pass


class TunnelError(CodestationError):
    """Tunnel operation errors."""

    pass


class DiskError(CodestationError):
    """Disk operation errors."""

    pass


class GCloudError(CodestationError):
    """GCloud CLI errors."""

    pass
