"""VM management operations."""

from rich.console import Console

from vmctl.config.models import VMConfig
from vmctl.core.exceptions import VMError
from vmctl.utils.subprocess_runner import run_command

console = Console()


class VMManager:
    """Manages Google Cloud VM instances."""

    def __init__(self, config: VMConfig) -> None:
        """Initialize VM manager.

        Args:
            config: VM configuration
        """
        self.config = config

    @property
    def use_direct_ssh(self) -> bool:
        """Whether to use direct SSH instead of gcloud compute ssh."""
        return self.config.ssh_host is not None

    def _ssh_opts(self) -> list[str]:
        """Build common SSH options for direct SSH."""
        opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
        if self.config.ssh_key:
            opts.extend(["-i", self.config.ssh_key])
        if self.config.ssh_port:
            opts.extend(["-p", str(self.config.ssh_port)])
        return opts

    def _scp_opts(self) -> list[str]:
        """Build common SCP options for direct SSH."""
        opts = ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
        if self.config.ssh_key:
            opts.extend(["-i", self.config.ssh_key])
        if self.config.ssh_port:
            opts.extend(["-P", str(self.config.ssh_port)])
        return opts

    def _ssh_target(self) -> str:
        """Build user@host string for direct SSH."""
        host = self.config.ssh_host
        if self.config.ssh_user:
            return f"{self.config.ssh_user}@{host}"
        return host or ""

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
        if self.use_direct_ssh:
            cmd = ["ssh", *self._ssh_opts(), self._ssh_target()]
            if command:
                cmd.append(command)
        else:
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

    def ssh_exec(self, command: str) -> tuple[bool, str, str]:
        """Execute a command on the VM via SSH and return output.

        Unlike ssh(), this method captures and returns stdout/stderr
        for programmatic use.

        Args:
            command: Command to execute on the VM

        Returns:
            Tuple of (success, stdout, stderr)
        """
        if self.use_direct_ssh:
            cmd = ["ssh", *self._ssh_opts(), self._ssh_target(), command]
        else:
            cmd = [
                "gcloud",
                "compute",
                "ssh",
                self.config.vm_name,
                f"--zone={self.config.zone}",
                f"--project={self.config.project}",
                "--tunnel-through-iap",
                "--command",
                command,
            ]

        result = run_command(cmd, check=False)
        return result.success, result.stdout, result.stderr

    def scp(
        self, local_path: str, remote_path: str, recursive: bool = False
    ) -> tuple[bool, str, str]:
        """Copy files to VM via SCP.

        Uses direct scp when ssh_host is configured, otherwise
        gcloud compute scp with IAP tunneling.

        Args:
            local_path: Local file or directory path
            remote_path: Remote destination path on VM
            recursive: If True, copy directories recursively

        Returns:
            Tuple of (success, stdout, stderr)
        """
        if self.use_direct_ssh:
            cmd = ["scp", *self._scp_opts()]
            if recursive:
                cmd.append("-r")
            cmd.extend([local_path, f"{self._ssh_target()}:{remote_path}"])
        else:
            cmd = [
                "gcloud",
                "compute",
                "scp",
            ]
            if recursive:
                cmd.append("--recurse")
            cmd.extend(
                [
                    local_path,
                    f"{self.config.vm_name}:{remote_path}",
                    f"--zone={self.config.zone}",
                    f"--project={self.config.project}",
                    "--tunnel-through-iap",
                ]
            )
        result = run_command(cmd, check=False)
        return result.success, result.stdout, result.stderr

    def logs(self, log_file: str = "/var/log/vm-auto-shutdown.log") -> str:
        """Get logs from VM.

        Args:
            log_file: Path to log file on VM

        Returns:
            Log contents

        Raises:
            VMError: If log retrieval fails
        """
        success, stdout, stderr = self.ssh_exec(f"sudo cat {log_file}")

        if not success:
            raise VMError(f"Failed to retrieve logs: {stderr}")

        return stdout
