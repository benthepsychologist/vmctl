"""Tests for subprocess runner utility."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from codestation.core.exceptions import GCloudError
from codestation.utils.subprocess_runner import CommandResult, run_command


class TestCommandResult:
    """Test CommandResult class."""

    def test_command_result_success(self) -> None:
        """Test CommandResult for successful command."""
        result = CommandResult(returncode=0, stdout="output", stderr="")
        assert result.returncode == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.success is True

    def test_command_result_failure(self) -> None:
        """Test CommandResult for failed command."""
        result = CommandResult(returncode=1, stdout="", stderr="error message")
        assert result.returncode == 1
        assert result.stdout == ""
        assert result.stderr == "error message"
        assert result.success is False

    def test_command_result_check_success(self) -> None:
        """Test check() method on successful command."""
        result = CommandResult(returncode=0, stdout="output", stderr="")
        # Should not raise exception
        checked_result = result.check()
        # Should return self for chaining
        assert checked_result is result

    def test_command_result_check_failure(self) -> None:
        """Test check() method on failed command."""
        result = CommandResult(returncode=1, stdout="out", stderr="err")
        with pytest.raises(GCloudError, match="Command failed with exit code 1"):
            result.check()

    def test_command_result_check_failure_includes_output(self) -> None:
        """Test check() includes stdout and stderr in error."""
        result = CommandResult(returncode=2, stdout="stdout content", stderr="stderr content")
        with pytest.raises(GCloudError) as exc_info:
            result.check()
        error_message = str(exc_info.value)
        assert "stdout content" in error_message
        assert "stderr content" in error_message
        assert "exit code 2" in error_message


class TestRunCommand:
    """Test run_command function."""

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_success(self, mock_run: MagicMock) -> None:
        """Test successful command execution."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  hello world  \n",
            stderr="",
        )

        result = run_command(["echo", "hello world"])

        assert result.success is True
        assert result.returncode == 0
        assert result.stdout == "hello world"  # Should be stripped
        assert result.stderr == ""
        mock_run.assert_called_once_with(
            ["echo", "hello world"],
            capture_output=True,
            text=True,
            timeout=None,
        )

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_failure(self, mock_run: MagicMock) -> None:
        """Test failed command execution."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error occurred",
        )

        result = run_command(["false"])

        assert result.success is False
        assert result.returncode == 1
        assert result.stderr == "error occurred"

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_with_check_success(self, mock_run: MagicMock) -> None:
        """Test command with check=True on success."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="success",
            stderr="",
        )

        result = run_command(["ls"], check=True)

        assert result.success is True
        assert result.stdout == "success"

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_with_check_failure(self, mock_run: MagicMock) -> None:
        """Test command with check=True on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error",
        )

        with pytest.raises(GCloudError, match="Command failed with exit code 1"):
            run_command(["false"], check=True)

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_with_timeout(self, mock_run: MagicMock) -> None:
        """Test command with timeout parameter."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="done",
            stderr="",
        )

        result = run_command(["sleep", "1"], timeout=5.0)

        assert result.success is True
        mock_run.assert_called_once_with(
            ["sleep", "1"],
            capture_output=True,
            text=True,
            timeout=5.0,
        )

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_timeout_expired(self, mock_run: MagicMock) -> None:
        """Test command that times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["sleep", "100"],
            timeout=1.0,
        )

        with pytest.raises(GCloudError, match="Command timed out after 1.0s"):
            run_command(["sleep", "100"], timeout=1.0)

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_file_not_found(self, mock_run: MagicMock) -> None:
        """Test command that doesn't exist."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(GCloudError, match="Command not found: nonexistent"):
            run_command(["nonexistent", "arg"])

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_with_kwargs(self, mock_run: MagicMock) -> None:
        """Test command with additional subprocess kwargs."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr="",
        )

        result = run_command(
            ["ls"],
            cwd="/tmp",
            env={"PATH": "/usr/bin"},
        )

        assert result.success is True
        # Verify kwargs were passed through
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["cwd"] == "/tmp"
        assert call_kwargs["env"] == {"PATH": "/usr/bin"}

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_strips_whitespace(self, mock_run: MagicMock) -> None:
        """Test that stdout and stderr are stripped."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  \n  output with spaces  \n  ",
            stderr="\t\terror message\t\t\n",
        )

        result = run_command(["test"])

        assert result.stdout == "output with spaces"
        assert result.stderr == "error message"

    @patch("codestation.utils.subprocess_runner.subprocess.run")
    def test_run_command_captures_output(self, mock_run: MagicMock) -> None:
        """Test that run_command always captures output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="captured",
            stderr="also captured",
        )

        result = run_command(["cmd"])

        # Verify capture_output=True and text=True are always set
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["capture_output"] is True
        assert call_kwargs["text"] is True
        assert result.stdout == "captured"
        assert result.stderr == "also captured"
