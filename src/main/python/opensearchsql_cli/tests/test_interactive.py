"""
Tests for Interactive Shell

This module contains tests for the InteractiveShell class that handles
interactive shell functionality for OpenSearch SQL CLI.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, call
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import PromptSession

from ..interactive_shell import InteractiveShell
from ..literals.opensearch_literals import Literals


class TestInteractiveShell:
    """
    Test class for InteractiveShell functionality.
    """

    def test_init(self, mock_sql_connection, mock_saved_queries):
        """Test initialization of InteractiveShell."""
        with patch("os.path.exists", return_value=False), patch(
            "builtins.open", MagicMock()
        ) as mock_open:

            shell = InteractiveShell(mock_sql_connection, mock_saved_queries)

            # Verify history file creation
            mock_open.assert_called_once()

            # Verify initial state
            assert shell.language_mode == "PPL"
            assert shell.is_ppl_mode is True
            assert shell.format == "table"
            assert shell.is_vertical is False
            assert shell.latest_query is None
            assert shell.sql_connection == mock_sql_connection
            assert shell.saved_queries == mock_saved_queries

    @patch("opensearchsql_cli.interactive_shell.console")
    def test_display_help_shell(self, mock_console):
        """Test display_help_shell static method."""
        InteractiveShell.display_help_shell()
        mock_console.print.assert_called_once()
        # Verify help text contains key commands
        help_text = mock_console.print.call_args[0][0]
        assert "Commands:" in help_text
        assert "Execute query" in help_text
        assert "Change language: PPL, SQL" in help_text
        assert "Change format: JSON, Table, CSV" in help_text
        assert "Toggle vertical display mode" in help_text
        assert "Save the latest query result" in help_text
        assert "Exit interactive mode" in help_text

    @pytest.mark.parametrize(
        "language_mode, expected_lang, mock_keywords, mock_functions, expected_keywords, expected_functions",
        [
            (
                "PPL",
                "ppl",
                ["source", "where", "fields"],
                ["count", "sum", "avg"],
                ["SOURCE", "WHERE"],
                ["COUNT", "SUM"],
            ),
            (
                "SQL",
                "sql",
                ["SELECT", "FROM", "WHERE"],
                ["COUNT", "SUM", "AVG"],
                ["SELECT", "FROM"],
                ["COUNT", "SUM"],
            ),
        ],
    )
    @patch("opensearchsql_cli.interactive_shell.Literals.get_literals")
    def test_auto_completer(
        self,
        mock_get_literals,
        language_mode,
        expected_lang,
        mock_keywords,
        mock_functions,
        expected_keywords,
        expected_functions,
    ):
        """Test auto_completer method with different language modes."""
        mock_get_literals.return_value = {
            "keywords": mock_keywords,
            "functions": mock_functions,
        }

        shell = InteractiveShell(MagicMock(), MagicMock())
        completer = shell.auto_completer(language_mode)

        # Verify get_literals was called with correct language
        mock_get_literals.assert_called_once_with(expected_lang)

        # Verify completer contains keywords, functions, and commands
        words = completer.words
        for keyword in expected_keywords:
            assert keyword in words  # Keywords
        for function in expected_functions:
            assert function in words  # Functions
        assert "-l" in words  # Command
        assert "-f" in words  # Command
        assert "help" in words  # Command
        assert "--save" in words  # Option

    @pytest.mark.parametrize(
        "query, is_explain",
        [
            ("source=test | fields name", False),
            ("explain source=test | fields name", True),
        ],
    )
    @patch("opensearchsql_cli.interactive_shell.ExecuteQuery")
    def test_execute_query(self, mock_execute_query, query, is_explain):
        """Test execute_query method with different query types."""
        mock_execute_query.execute_query.return_value = (
            True,
            "result",
            "formatted_result",
        )

        shell = InteractiveShell(MagicMock(), MagicMock())
        shell.is_ppl_mode = True
        shell.format = "table"
        shell.is_vertical = False

        result = shell.execute_query(query)

        # Verify query was stored
        assert shell.latest_query == query

        # Verify ExecuteQuery.execute_query was called with correct parameters
        mock_execute_query.execute_query.assert_called_once()
        args = mock_execute_query.execute_query.call_args[0]
        assert args[1] == query  # query
        assert args[2] is True  # is_ppl_mode
        assert args[3] is is_explain  # is_explain
        assert args[4] == "table"  # format
        assert args[5] is False  # is_vertical

        # Verify result
        assert result is True

    @patch("opensearchsql_cli.interactive_shell.ExecuteQuery")
    @patch("opensearchsql_cli.interactive_shell.console")
    def test_execute_query_exception(self, mock_console, mock_execute_query):
        """Test execute_query method with exception."""
        mock_execute_query.execute_query.side_effect = Exception("Test error")

        shell = InteractiveShell(MagicMock(), MagicMock())
        shell.is_ppl_mode = True
        shell.format = "table"
        shell.is_vertical = False

        result = shell.execute_query("source=test | fields name")

        # Verify query was stored
        assert shell.latest_query == "source=test | fields name"

        # Verify error was printed
        mock_console.print.assert_called_once()
        error_msg = mock_console.print.call_args[0][0]
        assert "ERROR:" in error_msg
        assert "Test error" in error_msg

        # Verify result
        assert result is False

    @pytest.mark.parametrize(
        "language, format_option, expected_language_mode, expected_is_ppl, expected_format, is_language_valid, is_format_valid",
        [
            ("ppl", "json", "PPL", True, "json", True, True),
            ("sql", "table", "SQL", False, "table", True, True),
            ("invalid", "table", "PPL", True, "table", False, True),
            ("ppl", "invalid", "PPL", True, "table", True, False),
        ],
    )
    @patch("opensearchsql_cli.interactive_shell.PromptSession")
    @patch("opensearchsql_cli.interactive_shell.config_manager")
    @patch("opensearchsql_cli.interactive_shell.console")
    def test_start_language_format(
        self,
        mock_console,
        mock_config_manager,
        mock_prompt_session,
        language,
        format_option,
        expected_language_mode,
        expected_is_ppl,
        expected_format,
        is_language_valid,
        is_format_valid,
    ):
        """Test start method with various language and format combinations."""
        # Setup mocks
        mock_session = MagicMock()
        mock_prompt_session.return_value = mock_session
        mock_session.prompt.side_effect = ["exit"]  # Exit after first prompt
        mock_config_manager.get_boolean.return_value = False

        # Create shell and start
        shell = InteractiveShell(MagicMock(), MagicMock())
        shell.start(language, format_option)

        # Verify language and format were set correctly
        assert shell.language_mode == expected_language_mode
        assert shell.is_ppl_mode == expected_is_ppl
        assert shell.format == expected_format

        # Verify prompt session was created and used
        mock_prompt_session.assert_called_once()
        mock_session.prompt.assert_called_once()

        # Verify error messages if applicable
        if not is_language_valid:
            mock_console.print.assert_any_call(
                f"[bold red]Invalid Language:[/bold red] [red]{language}.[/red] [bold red]\nDefaulting to PPL.[/bold red]"
            )

        if not is_format_valid:
            mock_console.print.assert_any_call(
                f"[bold red]Invalid Format:[/bold red] [red]{format_option}.[/red] [bold red]\nDefaulting to Table.[/bold red]"
            )

        # Verify exit message was printed
        mock_console.print.assert_any_call(
            "[bold green]\nDisconnected. Goodbye!!!\n[/bold green]"
        )

    @patch("opensearchsql_cli.interactive_shell.PromptSession")
    @patch("opensearchsql_cli.interactive_shell.config_manager")
    def test_start_command_processing(self, mock_config_manager, mock_prompt_session):
        """Test start method command processing."""
        # Setup mocks
        mock_session = MagicMock()
        mock_prompt_session.return_value = mock_session

        # Simulate user inputs
        mock_session.prompt.side_effect = [
            "help",
            "-l sql",
            "-l ppl",
            "-f json",
            "-f invalid",
            "-v",
            "-s --list",
            "-s --save test",
            "-s --load test",
            "-s --remove test",
            "-s",
            "select * from test",
            "exit",
        ]

        mock_config_manager.get_boolean.return_value = False

        # Create shell with mocked dependencies
        shell = InteractiveShell(MagicMock(), MagicMock())
        shell.execute_query = MagicMock(return_value=True)
        shell.latest_query = "select * from test"

        # Configure the loading_query mock to return expected values
        shell.saved_queries.loading_query.return_value = (
            True,
            "select * from test",
            "result",
            "SQL",
        )

        # Start the shell
        shell.start("ppl", "table")

        # Verify saved queries methods were called
        shell.saved_queries.list_saved_queries.assert_called_once()
        shell.saved_queries.saving_query.assert_called_once_with(
            "test", "select * from test", "PPL"
        )
        shell.saved_queries.loading_query.assert_called_once()
        shell.saved_queries.removing_query.assert_called_once_with("test")

        # Verify query execution
        shell.execute_query.assert_called_once_with("select * from test")

    @patch("opensearchsql_cli.interactive_shell.PromptSession")
    @patch("opensearchsql_cli.interactive_shell.config_manager")
    def test_start_keyboard_interrupt(self, mock_config_manager, mock_prompt_session):
        """Test start method with keyboard interrupt."""
        # Setup mocks
        mock_session = MagicMock()
        mock_prompt_session.return_value = mock_session
        mock_session.prompt.side_effect = KeyboardInterrupt()
        mock_config_manager.get_boolean.return_value = False

        # Create shell and start
        shell = InteractiveShell(MagicMock(), MagicMock())
        shell.start("ppl", "table")

        # Verify prompt was called
        mock_session.prompt.assert_called_once()
