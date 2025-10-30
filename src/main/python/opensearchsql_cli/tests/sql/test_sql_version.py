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
        mock_get_all_versions,
    ):
        """
        Test cases for SQL version selection
        """
        # Setup mocks
        mock_exists.return_value = jar_exists
        mock_join.return_value = "/mock/path/opensearchsqlcli-3.1.0.0.jar"

        # For failure cases, ensure the requested version is not in the list
        if test_id != 1:
            mock_get_all_versions.return_value = [
                v
                for v in mock_get_all_versions.return_value
                if not v.startswith(version)
            ]

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
                    f"[bold red]ERROR:[/bold red] [red]Version {version} is currently not supported[/red]"
                )
            else:
                # Unsupported version case
                mock_console.print.assert_any_call(
                    f"[bold red]ERROR:[/bold red] [red]Version {version} is currently not supported[/red]"
                )

    @patch("opensearchsql_cli.sql.sql_version.os.path.dirname")
    @patch("opensearchsql_cli.sql.sql_version.os.makedirs")
    @patch("opensearchsql_cli.sql.sql_version.os.path.exists")
    @patch("opensearchsql_cli.sql.sql_version.os.path.join")
    @patch("opensearchsql_cli.sql.sql_version.subprocess.run")
    @patch("opensearchsql_cli.sql.sql_version.console")
    @patch("opensearchsql_cli.sql.sql_version.open", create=True)
    def test_rebuild_jar(
        self,
        mock_open,
        mock_console,
        mock_run,
        mock_join,
        mock_exists,
        mock_makedirs,
        mock_dirname,
        mock_get_all_versions,
    ):
        """
        Test rebuilding JAR file
        """
        # Make sure version is in the list of available versions
        if "3.1.0.0" not in mock_get_all_versions.return_value:
            mock_get_all_versions.return_value = [
                "3.1.0.0"
            ] + mock_get_all_versions.return_value

        # Setup mocks to simulate JAR not existing initially but created after build
        mock_exists.side_effect = [
            False,
            True,
        ]  # First call returns False, second call returns True

        # Need to handle multiple calls to os.path.join
        def join_side_effect(*args):
            if args[-1] == "sqlcli_build.log":
                return "/mock/path/sqlcli_build.log"
            else:
                return "/mock/path/opensearchsqlcli-3.1.0.0.jar"

        mock_join.side_effect = join_side_effect
        mock_dirname.return_value = "/mock/path"
        mock_run.return_value = MagicMock(returncode=0)
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Create version manager and set version with rebuild
        version_manager = SqlVersion()
        result = version_manager.set_version("3.1", rebuild=True)

        # Assertions
        assert result is True
        assert mock_run.call_count == 2
        mock_console.print.assert_any_call(
            "[bold green]SUCCESS:[/bold green] [green]Built SQL CLI at /mock/path/opensearchsqlcli-3.1.0.0.jar[/green]"
        )

    @patch("opensearchsql_cli.sql.sql_version.PROJECT_ROOT", "/mock/project_root")
    @patch("opensearchsql_cli.sql.sql_version.os.path.join")
    def test_get_jar_path(
        self,
        mock_join,
    ):
        """
        Test getting JAR path
        """
        # Setup mock
        expected_path = "/mock/project_root/build/libs/opensearchsqlcli-live.jar"
        mock_join.return_value = expected_path

        # Create version manager and get JAR path
        version_manager = SqlVersion()
        path = version_manager.get_jar_path()

        # Assertions
        assert path == expected_path
        mock_join.assert_called_with(
            "/mock/project_root", "build", "libs", "opensearchsqlcli-live.jar"
        )
