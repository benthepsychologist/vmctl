"""IAP tunnel management for code-server access."""

import signal
import subprocess
import time

from rich.console import Console

from vmctl.config.models import VMConfig
from vmctl.core.exceptions import TunnelError

console = Console()


class TunnelManager:
    """Manages IAP tunnels to code-server."""

    def __init__(self, config: VMConfig, local_port: int = 8080, remote_port: int = 8080) -> None:
        """Initialize tunnel manager.

        Args:
            config: VM configuration
            local_port: Local port for tunnel
            remote_port: Remote port on VM (code-server default is 8080)
        """
        self.config = config
        self.local_port = local_port
        self.remote_port = remote_port
        self._process: subprocess.Popen[bytes] | None = None

    def start(self, background: bool = False) -> None:
        """Start IAP tunnel to code-server.

        Args:
            background: Run tunnel in background (default: foreground blocking)

        Raises:
            TunnelError: If tunnel startup fails
        """
        console.print(
            f"[blue]Starting IAP tunnel to {self.config.vm_name}:{self.remote_port} "
            f"-> localhost:{self.local_port}...[/blue]"
        )

        try:
            cmd = [
                "gcloud",
                "compute",
                "start-iap-tunnel",
                self.config.vm_name,
                str(self.remote_port),
                f"--local-host-port=localhost:{self.local_port}",
                f"--zone={self.config.zone}",
                f"--project={self.config.project}",
            ]

            if background:
                # Start in background
                self._process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                # Give it a moment to start
                time.sleep(2)
                console.print(
                    f"[green]✓ Tunnel started in background (PID: {self._process.pid})[/green]"
                )
                console.print(f"[yellow]→ Access code-server at http://localhost:{self.local_port}[/yellow]")
            else:
                # Run in foreground (blocking)
                console.print("[green]✓ Tunnel active[/green]")
                console.print(f"[yellow]→ Access code-server at http://localhost:{self.local_port}[/yellow]")
                console.print("[dim]Press Ctrl+C to stop tunnel[/dim]")

                # Run and handle Ctrl+C gracefully
                try:
                    subprocess.run(cmd, check=True)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Tunnel stopped[/yellow]")

        except subprocess.CalledProcessError as e:
            raise TunnelError(f"Failed to start tunnel: {e}") from e
        except Exception as e:
            raise TunnelError(f"Tunnel error: {e}") from e

    def stop(self) -> None:
        """Stop background tunnel process.

        Raises:
            TunnelError: If no background tunnel is running
        """
        if self._process is None:
            raise TunnelError("No background tunnel process running")

        try:
            # Send SIGTERM to process group
            if self._process.poll() is None:  # Still running
                self._process.send_signal(signal.SIGTERM)
                self._process.wait(timeout=5)
                console.print("[yellow]Tunnel stopped[/yellow]")
            else:
                console.print("[dim]Tunnel already stopped[/dim]")

        except subprocess.TimeoutExpired:
            # Force kill if didn't stop gracefully
            self._process.kill()
            console.print("[yellow]Tunnel force stopped[/yellow]")
        except Exception as e:
            raise TunnelError(f"Failed to stop tunnel: {e}") from e
        finally:
            self._process = None

    def check_tunnel(self, port: int | None = None) -> bool:
        """Check if a tunnel is active on the specified port.

        Args:
            port: Port to check (defaults to self.local_port)

        Returns:
            True if tunnel appears to be active
        """
        check_port = port or self.local_port

        # Check if port is in use (simple check)
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("localhost", check_port))
            sock.close()
            return result == 0
        except Exception:
            return False
