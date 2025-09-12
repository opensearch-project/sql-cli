"""
Tests for SQL Connection.

This module contains tests for the SqlConnection class that handles
connection to SQL library and OpenSearch Cluster configuration.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from opensearchsql_cli.sql.sql_connection import SqlConnection


class TestSqlConnection:
    """
    Test class for SqlConnection functionality.
    """

    @pytest.mark.parametrize(
        "test_id, description, library_started, expected_result",
        [
            (1, "Connect success when library not started", False, True),
            (2, "Connect success when library already started", True, True),
        ],
    )
    @patch("opensearchsql_cli.sql.sql_connection.JavaGateway")
    @patch("opensearchsql_cli.sql.sql_connection.sql_library_manager")
    @patch("opensearchsql_cli.sql.sql_connection.console")
    def test_connect(
        self,
        mock_console,
        mock_library_manager,
        mock_java_gateway,
        test_id,
        description,
        library_started,
        expected_result,
    ):
        """
        Test the connect method of SqlConnection.
        """
        print(f"\n=== Test Case #{test_id}: {description} ===")

        # Setup mocks
        mock_library_manager.started = library_started
        mock_library_manager.start.return_value = True
        mock_gateway = MagicMock()
        mock_java_gateway.return_value = mock_gateway

        # Create connection instance
        connection = SqlConnection()

        # Call connect method
        result = connection.connect()

        # Verify result
        assert result == expected_result
        assert connection.sql_connected == expected_result
        assert connection.sql_lib == mock_gateway

        # Verify library manager interaction
        if not library_started:
            mock_library_manager.start.assert_called_once()
        else:
            mock_library_manager.start.assert_not_called()

        # Verify JavaGateway creation
        mock_java_gateway.assert_called_once()

        print(f"Result: {'Success' if result == expected_result else 'Failed'}")
