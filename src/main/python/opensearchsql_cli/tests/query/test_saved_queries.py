"""
Tests for saved queries functionality.

This module contains tests for the saved query commands (-s --save, -s --load, -s --remove, -s --list).
"""

import pytest
import os
import json
from opensearchsql_cli.query.saved_queries import SavedQueries
from unittest.mock import patch, MagicMock


class TestSavedQueries:
    """
    Test class for saved queries functionality.
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
            TestSavedQueries.test_case_num += 1
            print(
                f"\n=== Test Case #{TestSavedQueries.test_case_num}: {description} ==="
            )
        else:
            print(f"Result: {result}")

    @pytest.mark.parametrize(
        "test_id, description, expected_result",
        [
            (1, "Initialize SavedQueries", "Directory and file created successfully"),
        ],
    )
    def test_init_creates_directory_and_file(
        self, test_id, description, expected_result, temp_dir
    ):
        """
        Test that the SavedQueries constructor creates the directory and file if they don't exist.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # Create a SavedQueries instance
        saved_queries = SavedQueries(base_dir=temp_dir)

        # Check that the directory and file were created
        assert os.path.exists(temp_dir)
        assert os.path.exists(os.path.join(temp_dir, "saved.txt"))

        # Check that the file contains an empty dictionary
        with open(os.path.join(temp_dir, "saved.txt"), "r") as f:
            data = json.load(f)
            assert data == {}

        self.print_test_info(f"{description} (Test #{test_id})", expected_result)

    @pytest.mark.parametrize(
        "test_id, description, query_name, query, language, expected_success, expected_result",
        [
            (
                1,
                "Save Query - Success",
                "test_query",
                "source=test",
                "PPL",
                True,
                "Query saved successfully",
            ),
            (
                2,
                "Save Query - Already Exists",
                "test_query",
                "source=test2",
                "PPL",
                False,
                "Query not saved as expected",
            ),
            (
                3,
                "Replace Query - Success",
                "test_query",
                "source=test2",
                "PPL",
                True,
                "Query replaced successfully",
            ),
            (
                4,
                "Replace Query - Not Exists",
                "nonexistent_query",
                "source=test",
                "PPL",
                False,
                "Query not replaced as expected",
            ),
        ],
    )
    def test_save_commands(
        self,
        test_id,
        description,
        query_name,
        query,
        language,
        expected_success,
        expected_result,
        saved_queries,
        mock_console,
    ):
        """
        Test saving and replacing queries.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # For "Already Exists" test, save a query first
        if "Already Exists" in description:
            saved_queries.save_query(query_name, "source=test", "PPL")

            # Try to save another query with the same name
            result = saved_queries.save_query(query_name, query, language)

            # Check that the query was not saved
            assert result is expected_success
            mock_console.print.assert_any_call(
                f"A query with name '[green]{query_name}[/green]' already exists."
            )

        # For "Replace" tests
        elif "Replace" in description:
            # For "Replace - Success", save a query first
            if expected_success:
                saved_queries.save_query(query_name, "source=test", "PPL")

            # Replace the query
            result = saved_queries.replace_query(query_name, query, language)

            # Check that the query was replaced or not based on expected_success
            assert result is expected_success

            if expected_success:
                mock_console.print.assert_called_with(
                    f"Query '[green]{query_name}[/green]' replaced"
                )

                # Check that the query was updated in the file
                saved_data = saved_queries._load_saved_data()
                assert query_name in saved_data
                assert saved_data[query_name]["query"] == query
            else:
                mock_console.print.assert_called_with(
                    f"[bold red]ERROR:[/bold red] [red]No query named[/red] '[white]{query_name}[/white]' [red]exists.[/red]"
                )

        # For regular "Save" test
        else:
            # Save a query
            result = saved_queries.save_query(query_name, query, language)

            # Check that the query was saved
            assert result is expected_success
            mock_console.print.assert_called_with(
                f"Query saved as '[green]{query_name}[/green]'"
            )

            # Check that the query was saved to the file
            saved_data = saved_queries._load_saved_data()
            assert query_name in saved_data
            assert saved_data[query_name]["query"] == query
            assert saved_data[query_name]["language"] == language
            assert "timestamp" in saved_data[query_name]

        self.print_test_info(f"{description} (Test #{test_id})", expected_result)

    @pytest.mark.parametrize(
        "test_id, description, query_name, query, language, expected_success, expected_result",
        [
            (
                1,
                "Load Query - Success",
                "test_query",
                "source=test",
                "PPL",
                True,
                "Query loaded successfully",
            ),
            (
                2,
                "Load Query - Not Exists",
                "nonexistent_query",
                None,
                None,
                False,
                "Query not loaded as expected",
            ),
        ],
    )
    def test_load_commands(
        self,
        test_id,
        description,
        query_name,
        query,
        language,
        expected_success,
        expected_result,
        saved_queries,
        mock_console,
    ):
        """
        Test loading saved queries.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # For "Success" test, save a query first
        if expected_success:
            saved_queries.save_query(query_name, query, language)

        # Load the query
        success, query_data = saved_queries.load_query(query_name)

        # Check that the query was loaded or not based on expected_success
        assert success is expected_success

        if expected_success:
            assert query_data["query"] == query
            assert query_data["language"] == language
        else:
            assert query_data is None
            mock_console.print.assert_called_with(
                f"[bold red]ERROR:[/bold red] Saved Query '[green]{query_name}[/green]' does not exist."
            )

        self.print_test_info(f"{description} (Test #{test_id})", expected_result)

    @pytest.mark.parametrize(
        "test_id, description, query_name, query, language, confirm, expected_success, expected_result",
        [
            (
                1,
                "Remove Query - Success",
                "test_query",
                "source=test",
                "PPL",
                None,
                True,
                "Query removed successfully",
            ),
            (
                2,
                "Remove Query - Not Exists",
                "nonexistent_query",
                None,
                None,
                None,
                False,
                "Query not removed as expected",
            ),
            (
                3,
                "Removing Query - Confirm",
                "test_query",
                "source=test",
                "PPL",
                "y",
                True,
                "Query removed after confirmation",
            ),
            (
                4,
                "Removing Query - No Confirm",
                "test_query",
                "source=test",
                "PPL",
                "n",
                False,
                "Query not removed after declining",
            ),
            (
                5,
                "Removing Query - Not Exists",
                "nonexistent_query",
                None,
                None,
                None,
                False,
                "Query not found error displayed correctly",
            ),
        ],
    )
    def test_remove_commands(
        self,
        test_id,
        description,
        query_name,
        query,
        language,
        confirm,
        expected_success,
        expected_result,
        saved_queries,
        mock_console,
    ):
        """
        Test removing saved queries.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # For tests that need a query to exist first
        if query and "Not Exists" not in description:
            saved_queries.save_query(query_name, query, language)

        # For tests with confirmation
        if "Confirm" in description:
            with patch("builtins.input", return_value=confirm):
                # Remove the query with confirmation
                result = saved_queries.removing_query(query_name)

                # Check that the query was removed or not based on expected_success
                assert result is expected_success

                if expected_success:
                    mock_console.print.assert_any_call(
                        f"Query '[green]{query_name}[/green]' removed"
                    )

                    # Check that the query was removed from the file
                    saved_data = saved_queries._load_saved_data()
                    assert query_name not in saved_data
                else:
                    mock_console.print.assert_any_call(
                        f"Query '[green]{query_name}[/green]' was [red]NOT[/red] removed."
                    )

                    # Check that the query was not removed from the file
                    if query:
                        saved_data = saved_queries._load_saved_data()
                        assert query_name in saved_data

        # For regular "Remove" tests
        elif "Not Exists" in description:
            if "removing_query" in description.lower():
                # Try to remove a query that doesn't exist using removing_query
                result = saved_queries.removing_query(query_name)

                # Check that the query was not removed
                assert result is expected_success
                mock_console.print.assert_called_with(
                    f"[bold red]ERROR:[/bold red] [red]Query[/red] '[green]{query_name}[/green]' [red]not found.[/red]"
                )
            else:
                # Try to remove a query that doesn't exist using remove_query
                result = saved_queries.remove_query(query_name)

                # Check that the query was not removed
                assert result is expected_success
                mock_console.print.assert_called_with(
                    f"[bold red]ERROR:[/bold red] Saved Query '[green]{query_name}[/green]' does not exist."
                )
        else:
            # Remove the query
            result = saved_queries.remove_query(query_name)

            # Check that the query was removed
            assert result is expected_success
            mock_console.print.assert_called_with(
                f"Query '[green]{query_name}[/green]' removed"
            )

            # Check that the query was removed from the file
            saved_data = saved_queries._load_saved_data()
            assert query_name not in saved_data

        self.print_test_info(f"{description} (Test #{test_id})", expected_result)

    @pytest.mark.parametrize(
        "test_id, description, queries, expected_success, expected_result",
        [
            (
                1,
                "List Queries - Multiple",
                [
                    ("test_query1", "source=test1", "PPL"),
                    ("test_query2", "source=test2", "PPL"),
                ],
                True,
                "Queries listed successfully",
            ),
            (
                2,
                "List Saved Queries - Formatted",
                [
                    ("test_query1", "source=test1", "PPL"),
                    ("test_query2", "source=test2", "PPL"),
                ],
                True,
                "Queries listed with formatting successfully",
            ),
            (
                3,
                "List Saved Queries - Empty",
                [],
                False,
                "Empty list handled correctly",
            ),
        ],
    )
    def test_list_commands(
        self,
        test_id,
        description,
        queries,
        expected_success,
        expected_result,
        saved_queries,
        mock_console,
    ):
        """
        Test listing saved queries.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # Save queries if needed
        for query_name, query, language in queries:
            saved_queries.save_query(query_name, query, language)

        if "Formatted" in description:
            # List the queries with formatted output
            result = saved_queries.list_saved_queries()

            # Check that the queries were listed
            assert result is expected_success

            if expected_success:
                for query_name, query, _ in queries:
                    mock_console.print.assert_any_call(
                        f"\n- [green]{query_name}[/green]"
                    )
                    mock_console.print.assert_any_call(f"\t[yellow]{query}[/yellow]")
            else:
                mock_console.print.assert_called_with(
                    "[yellow]No saved queries found.[/yellow]"
                )

        elif "Empty" in description:
            # List the queries when there are none
            result = saved_queries.list_saved_queries()

            # Check that no queries were listed
            assert result is expected_success
            mock_console.print.assert_called_with(
                "[yellow]No saved queries found.[/yellow]"
            )

        else:
            # List the queries
            saved_data = saved_queries.list_queries()

            # Check that the queries are listed
            for query_name, query, language in queries:
                assert query_name in saved_data
                assert saved_data[query_name]["query"] == query

        self.print_test_info(f"{description} (Test #{test_id})", expected_result)

    @pytest.mark.parametrize(
        "test_id, description, query_name, query, language, confirm, expected_success, expected_result",
        [
            (
                1,
                "Saving Query - Replace Confirmed",
                "test_query",
                "source=test2",
                "PPL",
                "y",
                True,
                "Query replaced after confirmation",
            ),
            (
                2,
                "Saving Query - Replace Declined",
                "test_query",
                "source=test2",
                "PPL",
                "n",
                False,
                "Query not replaced after declining",
            ),
            (
                3,
                "Saving Query - No Query",
                "test_query",
                None,
                "PPL",
                None,
                False,
                "Error message displayed correctly",
            ),
        ],
    )
    def test_saving_query_commands(
        self,
        test_id,
        description,
        query_name,
        query,
        language,
        confirm,
        expected_success,
        expected_result,
        saved_queries,
        mock_console,
    ):
        """
        Test saving queries with confirmation.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # For tests that need a query to exist first
        if "No Query" not in description:
            saved_queries.save_query(query_name, "source=test", "PPL")

        # For tests with confirmation
        if confirm:
            with patch("builtins.input", return_value=confirm):
                # Save another query with the same name
                result = saved_queries.saving_query(query_name, query, language)

                # Check that the query was replaced or not based on expected_success
                assert result is expected_success

                if expected_success:
                    mock_console.print.assert_any_call(
                        f"Query '[green]{query_name}[/green]' replaced"
                    )

                    # Check that the query was updated in the file
                    saved_data = saved_queries._load_saved_data()
                    assert query_name in saved_data
                    assert saved_data[query_name]["query"] == query
                else:
                    mock_console.print.assert_any_call(
                        f"Query '[green]{query_name}[/green]' was [red]NOT[/red] replaced."
                    )

                    # Check that the query was not updated in the file
                    saved_data = saved_queries._load_saved_data()
                    assert query_name in saved_data
                    assert saved_data[query_name]["query"] == "source=test"
        else:
            # Try to save a query when there's no query to save
            result = saved_queries.saving_query(query_name, query, language)

            # Check that the query was not saved
            assert result is expected_success
            mock_console.print.assert_called_with(
                "[bold red]ERROR:[/bold red] [red]Please execute a query first.[/red]"
            )

        self.print_test_info(f"{description} (Test #{test_id})", expected_result)

    @pytest.mark.parametrize(
        "test_id, description, query_name, query, language, mock_result, exception, expected_success, expected_result",
        [
            (
                1,
                "Loading Query - Success",
                "test_query",
                "source=test",
                "PPL",
                (True, "result", "formatted_result"),
                None,
                True,
                "Query loaded and executed successfully",
            ),
            (
                2,
                "Loading Query - Not Exists",
                "nonexistent_query",
                None,
                None,
                None,
                None,
                False,
                "Query not loaded as expected",
            ),
            (
                3,
                "Loading Query - Execution Error",
                "test_query",
                "source=test",
                "PPL",
                None,
                Exception("Test exception"),
                False,
                "Error handled correctly",
            ),
        ],
    )
    def test_loading_query_commands(
        self,
        test_id,
        description,
        query_name,
        query,
        language,
        mock_result,
        exception,
        expected_success,
        expected_result,
        saved_queries,
        mock_console,
        mock_connection,
    ):
        """
        Test loading and executing saved queries.
        """
        self.print_test_info(f"{description} (Test #{test_id})")

        # For tests that need a query to exist first
        if query and "Not Exists" not in description:
            saved_queries.save_query(query_name, query, language)

        # For tests with mocked execute_query
        if "Success" in description or "Error" in description:
            with patch(
                "opensearchsql_cli.query.execute_query.ExecuteQuery.execute_query"
            ) as mock_execute_query:
                if exception:
                    # Configure the mock to raise an exception when called
                    mock_execute_query.side_effect = exception
                else:
                    # Mock the execute_query method
                    mock_execute_query.return_value = mock_result

                # Load and execute the query
                success, result_query, formatted_result, result_language = (
                    saved_queries.loading_query(query_name, mock_connection)
                )

                # Check that the query was loaded and executed or not based on expected_success
                assert success is expected_success

                if expected_success:
                    assert result_query == query
                    assert formatted_result == "formatted_result"
                    assert result_language == language
                    mock_execute_query.assert_called_once()
                elif exception:
                    assert result_query == ""
                    assert formatted_result == ""
                    assert result_language == ""
                    mock_console.print.assert_called_with(
                        f"[bold red]ERROR:[/bold red] [red] Unable to execute [/red] {str(exception)}"
                    )
        else:
            # Try to load and execute a query that doesn't exist
            success, result_query, formatted_result, result_language = (
                saved_queries.loading_query(query_name, mock_connection)
            )

            # Check that the query was not loaded
            assert success is expected_success
            assert result_query == ""
            assert formatted_result == ""
            assert result_language == ""
            mock_console.print.assert_called_with(
                f"[bold red]ERROR:[/bold red] Saved Query '[green]{query_name}[/green]' does not exist."
            )

        self.print_test_info(f"{description} (Test #{test_id})", expected_result)
