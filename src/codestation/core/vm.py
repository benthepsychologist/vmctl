"""VM management operations."""

from rich.console import Console

from codestation.config.models import VMConfig
from codestation.core.exceptions import VMError
from codestation.utils.subprocess_runner import run_command

console = Console()


class VMManager:
    """Manages Google Cloud VM instances."""

    def __init__(self, config: VMConfig) -> None:
        """Initialize VM manager.

        Args:
            config: VM configuration
        """
        self.config = config

    def exists(self) -> bool:
        """Check if VM exists.

        Returns:
            True if VM exists
        """
        result = run_command(
            [
                "gcloud",
                "compute",
                "instances",
                "describe",
                self.config.vm_name,
                f"--zone={self.config.zone}",
                f"--project={self.config.project}",
            ],
            check=False,
        )
        return result.success

    def status(self) -> str:
        """Get VM status.

        Returns:
            Status string (RUNNING, TERMINATED, STOPPED, etc.)

        Raises:
            VMError: If VM doesn't exist or status check fails
        """
        result = run_command(
            [
                "gcloud",
                "compute",
                "instances",
                "describe",
                self.config.vm_name,
                f"--zone={self.config.zone}",
                f"--project={self.config.project}",
                "--format=value(status)",
            ],
            check=False,
        )

        if not result.success:
            raise VMError(f"Failed to get VM status: {result.stderr}")

        return result.stdout or "UNKNOWN"

    def start(self) -> None:
        """Start the VM.

        Raises:
            VMError: If start fails
        """
        console.print(f"[blue]Starting VM {self.config.vm_name}...[/blue]")

        try:
            run_command(
                [
                    "gcloud",
                    "compute",
                    "instances",
                    "start",
                    self.config.vm_name,
                    f"--zone={self.config.zone}",
                    f"--project={self.config.project}",
                ],
                check=True,
            )
            console.print(f"[green]✓ VM {self.config.vm_name} started[/green]")
        except Exception as e:
            raise VMError(f"Failed to start VM: {e}") from e

    def stop(self) -> None:
        """Stop the VM.

        Raises:
            VMError: If stop fails
        """
        console.print(f"[blue]Stopping VM {self.config.vm_name}...[/blue]")

        try:
            run_command(
                [
                    "gcloud",
                    "compute",
                    "instances",
                    "stop",
                    self.config.vm_name,
                    f"--zone={self.config.zone}",
                    f"--project={self.config.project}",
                ],
                check=True,
            )
            console.print(f"[green]✓ VM {self.config.vm_name} stopped[/green]")
        except Exception as e:
            raise VMError(f"Failed to stop VM: {e}") from e

    def delete(self) -> None:
        """Delete the VM and its boot disk.

        Raises:
            VMError: If deletion fails
        """
        console.print(f"[red]Deleting VM {self.config.vm_name}...[/red]")

        try:
            run_command(
                [
                    "gcloud",
                    "compute",
                    "instances",
                    "delete",
                    self.config.vm_name,
                    f"--zone={self.config.zone}",
                    f"--project={self.config.project}",
                    "--delete-disks=boot",
                    "--quiet",
                ],
                check=True,
            )
            console.print(f"[green]✓ VM {self.config.vm_name} deleted[/green]")
        except Exception as e:
            raise VMError(f"Failed to delete VM: {e}") from e

    def ssh(self, command: str | None = None) -> None:
        """SSH into the VM.

        Args:
            command: Optional command to run (if None, opens interactive shell)

        Raises:
            VMError: If SSH fails
        """
        cmd = [
            "gcloud",
            "compute",
            "ssh",
            self.config.vm_name,
            f"--zone={self.config.zone}",
            f"--project={self.config.project}",
            "--tunnel-through-iap",
        ]

        if command:
            cmd.extend(["--command", command])

        try:
            result = run_command(cmd, check=False)
            if not result.success:
                raise VMError(f"SSH command failed: {result.stderr}")
        except Exception as e:
            raise VMError(f"Failed to SSH to VM: {e}") from e

    def logs(self, log_file: str = "/var/log/vm-auto-shutdown.log") -> str:
        """Get logs from VM.

        Args:
            log_file: Path to log file on VM

        Returns:
            Log contents

        Raises:
            VMError: If log retrieval fails
        """
        result = run_command(
            [
                "gcloud",
                "compute",
                "ssh",
                self.config.vm_name,
                f"--zone={self.config.zone}",
                f"--project={self.config.project}",
                "--tunnel-through-iap",
                "--command",
                f"sudo cat {log_file}",
            ],
            check=False,
        )

        if not result.success:
            raise VMError(f"Failed to retrieve logs: {result.stderr}")

        return result.stdout
