"""Tests for tunnel management."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from vmws.config.models import VMConfig
from vmws.core.exceptions import TunnelError
from vmws.core.tunnel import TunnelManager


@pytest.fixture
def vm_config() -> VMConfig:
    """Create test VM config."""
    return VMConfig(
        vm_name="test-vm",
        zone="us-central1-a",
        project="test-project",
    )


@pytest.fixture
def tunnel_manager(vm_config: VMConfig) -> TunnelManager:
    """Create tunnel manager for testing."""
    return TunnelManager(vm_config, local_port=8080, remote_port=8080)


class TestTunnelManager:
    """Test TunnelManager class."""

    def test_init(self, tunnel_manager: TunnelManager) -> None:
        """Test tunnel manager initialization."""
        assert tunnel_manager.local_port == 8080
        assert tunnel_manager.remote_port == 8080
        assert tunnel_manager._process is None

    def test_init_custom_ports(self, vm_config: VMConfig) -> None:
        """Test initialization with custom ports."""
        tunnel = TunnelManager(vm_config, local_port=9090, remote_port=8443)
        assert tunnel.local_port == 9090
        assert tunnel.remote_port == 8443

    def test_check_tunnel_active(self, tunnel_manager: TunnelManager) -> None:
        """Test checking if tunnel is active."""
        with patch("socket.socket") as mock_socket_class:
            mock_sock = mock_socket_class.return_value
            mock_sock.connect_ex.return_value = 0

            assert tunnel_manager.check_tunnel() is True
            mock_sock.connect_ex.assert_called_once_with(("localhost", 8080))
            mock_sock.close.assert_called_once()

    def test_check_tunnel_inactive(self, tunnel_manager: TunnelManager) -> None:
        """Test checking if tunnel is inactive."""
        with patch("socket.socket") as mock_socket_class:
            mock_sock = mock_socket_class.return_value
            mock_sock.connect_ex.return_value = 1

            assert tunnel_manager.check_tunnel() is False

    def test_check_tunnel_custom_port(self, tunnel_manager: TunnelManager) -> None:
        """Test checking tunnel on custom port."""
        with patch("socket.socket") as mock_socket_class:
            mock_sock = mock_socket_class.return_value
            mock_sock.connect_ex.return_value = 0

            assert tunnel_manager.check_tunnel(port=9090) is True
            mock_sock.connect_ex.assert_called_once_with(("localhost", 9090))

    def test_check_tunnel_exception(self, tunnel_manager: TunnelManager) -> None:
        """Test check_tunnel handles exceptions."""
        with patch("socket.socket") as mock_socket_class:
            mock_socket_class.side_effect = Exception("Socket error")

            assert tunnel_manager.check_tunnel() is False

    @patch("vmws.core.tunnel.subprocess.Popen")
    @patch("vmws.core.tunnel.time.sleep")
    def test_start_background(
        self, mock_sleep: MagicMock, mock_popen: MagicMock, tunnel_manager: TunnelManager
    ) -> None:
        """Test starting tunnel in background."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process

        tunnel_manager.start(background=True)

        # Verify gcloud command was constructed correctly
        expected_cmd = [
            "gcloud",
            "compute",
            "start-iap-tunnel",
            "test-vm",
            "8080",
            "--local-host-port=localhost:8080",
            "--zone=us-central1-a",
            "--project=test-project",
        ]
        mock_popen.assert_called_once_with(
            expected_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        mock_sleep.assert_called_once_with(2)
        assert tunnel_manager._process is mock_process

    @patch("vmws.core.tunnel.subprocess.run")
    def test_start_foreground(self, mock_run: MagicMock, tunnel_manager: TunnelManager) -> None:
        """Test starting tunnel in foreground."""
        tunnel_manager.start(background=False)

        expected_cmd = [
            "gcloud",
            "compute",
            "start-iap-tunnel",
            "test-vm",
            "8080",
            "--local-host-port=localhost:8080",
            "--zone=us-central1-a",
            "--project=test-project",
        ]
        mock_run.assert_called_once_with(expected_cmd, check=True)

    @patch("vmws.core.tunnel.subprocess.run")
    def test_start_foreground_keyboard_interrupt(
        self, mock_run: MagicMock, tunnel_manager: TunnelManager
    ) -> None:
        """Test starting tunnel handles keyboard interrupt."""
        mock_run.side_effect = KeyboardInterrupt()

        # Should not raise, just exit gracefully
        tunnel_manager.start(background=False)

    @patch("vmws.core.tunnel.subprocess.run")
    def test_start_foreground_error(
        self, mock_run: MagicMock, tunnel_manager: TunnelManager
    ) -> None:
        """Test start raises TunnelError on subprocess error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "gcloud")

        with pytest.raises(TunnelError, match="Failed to start tunnel"):
            tunnel_manager.start(background=False)

    @patch("vmws.core.tunnel.subprocess.Popen")
    def test_start_background_error(
        self, mock_popen: MagicMock, tunnel_manager: TunnelManager
    ) -> None:
        """Test start background raises TunnelError on error."""
        mock_popen.side_effect = Exception("Popen failed")

        with pytest.raises(TunnelError, match="Tunnel error"):
            tunnel_manager.start(background=True)

    def test_stop_no_process(self, tunnel_manager: TunnelManager) -> None:
        """Test stop raises error when no process running."""
        with pytest.raises(TunnelError, match="No background tunnel process running"):
            tunnel_manager.stop()

    def test_stop_running_process(self, tunnel_manager: TunnelManager) -> None:
        """Test stopping a running background process."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        tunnel_manager._process = mock_process

        tunnel_manager.stop()

        mock_process.send_signal.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)
        assert tunnel_manager._process is None

    def test_stop_already_stopped_process(self, tunnel_manager: TunnelManager) -> None:
        """Test stopping a process that already stopped."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Already stopped
        tunnel_manager._process = mock_process

        tunnel_manager.stop()

        mock_process.send_signal.assert_not_called()
        assert tunnel_manager._process is None

    def test_stop_timeout_force_kill(self, tunnel_manager: TunnelManager) -> None:
        """Test stop force kills process if timeout expires."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.wait.side_effect = subprocess.TimeoutExpired("cmd", 5)
        tunnel_manager._process = mock_process

        tunnel_manager.stop()

        mock_process.kill.assert_called_once()
        assert tunnel_manager._process is None

    def test_stop_error(self, tunnel_manager: TunnelManager) -> None:
        """Test stop raises TunnelError on unexpected error."""
        mock_process = MagicMock()
        mock_process.poll.side_effect = Exception("Unexpected error")
        tunnel_manager._process = mock_process

        with pytest.raises(TunnelError, match="Failed to stop tunnel"):
            tunnel_manager.stop()

        # Process should be cleared even on error
        assert tunnel_manager._process is None
