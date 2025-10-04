"""Tests for CLI functionality."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.cli import cli


class TestCLIEnvironmentVariables:
    """Test CLI environment variable support."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture(autouse=True)
    def mock_client(self):
        """Create a mock Todoist client."""
        with patch("src.cli.TodoistClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.get_projects.return_value = []
            mock_client.get_tasks.return_value = []
            yield mock_client

    @pytest.fixture(autouse=True)
    def mock_export_function(self):
        """Mock the export_tasks_internal function."""
        with patch("src.cli.export_tasks_internal") as mock_export:
            mock_export.return_value = 0
            yield mock_export

    def test_export_output_dir_env_var(self, runner, mock_export_function, tmp_path):
        """Test that EXPORT_OUTPUT_DIR environment variable is used."""
        test_output_dir = str(tmp_path / "custom_export")

        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_OUTPUT_DIR": test_output_dir,
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            # Verify that the export function was called with the env var path
            mock_export_function.assert_called_once()
            call_args = mock_export_function.call_args
            assert call_args.kwargs["export_config"].output_dir == Path(test_output_dir)

    def test_export_output_dir_cli_overrides_env(
        self, runner, mock_export_function, tmp_path
    ):
        """Test that CLI --output-dir option overrides environment variable."""
        env_output_dir = str(tmp_path / "env_export")
        cli_output_dir = str(tmp_path / "cli_export")

        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_OUTPUT_DIR": env_output_dir,
            },
        ):
            result = runner.invoke(cli, ["export", "--output-dir", cli_output_dir])

            assert result.exit_code == 0
            # CLI option should override env var
            call_args = mock_export_function.call_args
            assert call_args.kwargs["export_config"].output_dir == Path(cli_output_dir)

    def test_export_include_completed_env_var_true(self, runner, mock_export_function):
        """Test that EXPORT_INCLUDE_COMPLETED=true enables completed tasks."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMPLETED": "true",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            # Verify that include_completed was set to True
            call_args = mock_export_function.call_args
            assert call_args.kwargs["include_completed"] is True

    def test_export_include_completed_env_var_false(self, runner, mock_export_function):
        """Test that EXPORT_INCLUDE_COMPLETED=false disables completed tasks."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMPLETED": "false",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            # Verify that include_completed was set to False
            call_args = mock_export_function.call_args
            assert call_args.kwargs["include_completed"] is False

    def test_export_include_completed_env_var_1(self, runner, mock_export_function):
        """Test that EXPORT_INCLUDE_COMPLETED=1 enables completed tasks."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMPLETED": "1",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            call_args = mock_export_function.call_args
            assert call_args.kwargs["include_completed"] is True

    def test_export_include_completed_cli_overrides_env(
        self, runner, mock_export_function
    ):
        """Test that CLI --include-completed flag overrides environment variable."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMPLETED": "false",
            },
        ):
            result = runner.invoke(cli, ["export", "--include-completed"])

            assert result.exit_code == 0
            # CLI flag should override env var
            call_args = mock_export_function.call_args
            assert call_args.kwargs["include_completed"] is True

    def test_export_include_comments_env_var_true(self, runner, mock_export_function):
        """Test that EXPORT_INCLUDE_COMMENTS=true enables comments."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMMENTS": "true",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            # Verify that include_comments was set to True
            call_args = mock_export_function.call_args
            assert call_args.kwargs["export_config"].include_comments is True

    def test_export_include_comments_env_var_false(self, runner, mock_export_function):
        """Test that EXPORT_INCLUDE_COMMENTS=false disables comments."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMMENTS": "false",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            # Verify that include_comments was set to False
            call_args = mock_export_function.call_args
            assert call_args.kwargs["export_config"].include_comments is False

    def test_export_include_comments_env_var_1(self, runner, mock_export_function):
        """Test that EXPORT_INCLUDE_COMMENTS=1 enables comments."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMMENTS": "1",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            call_args = mock_export_function.call_args
            assert call_args.kwargs["export_config"].include_comments is True

    def test_export_include_comments_env_var_yes(self, runner, mock_export_function):
        """Test that EXPORT_INCLUDE_COMMENTS=yes enables comments."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMMENTS": "yes",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            call_args = mock_export_function.call_args
            assert call_args.kwargs["export_config"].include_comments is True

    def test_export_no_comments_flag_overrides_env(self, runner, mock_export_function):
        """Test that --no-comments flag overrides EXPORT_INCLUDE_COMMENTS env var."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMMENTS": "true",
            },
        ):
            result = runner.invoke(cli, ["export", "--no-comments"])

            assert result.exit_code == 0
            # --no-comments flag should override env var
            call_args = mock_export_function.call_args
            assert call_args.kwargs["export_config"].include_comments is False

    def test_export_all_env_vars_together(self, runner, mock_export_function, tmp_path):
        """Test that all environment variables work together."""
        test_output_dir = str(tmp_path / "env_export")

        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_OUTPUT_DIR": test_output_dir,
                "EXPORT_INCLUDE_COMPLETED": "true",
                "EXPORT_INCLUDE_COMMENTS": "false",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            call_args = mock_export_function.call_args

            # Check all configurations
            assert call_args.kwargs["export_config"].output_dir == Path(test_output_dir)
            assert call_args.kwargs["include_completed"] is True
            assert call_args.kwargs["export_config"].include_comments is False

    def test_export_env_vars_case_insensitive(self, runner, mock_export_function):
        """Test that environment variable values are case insensitive."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMPLETED": "TRUE",
                "EXPORT_INCLUDE_COMMENTS": "FALSE",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            call_args = mock_export_function.call_args
            assert call_args.kwargs["include_completed"] is True
            assert call_args.kwargs["export_config"].include_comments is False

    def test_export_env_vars_default_behavior(self, runner, mock_export_function):
        """Test default behavior when environment variables are not set."""
        with patch.dict(
            os.environ,
            {"TODOIST_API_TOKEN": "test_token"},
            clear=True,
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            call_args = mock_export_function.call_args

            # Check defaults
            assert (
                call_args.kwargs["export_config"].output_dir
                == Path.cwd() / "obsidian_export"
            )
            assert call_args.kwargs["include_completed"] is False
            assert call_args.kwargs["export_config"].include_comments is True

    def test_export_false_boolean_env_var(self, runner, mock_export_function):
        """Test that false boolean environment variables are parsed correctly."""
        with patch.dict(
            os.environ,
            {
                "TODOIST_API_TOKEN": "test_token",
                "EXPORT_INCLUDE_COMPLETED": "no",
                "EXPORT_INCLUDE_COMMENTS": "off",
            },
        ):
            result = runner.invoke(cli, ["export"])

            assert result.exit_code == 0
            call_args = mock_export_function.call_args

            # Values should be parsed as False
            assert call_args.kwargs["include_completed"] is False
            assert call_args.kwargs["export_config"].include_comments is False
