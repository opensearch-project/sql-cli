"""
Tests for the execute_query module.

This module contains tests for the query execution functionality.
"""

import pytest
import json
from rich.console import Console
from unittest.mock import patch, MagicMock
from opensearchsql_cli.query.execute_query import ExecuteQuery
from opensearchsql_cli.query.query_results import QueryResults
from opensearchsql_cli.query.explain_results import ExplainResults

# Create a console instance for printing
console = Console()


class TestQuery:
    """
    Test class for ExecuteQuery methods.
    """

    def execute_query_test(
        self,
        mock_console,
        mock_response,
        test_case_num,
        test_case_name,
        query,
        is_ppl_mode=True,
        is_explain=False,
        format="table",
        is_vertical=False,
        expected_success=True,
    ):
        """
        Dynamic function to execute query tests with different parameters.

        Args:
            mock_console: Mocked console object
            mock_response: Mock response to be returned by the query executor
            test_case_num: Test case number for display
            test_case_name: Test case name for display
            query: Query to execute
            is_ppl_mode: Whether to use PPL mode (True) or SQL mode (False)
            is_explain: Whether to use explain mode
            format: Output format (table, csv, json)
            is_vertical: Whether to use vertical table format
            expected_success: Whether the query is expected to succeed
        """
        # Arrange
        mock_connection = MagicMock()
        mock_print = MagicMock()

        # Mock the query_executor to return the provided response
        mock_connection.query_executor.return_value = mock_response

        # Print the test case header and details
        print(f"\n\n=== Test Case {test_case_num}: {test_case_name} ===")
        print(f"Query: {query}")
        print(f"Mode: {'PPL' if is_ppl_mode else 'SQL'}")
        print(f"Format: {format.upper()}")
        print(f"Vertical: {is_vertical}")
        print(f"Explain: {is_explain}")
        print(f"Expected Success: {expected_success}")

        # Act
        success, result, formatted_result = ExecuteQuery.execute_query(
            connection=mock_connection,
            query=query,
            is_ppl_mode=is_ppl_mode,
            is_explain=is_explain,
            format=format,
            is_vertical=is_vertical,
            print_function=mock_print,
        )

        # Display the result based on format and response type
        print("\nResult:")
        if format == "table":
            table_data = QueryResults.table_format(mock_response, is_vertical)
            QueryResults.display_table_result(table_data, console.print)
        elif format == "json" and is_explain:
            if "calcite" in mock_response:
                formatted_explain = ExplainResults.explain_calcite(mock_response)
                print(formatted_explain)
            elif "root" in mock_response:
                formatted_explain = ExplainResults.explain_legacy(mock_response)
                print(formatted_explain)
            else:
                print(mock_response)
        else:
            print(mock_response)

        # Assert
        assert success is expected_success
        assert result == mock_response
        print(f"\nSuccess: {success} (Expected: {expected_success})")

        # Verify the connection was called with the correct parameters
        mock_connection.query_executor.assert_called_once_with(
            query, is_ppl_mode, format
        )
        print(
            f"Query Executor Called: query={query}, is_ppl_mode={is_ppl_mode}, format={format}"
        )

        # Verify the print function was called with the expected arguments
        if expected_success:
            # Check that the Result: message was printed
            mock_print.assert_any_call("Result:\n")
            print("Result message printed")
        else:
            # Check for error messages based on the response content
            if "SyntaxCheckException" in mock_response:
                error_parts = mock_response.split("SyntaxCheckException:", 1)
                mock_print.assert_any_call(
                    f"[bold red]Syntax Error: [/bold red][red]{error_parts[1].strip()}[/red]\n"
                )
                print(f"Syntax Error: {error_parts[1].strip()}")
            elif "SemanticCheckException" in mock_response:
                error_parts = mock_response.split("SemanticCheckException:", 1)
                mock_print.assert_any_call(
                    f"[bold red]Semantic Error: [/bold red][red]{error_parts[1].strip()}[/red]\n"
                )
                print(f"Semantic Error: {error_parts[1].strip()}")
            elif "index_not_found_exception" in mock_response:
                mock_print.assert_any_call("[bold red]Index does not exist[/bold red]")
                print("Index does not exist")
            elif '"statement" is null' in mock_response:
                mock_print.assert_any_call("[bold red]Statement is null[/bold red]")
                print("Statement is null")

        # Verify all calls to mock_print
        assert mock_print.call_count >= 1
        print(f"Print function called {mock_print.call_count} times")
        print("=" * 50)

    # Comprehensive parameterized test covering all test cases
    @pytest.mark.parametrize(
        "test_case_num, test_case_name, query, is_ppl_mode, is_explain, format, is_vertical, expected_success, fixture_name",
        [
            # PPL test
            (
                1,
                "PPL Table",
                "source=employees",
                True,
                False,
                "table",
                False,
                True,
                "mock_json_response",
            ),
            (
                2,
                "PPL Vertical Table",
                "source=employees",
                True,
                False,
                "table",
                True,
                True,
                "mock_json_response",
            ),
            (
                3,
                "PPL CSV",
                "source=employees",
                True,
                False,
                "csv",
                False,
                True,
                "mock_csv_response",
            ),
            (
                4,
                "PPL JSON",
                "source=employees",
                True,
                False,
                "json",
                False,
                True,
                "mock_json_response",
            ),
            (
                5,
                "PPL Explain Calcite",
                "explain source=employees",
                True,
                True,
                "json",
                False,
                True,
                "mock_calcite_explain",
            ),
            (
                6,
                "PPL Syntax Error",
                "invalid",
                True,
                False,
                "json",
                False,
                False,
                "mock_syntax_error_response",
            ),
            (
                7,
                "PPL Semantic Error",
                "source=employees | fields unknown_field",
                True,
                False,
                "json",
                False,
                False,
                "mock_semantic_error_response",
            ),
            (
                8,
                "PPL Index Not Found Error",
                "source=nonexistent_index",
                True,
                False,
                "json",
                False,
                False,
                "mock_index_not_found_response",
            ),
            (
                9,
                "PPL Null Statement Error",
                ";",
                True,
                False,
                "json",
                False,
                False,
                "mock_null_statement_response",
            ),
            # SQL test
            (
                10,
                "SQL Table",
                "SELECT * FROM employees",
                False,
                False,
                "table",
                False,
                True,
                "mock_json_response",
            ),
            (
                11,
                "SQL Vertical Table",
                "SELECT * FROM employees",
                False,
                False,
                "table",
                True,
                True,
                "mock_json_response",
            ),
            (
                12,
                "SQL CSV",
                "SELECT * FROM employees",
                False,
                False,
                "csv",
                False,
                True,
                "mock_csv_response",
            ),
            (
                13,
                "SQL JSON",
                "SELECT * FROM employees",
                False,
                False,
                "json",
                False,
                True,
                "mock_json_response",
            ),
            (
                14,
                "SQL Explain Legacy",
                "EXPLAIN SELECT * FROM employees",
                False,
                True,
                "json",
                False,
                True,
                "mock_legacy_explain",
            ),
            (
                15,
                "SQL Syntax Error",
                "SELECT * FROMM employees",
                False,
                False,
                "json",
                False,
                False,
                "mock_syntax_error_response",
            ),
            (
                16,
                "SQL Semantic Error",
                "SELECT unknown_field FROM employees",
                False,
                False,
                "json",
                False,
                False,
                "mock_semantic_error_response",
            ),
            (
                17,
                "SQL Index Not Found Error",
                "SELECT * FROM nonexistent_index",
                False,
                False,
                "json",
                False,
                False,
                "mock_index_not_found_response",
            ),
            (
                18,
                "SQL Null Statement Error",
                ";",
                False,
                False,
                "json",
                False,
                False,
                "mock_null_statement_response",
            ),
        ],
    )
    @patch("opensearchsql_cli.query.execute_query.console")
    def test_query_parameterized(
        self,
        mock_console,
        test_case_num,
        test_case_name,
        query,
        is_ppl_mode,
        is_explain,
        format,
        is_vertical,
        expected_success,
        fixture_name,
        request,
    ):
        """
        Parameterized test for executing queries with different configurations.

        Args:
            mock_console: Mocked console object
            test_case_num: Test case number for display
            test_case_name: Test case name for display
            query: Query to execute
            is_ppl_mode: Whether to use PPL mode (True) or SQL mode (False)
            is_explain: Whether to use explain mode
            format: Output format (table, csv, json)
            is_vertical: Whether to use vertical table format
            expected_success: Whether the query is expected to succeed
            fixture_name: Name of the fixture to use for mock response
            request: pytest request fixture for accessing other fixtures
        """
        # Get the mock response from the fixture
        mock_response = request.getfixturevalue(fixture_name)

        # Execute the test
        self.execute_query_test(
            mock_console=mock_console,
            mock_response=mock_response,
            test_case_num=test_case_num,
            test_case_name=test_case_name,
            query=query,
            is_ppl_mode=is_ppl_mode,
            is_explain=is_explain,
            format=format,
            is_vertical=is_vertical,
            expected_success=expected_success,
        )
