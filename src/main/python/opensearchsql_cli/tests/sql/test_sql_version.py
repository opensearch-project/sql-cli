"""
Tests for SQL Version Management.

This module contains tests for the SQL Version Management functionality.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from opensearchsql_cli.sql.sql_version import SqlVersion


class TestSqlVersion:
    """
    Test class for SqlVersion.
    """

    @pytest.mark.parametrize(
        "test_id, description, version, rebuild, jar_exists, expected_result",
        [
            (1, "SQL version: success", "3.1", False, True, True),
            (2, "SQL version: unsupported fail", "4.0", False, False, False),
            (3, "SQL version: invalid format", "invalid", False, False, False),
        ],
    )
    @patch("opensearchsql_cli.sql.sql_version.os.path.exists")
    @patch("opensearchsql_cli.sql.sql_version.os.path.join")
    @patch("opensearchsql_cli.sql.sql_version.console")
    def test_set_version(
        self,
        mock_console,
        mock_join,
        mock_exists,
        test_id,
        description,
        version,
        rebuild,
        jar_exists,
        expected_result,
    ):
        """
        Test cases for SQL version selection
        """
        # Setup mocks
        mock_exists.return_value = jar_exists
        mock_join.return_value = "/mock/path/opensearchsql-v3.1.0.0.jar"

        # Create version manager and set version
        version_manager = SqlVersion()
        result = version_manager.set_version(version, rebuild)

        # Assertions
        assert result is expected_result

        if expected_result:
            # For successful version setting
            assert version_manager.version.startswith(version)
        else:
            # For failed version setting
            if "invalid" in version:
                # Invalid format case
                mock_console.print.assert_any_call(
                    f"[bold red]\nERROR:[/bold red] [red]Version {version} is currently not supported.[/red]"
                )
            else:
                # Unsupported version case
                mock_console.print.assert_any_call(
                    f"[bold red]\nERROR:[/bold red] [red]Version {version} is currently not supported.[/red]"
                )

    @patch("opensearchsql_cli.sql.sql_version.os.path.exists")
    @patch("opensearchsql_cli.sql.sql_version.os.path.join")
    @patch("opensearchsql_cli.sql.sql_version.subprocess.run")
    @patch("opensearchsql_cli.sql.sql_version.console")
    @patch("opensearchsql_cli.sql.sql_version.open", create=True)
    def test_rebuild_jar(
        self, mock_open, mock_console, mock_run, mock_join, mock_exists
    ):
        """
        Test rebuilding JAR file
        """
        # Setup mocks to simulate JAR not existing initially but created after build
        mock_exists.side_effect = [
            False,
            True,
        ]  # First call returns False, second call returns True

        # Need to handle multiple calls to os.path.join
        def join_side_effect(*args):
            if args[-1] == "build.log":
                return "/mock/path/build.log"
            else:
                return "/mock/path/opensearchsql-v3.1.0.0.jar"

        mock_join.side_effect = join_side_effect
        mock_run.return_value = MagicMock(returncode=0)
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Create version manager and set version with rebuild
        version_manager = SqlVersion()
        result = version_manager.set_version("3.1", rebuild=True)

        # Assertions
        assert result is True
        mock_run.assert_called_once()
        mock_console.print.assert_any_call(
            "[bold green]SUCCESS:[/bold green] [green]Built v3.1.0.0 successfully at /mock/path/opensearchsql-v3.1.0.0.jar[/green]"
        )

    @patch("opensearchsql_cli.sql.sql_version.os.path.join")
    def test_get_jar_path(self, mock_join):
        """
        Test getting JAR path
        """
        # Setup mock
        expected_path = "/mock/project_root/build/libs/opensearchsql-v3.1.0.0.jar"
        mock_join.return_value = expected_path

        # Create version manager and get JAR path
        version_manager = SqlVersion()
        path = version_manager.get_jar_path("/mock/project_root")

        # Assertions
        assert path == expected_path
        mock_join.assert_called_with(
            "/mock/project_root", "build", "libs", "opensearchsql-v3.1.0.0.jar"
        )
