"""Tests for main CLI entry point."""

import pytest
from click.testing import CliRunner

from codestation import __version__
from codestation.cli.main import cli


class TestCLIMain:
    """Test main CLI entry point."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create Click test runner."""
        return CliRunner()

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI help message."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Codestation" in result.output
        assert "Save 61-83%" in result.output
        assert "Quick Start" in result.output

    def test_cli_version(self, runner: CliRunner) -> None:
        """Test CLI version output."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output
        assert "cstation" in result.output

    def test_cli_has_create_command(self, runner: CliRunner) -> None:
        """Test create command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "create" in result.output

    def test_cli_has_init_fresh_command(self, runner: CliRunner) -> None:
        """Test init-fresh command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "init-fresh" in result.output

    def test_cli_has_start_command(self, runner: CliRunner) -> None:
        """Test start command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "start" in result.output

    def test_cli_has_stop_command(self, runner: CliRunner) -> None:
        """Test stop command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "stop" in result.output

    def test_cli_has_status_command(self, runner: CliRunner) -> None:
        """Test status command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "status" in result.output

    def test_cli_has_connect_command(self, runner: CliRunner) -> None:
        """Test connect command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "connect" in result.output

    def test_cli_has_ssh_command(self, runner: CliRunner) -> None:
        """Test ssh command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "ssh" in result.output

    def test_cli_has_tunnel_command(self, runner: CliRunner) -> None:
        """Test tunnel command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "tunnel" in result.output

    def test_cli_has_logs_command(self, runner: CliRunner) -> None:
        """Test logs command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "logs" in result.output

    def test_cli_has_delete_command(self, runner: CliRunner) -> None:
        """Test delete command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "delete" in result.output

    def test_cli_has_config_command(self, runner: CliRunner) -> None:
        """Test config command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "config" in result.output

    def test_cli_has_backup_command(self, runner: CliRunner) -> None:
        """Test backup command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "backup" in result.output

    def test_cli_has_restore_command(self, runner: CliRunner) -> None:
        """Test restore command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "restore" in result.output

    def test_cli_has_snapshots_command(self, runner: CliRunner) -> None:
        """Test snapshots command is registered."""
        result = runner.invoke(cli, ["--help"])
        assert "snapshots" in result.output

    def test_cli_invalid_command(self, runner: CliRunner) -> None:
        """Test CLI with invalid command."""
        result = runner.invoke(cli, ["invalid-command"])
        assert result.exit_code != 0
        assert "Error" in result.output or "No such command" in result.output

    def test_cli_context_creation(self, runner: CliRunner) -> None:
        """Test CLI creates context object."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        # Context should be created without errors
