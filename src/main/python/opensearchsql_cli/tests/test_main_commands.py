"""
Tests for individual CLI commands.

This module contains tests for each command-line option of the CLI application.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from ..main import OpenSearchSqlCli

# Create a CLI runner for testing
runner = CliRunner()


class TestCommands:
    """
    Test class for individual CLI commands.
    """

    # Test case counter
    test_case_num = 0

    def print_test_info(self, description, result=None):
        """
        Print test case number, description, and result.

        Args:
            description: Test case description
            result: Test result (optional)
        """

        if result is None:
            TestCommands.test_case_num += 1
            print(f"\n=== Test Case #{TestCommands.test_case_num}: {description} ===")
        else:
            print(f"Result: {result}")

    def _check_missing_arg(self, flag, expected_error_text):
        """
        Helper method to test commands with missing arguments.

        Args:
            flag: Command-line flag to test (e.g., "-e", "--aws-auth")
            expected_error_text: Text to look for in the error message

        Returns:
            tuple: (result, test_result) where:
                - result: The result of the command execution
                - test_result: A string describing the test result
        """
        # Create a CLI instance with mocked shell
        cli = OpenSearchSqlCli()
        cli.shell = MagicMock()

        # Invoke the CLI with the flag but no argument
        result = runner.invoke(cli.app, [flag])

        # Verify the result
        assert result.exit_code == 2
        assert expected_error_text in result.stderr

        test_result = f"Command correctly failed with missing argument error for {flag}"
        return result, test_result

    def setup_cli_test(
        self,
        mock_console,
        mock_config_manager,
        mock_version_manager,
        mock_library_manager,
        mock_sql_connection,
        mock_figlet=None,
        endpoint=None,
        username_password=None,
        insecure=False,
        aws_auth=None,
        language=None,
        format=None,
        version=None,
        local=None,
        remote=None,
        remote_output=None,
        rebuild=False,
        config=False,
        connection_success=True,
        error_message=None,
        version_success=True,
    ):
        """
        Setup common test environment for CLI tests.

        Args:
            mock_console: Mocked console object
            mock_config_manager: Mocked config manager
            mock_version_manager: Mocked version manager
            mock_library_manager: Mocked library manager
            mock_sql_connection: Mocked SQL connection
            mock_figlet: Mocked figlet (optional)
            endpoint: Endpoint parameter (optional)
            username_password: Username and password in format username:password (optional)
            insecure: Whether to ignore SSL certificate validation (optional)
            aws_auth: AWS auth parameter (optional)
            language: Language mode (optional)
            format: Output format (optional)
            version: SQL plugin version (optional)
            rebuild: Whether to rebuild the JAR file (optional)
            config: Whether to display configuration settings (optional)
            connection_success: Whether the connection should succeed (optional)
            error_message: Error message to return if connection fails (optional)
            version_success: Whether version setting should succeed (optional)

        Returns:
            tuple: (cli, command_args)
        """

        # Mock the necessary components to avoid actual connections
        mock_sql_connection.connect.return_value = True
        mock_sql_connection.verify_opensearch_connection.return_value = (
            connection_success
        )
        mock_sql_connection.initialize_sql_library.return_value = connection_success
        mock_sql_connection.version = "2.0.0"

        # Set error message if provided
        if error_message:
            mock_sql_connection.error_message = error_message

        # Set URL and username based on endpoint type
        if aws_auth:
            mock_sql_connection.url = aws_auth
            mock_sql_connection.username = "us-west-2"
        elif username_password and (endpoint and endpoint.startswith("https")):
            # Set username for HTTPS connections
            mock_sql_connection.url = endpoint
            mock_sql_connection.username = username_password.split(":")[0]
        else:
            # For HTTP connections, set empty username
            mock_sql_connection.url = endpoint or endpoint.startswith("http")
            mock_sql_connection.username = ""

        # Set up version manager
        mock_version_manager.version = version or "1.0.0"
        mock_version_manager.set_version.return_value = version_success
        mock_version_manager.set_local_version.return_value = version_success
        mock_version_manager.set_remote_version.return_value = version_success

        mock_config_manager.get.side_effect = lambda section, key, default: {
            ("Query", "language", "ppl"): language or "ppl",
            ("Query", "format", "table"): format or "table",
            ("Connection", "endpoint", ""): "",
            ("Connection", "username", ""): "",
            ("Connection", "password", ""): "",
            ("SqlVersion", "remote_output", ""): remote_output or "",
        }.get((section, key, default), default)

        mock_config_manager.get_boolean.side_effect = lambda section, key, default: {
            ("Connection", "insecure", False): insecure,
            ("Connection", "aws_auth", False): False,
            ("Query", "vertical", False): False,
        }.get((section, key, default), default)

        if mock_figlet:
            mock_figlet.return_value = "OpenSearch"

        # Create a CLI instance with mocked dependencies
        cli = OpenSearchSqlCli()

        # Mock the shell attribute to prevent it from being called
        if not config:
            cli.shell = MagicMock()

        # Prepare command arguments
        command_args = []
        if endpoint:
            command_args.extend(["-e", endpoint])
        if username_password:
            command_args.extend(["-u", username_password])
        if insecure:
            command_args.append("-k")
        if aws_auth:
            command_args.extend(["--aws-auth", aws_auth])
        if language:
            command_args.extend(["-l", language])
        if format:
            command_args.extend(["-f", format])
        if version:
            command_args.extend(["--version", version])
        if local:
            command_args.extend(["--local", local])
        if remote:
            command_args.extend(["--remote", remote])
        if remote_output:
            command_args.extend(["--output", remote_output])
        if rebuild:
            command_args.append("--rebuild")
        if config:
            command_args.append("--config")

        return cli, command_args

    @pytest.mark.parametrize(
        "test_id, description, endpoint, username_password, insecure, expected_success, error_message",
        [
            (
                1,
                "HTTP success",
                "test:9200",
                None,
                False,
                True,
                None,
            ),
            (
                2,
                "HTTPS success with auth",
                "https://test:9200",
                "user:pass",
                False,
                True,
                None,
            ),
            (
                3,
                "HTTPS success with auth and insecure flag",
                "https://test:9200",
                "user:pass",
                True,
                True,
                None,
            ),
            (
                4,
                "Endpoint missing argument",
                None,
                None,
                False,
                False,
                "Option '-e' requires an argument.",
            ),
        ],
    )
    @patch("opensearchsql_cli.main.sql_connection")
    @patch("opensearchsql_cli.main.sql_library_manager")
    @patch("opensearchsql_cli.main.sql_version")
    @patch("opensearchsql_cli.main.config_manager")
    @patch("opensearchsql_cli.main.console")
    @patch("opensearchsql_cli.main.pyfiglet.figlet_format")
    def test_endpoint_command(
        self,
        mock_figlet,
        mock_console,
        mock_config_manager,
        mock_version_manager,
        mock_library_manager,
        mock_sql_connection,
        test_id,
        description,
        endpoint,
        username_password,
        insecure,
        expected_success,
        error_message,
    ):
        """
        Test the -e -u -k commands for HTTPS connections with authentication and insecure flag.
        """

        self.print_test_info(f"{description} (Test #{test_id})")

        if endpoint == None:
            # Test missing argument case
            result, test_result = self._check_missing_arg(
                "-e", "Option '-e' requires an argument"
            )
        else:
            # Setup test environment
            cli, command_args = self.setup_cli_test(
                mock_console,
                mock_config_manager,
                mock_version_manager,
                mock_library_manager,
                mock_sql_connection,
                mock_figlet,
                endpoint=endpoint,
                username_password=username_password,
                insecure=insecure,
                connection_success=expected_success,
                error_message=error_message,
            )
            result = runner.invoke(cli.app, command_args)

            assert result.exit_code == 0

            # Verify specific behavior based on expected success
            if expected_success:
                mock_console.print.assert_any_call(
                    f"[green]Endpoint:[/green] {endpoint}"
                )
                if username_password:
                    username = username_password.split(":")[0]
                    mock_console.print.assert_any_call(
                        f"[green]User:[/green] [dim white]{username}[/dim white]"
                    )
                    test_result = f"Successfully connected to {endpoint} with user {username_password}"
                else:
                    test_result = f"Successfully connected to {endpoint}"
            else:
                mock_console.print.assert_any_call(
                    f"[bold red]ERROR:[/bold red] [red]{error_message}[/red]\n"
                )
                test_result = f"Failed to connect to {endpoint} as expected"

        self.print_test_info(f"{description} (Test #{test_id})", test_result)

    @pytest.mark.parametrize(
        "test_id, description, aws_auth, expected_success, error_message",
        [
            (
                1,
                "AWS auth success",
                "https://test-domain.us-west-2.es.amazonaws.com",
                True,
                None,
            ),
            (
                2,
                "AWS auth missing argument",
                None,
                False,
                "Option '--aws-auth' requires an argument.",
            ),
        ],
    )
    @patch("opensearchsql_cli.main.sql_connection")
    @patch("opensearchsql_cli.main.sql_library_manager")
    @patch("opensearchsql_cli.main.sql_version")
    @patch("opensearchsql_cli.main.config_manager")
    @patch("opensearchsql_cli.main.console")
    @patch("opensearchsql_cli.main.pyfiglet.figlet_format")
    def test_aws_auth_command(
        self,
        mock_figlet,
        mock_console,
        mock_config_manager,
        mock_version_manager,
        mock_library_manager,
        mock_sql_connection,
        test_id,
        description,
        aws_auth,
        expected_success,
        error_message,
    ):
        """
        Test the --aws-auth command for AWS authentication.
        """

        self.print_test_info(f"{description} (Test #{test_id})")

        if aws_auth == None:
            # Test missing argument case
            result, test_result = self._check_missing_arg(
                "--aws-auth", "Option '--aws-auth' requires an argument"
            )
        else:
            # Setup test environment normally
            cli, command_args = self.setup_cli_test(
                mock_console,
                mock_config_manager,
                mock_version_manager,
                mock_library_manager,
                mock_sql_connection,
                mock_figlet,
                aws_auth=aws_auth,
                connection_success=expected_success,
                error_message=error_message,
            )
            result = runner.invoke(cli.app, command_args)

            # For normal cases, expect exit code 0
            assert result.exit_code == 0

            # Verify specific behavior based on expected success
            if expected_success:
                mock_console.print.assert_any_call(
                    f"[green]Endpoint:[/green] {aws_auth}"
                )
                mock_console.print.assert_any_call(
                    f"[green]Region:[/green] [dim white]us-west-2[/dim white]"
                )
                test_result = f"Successfully connected to AWS endpoint {aws_auth}"
            else:
                mock_console.print.assert_any_call(
                    f"[bold red]ERROR:[/bold red] [red]{error_message}[/red]\n"
                )
                test_result = (
                    f"Failed to connect to AWS endpoint {aws_auth} as expected"
                )

        self.print_test_info(f"{description} (Test #{test_id})", test_result)

    @pytest.mark.parametrize(
        "test_id, description, command_type, value, expected_display, rebuild, version_success",
        [
            # Language tests
            (1, "PPL language", "language", "ppl", "PPL", False, True),
            (2, "SQL language", "language", "sql", "SQL", False, True),
            (3, "Language missing argument", "language", None, None, False, True),
            # Format tests
            (4, "Table format", "format", "table", "TABLE", False, True),
            (5, "JSON format", "format", "json", "JSON", False, True),
            (6, "CSV format", "format", "csv", "CSV", False, True),
            (7, "Format missing argument", "format", None, None, False, True),
            # Version tests
            (8, "Valid version", "version", "3.1", "v3.1", False, True),
            (9, "Version with rebuild flag", "version", "3.1", "v3.1", True, True),
            (10, "Invalid version", "version", "invalid", None, False, False),
            (11, "Version missing argument", "version", None, None, False, True),
            # Local directory tests
            (12, "Local directory", "local", "/path/to/sql", "v3.1", False, True),
            (13, "Local directory with rebuild", "local", "/path", "v3.1", True, True),
            # Remote git tests
            (14, "Remote", "remote", "url.git", "v3.1", False, True),
            (15, "Remote with rebuild", "remote", "url.git", "v3.1", True, True),
        ],
    )
    @patch("opensearchsql_cli.main.sql_connection")
    @patch("opensearchsql_cli.main.sql_library_manager")
    @patch("opensearchsql_cli.main.sql_version")
    @patch("opensearchsql_cli.main.config_manager")
    @patch("opensearchsql_cli.main.console")
    @patch("opensearchsql_cli.main.pyfiglet.figlet_format")
    def test_others_commands(
        self,
        mock_figlet,
        mock_console,
        mock_config_manager,
        mock_version_manager,
        mock_library_manager,
        mock_sql_connection,
        test_id,
        description,
        command_type,
        value,
        expected_display,
        rebuild,
        version_success,
    ):
        """
        Test for language, format, and version commands.

        Args:
            command_type: Type of command to test ('language', 'format', or 'version')
            value: Value to pass to the command (or None for missing argument test)
            expected_display: Expected display value (or None for missing argument test)
            rebuild: Whether to include the --rebuild flag (for version command only)
            version_success: Whether version setting should succeed (for version command only)
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # Map command type to flag
        flag_map = {
            "language": "-l",
            "format": "-f",
            "version": "--version",
            "local": "--local",
            "remote": "--remote",
        }
        flag = flag_map[command_type]

        if value is None:
            # Test missing argument case
            result, test_result = self._check_missing_arg(
                flag, f"Option '{flag}' requires an argument"
            )
        else:
            # Setup test environment with appropriate parameters based on command type
            kwargs = {
                "endpoint": "test:9200",
                command_type: value,
            }

            # Add rebuild flag if needed
            if rebuild:
                kwargs["rebuild"] = True
                kwargs["version_success"] = version_success

            cli, command_args = self.setup_cli_test(
                mock_console,
                mock_config_manager,
                mock_version_manager,
                mock_library_manager,
                mock_sql_connection,
                mock_figlet,
                **kwargs,
            )

            result = runner.invoke(cli.app, command_args)
            assert result.exit_code == 0

            # Verify behavior based on command type
            if command_type == "language":
                if expected_display:
                    mock_console.print.assert_any_call(
                        f"[green]Language:[/green] [dim white]{expected_display}[/dim white]"
                    )
                    # Verify that shell.start was called with the correct language parameter
                    cli.shell.start.assert_called_once_with(value, "table")
                test_result = f"Language {value} displayed as {expected_display}"

            elif command_type == "format":
                if expected_display:
                    mock_console.print.assert_any_call(
                        f"[green]Format:[/green] [dim white]{expected_display}[/dim white]"
                    )
                    # Verify that shell.start was called with the correct format parameter
                    cli.shell.start.assert_called_once_with("ppl", value)
                test_result = f"Format {value} displayed as {expected_display}"

            elif command_type == "version":
                # Verify that set_version was called with the correct parameters
                # Check if any of the version setting methods were called
                if version_success:
                    # Check if set_version was called with keyword arguments
                    mock_version_manager.set_version.assert_called_once_with(
                        version=value, rebuild=rebuild
                    )

                    mock_console.print.assert_any_call(
                        f"[green]SQL:[/green] [dim white]{expected_display}[/dim white]"
                    )
                    test_result = f"Version {value} set successfully"
                else:
                    mock_version_manager.set_version.assert_called_once_with(
                        version=value, rebuild=rebuild
                    )
                    test_result = f"Version {value} failed as expected"

            elif command_type == "local":
                # Verify that set_local_version was called with the correct parameters
                if version_success:
                    # Check if set_local_version was called with correct parameters
                    mock_version_manager.set_local_version.assert_called_once_with(
                        value, rebuild=rebuild
                    )

                    test_result = f"Local directory {value} set successfully"
                else:
                    mock_version_manager.set_local_version.assert_called_once_with(
                        value, rebuild=rebuild
                    )
                    test_result = f"Local directory {value} failed as expected"

            elif command_type == "remote":
                # Verify that set_remote_version was called with the correct parameters
                if version_success:
                    # Get git URL from value
                    git_url = value

                    # Get branch name from config (default to "main")
                    branch_name = mock_config_manager.get(
                        "SqlVersion", "branch_name", "main"
                    )

                    # Get remote_output from mock_config_manager
                    remote_output = mock_config_manager.get(
                        "SqlVersion", "remote_output", ""
                    )

                    # Check if set_remote_version was called with correct parameters
                    mock_version_manager.set_remote_version.assert_called_once_with(
                        branch_name,
                        git_url,
                        rebuild=rebuild,
                        remote_output=remote_output,
                    )

                    test_result = f"Remote git {value} set successfully"
                else:
                    # Get git URL from value
                    git_url = value

                    # Get branch name from config (default to "main")
                    branch_name = mock_config_manager.get(
                        "SqlVersion", "branch_name", "main"
                    )

                    # Get remote_output from mock_config_manager
                    remote_output = mock_config_manager.get(
                        "SqlVersion", "remote_output", ""
                    )

                    mock_version_manager.set_remote_version.assert_called_once_with(
                        branch_name,
                        git_url,
                        rebuild=rebuild,
                        remote_output=remote_output,
                    )
                    test_result = f"Remote git {value} failed as expected"

        self.print_test_info(f"{description} (Test #{test_id})", test_result)

    @pytest.mark.parametrize(
        "test_id, description, query, language, format, expected_success",
        [
            (
                1,
                "Query command success",
                "SELECT * FROM accounts",
                "sql",
                "table",
                True,
            ),
            (
                2,
                "PPL query command success",
                "source=accounts",
                "ppl",
                "json",
                True,
            ),
            (
                3,
                "Query missing argument",
                None,
                "ppl",
                "table",
                False,
            ),
        ],
    )
    @patch("opensearchsql_cli.main.sql_connection")
    @patch("opensearchsql_cli.main.sql_library_manager")
    @patch("opensearchsql_cli.main.sql_version")
    @patch("opensearchsql_cli.main.config_manager")
    @patch("opensearchsql_cli.main.console")
    @patch("opensearchsql_cli.main.pyfiglet.figlet_format")
    def test_query_command(
        self,
        mock_figlet,
        mock_console,
        mock_config_manager,
        mock_version_manager,
        mock_library_manager,
        mock_sql_connection,
        test_id,
        description,
        query,
        language,
        format,
        expected_success,
    ):
        """
        Test the -q/--query command for executing a query and exiting.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        if query is None:
            # Test missing argument case
            result, test_result = self._check_missing_arg(
                "-q", "Option '-q' requires an argument"
            )
        else:
            # Setup test environment
            cli, command_args = self.setup_cli_test(
                mock_console,
                mock_config_manager,
                mock_version_manager,
                mock_library_manager,
                mock_sql_connection,
                mock_figlet,
                endpoint="test:9200",
                language=language,
                format=format,
                connection_success=True,
            )

            # Add query parameter
            command_args.extend(["-q", query])

            # Execute the command
            result = runner.invoke(cli.app, command_args)

            # Verify the result
            assert result.exit_code == 0

            # Verify that execute_query was called with the correct query
            cli.shell.execute_query.assert_called_once_with(query)

            # Verify that shell.start was NOT called (CLI should exit after executing query)
            cli.shell.start.assert_not_called()

            test_result = f"Query '{query}' executed successfully with language={language}, format={format}"

        self.print_test_info(f"{description} (Test #{test_id})", test_result)
