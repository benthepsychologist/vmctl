"""Subprocess utility for running commands."""

import subprocess
from typing import Any

from vmws.core.exceptions import GCloudError


class CommandResult:
    """Result of a command execution."""

    def __init__(self, returncode: int, stdout: str, stderr: str) -> None:
        """Initialize command result.

        Args:
            returncode: Exit code of command
            stdout: Standard output
            stderr: Standard error
        """
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.success = returncode == 0

    def check(self) -> "CommandResult":
        """Raise exception if command failed.

        Returns:
            Self for chaining

        Raises:
            GCloudError: If command failed
        """
        if not self.success:
            raise GCloudError(
                f"Command failed with exit code {self.returncode}\n"
                f"STDOUT: {self.stdout}\n"
                f"STDERR: {self.stderr}"
            )
        return self


def run_command(
    cmd: list[str],
    check: bool = False,
    timeout: float | None = None,
    **kwargs: Any,
) -> CommandResult:
    """Run a command and return structured result.

    Args:
        cmd: Command and arguments as list
        check: Raise exception if command fails
        timeout: Command timeout in seconds
        **kwargs: Additional subprocess.run arguments

    Returns:
        CommandResult with output and status

    Raises:
        GCloudError: If command fails and check=True
    """
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            **kwargs,
        )
        cmd_result = CommandResult(
            returncode=result.returncode,
            stdout=result.stdout.strip(),
            stderr=result.stderr.strip(),
        )

        if check:
            cmd_result.check()

        return cmd_result

    except subprocess.TimeoutExpired as e:
        raise GCloudError(f"Command timed out after {timeout}s: {' '.join(cmd)}") from e
    except FileNotFoundError as e:
        raise GCloudError(f"Command not found: {cmd[0]}") from e
