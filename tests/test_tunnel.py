"""Tests for tunnel management."""

from unittest.mock import patch

import pytest

from vmws.config.models import VMConfig
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

    def test_check_tunnel_active(self, tunnel_manager: TunnelManager) -> None:
        """Test checking if tunnel is active."""
        with patch("socket.socket") as mock_socket_class:
            mock_sock = mock_socket_class.return_value
            mock_sock.connect_ex.return_value = 0

            assert tunnel_manager.check_tunnel() is True

    def test_check_tunnel_inactive(self, tunnel_manager: TunnelManager) -> None:
        """Test checking if tunnel is inactive."""
        with patch("socket.socket") as mock_socket_class:
            mock_sock = mock_socket_class.return_value
            mock_sock.connect_ex.return_value = 1

            assert tunnel_manager.check_tunnel() is False
