"""
Tests for SQL Library Manager.

This module contains tests for the SQL Library Manager functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from opensearchsql_cli.sql.sql_library_manager import SqlLibraryManager


class TestSqlLibraryManager:
    """
    Test class for SqlLibraryManager.
    """

    @pytest.mark.parametrize(
        "test_id, description, process_fixture, expected_result, expected_started, thread_called",
        [
            (
                1,
                "SQL Library gateway connection: success",
                "mock_process",
                True,
                True,
                True,
            ),
            (
                2,
                "SQL Library gateway connection: fail timeout",
                "mock_process_timeout",
                False,
                False,
                False,
            ),
        ],
    )
    @patch("opensearchsql_cli.sql.sql_library_manager.subprocess.Popen")
    @patch("opensearchsql_cli.sql.sql_library_manager.threading.Thread")
    @patch("opensearchsql_cli.sql.sql_library_manager.logging")
    @patch("opensearchsql_cli.sql.sql_library_manager.os.path.join")
    @patch(
        "opensearchsql_cli.sql.sql_library_manager.SqlLibraryManager._check_port_in_use"
    )
    @patch(
        "opensearchsql_cli.sql.sql_library_manager.SqlLibraryManager._kill_process_on_port"
    )
    def test_gateway_connection(
        self,
        mock_kill_port,
        mock_check_port,
        mock_join,
        mock_logging,
        mock_thread,
        mock_popen,
        test_id,
        description,
        process_fixture,
        expected_result,
        expected_started,
        thread_called,
        request,
    ):
        """
        Test cases for SQL Library gateway connection
        """
        # Setup mocks
        mock_check_port.return_value = True  # Port is in use
        mock_kill_port.return_value = True  # Successfully killed process
        mock_join.return_value = "/mock/path"

        # Mock logger
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger

        # Get the appropriate process fixture
        mock_process = request.getfixturevalue(process_fixture)
        mock_popen.return_value = mock_process

        # Create manager and start
        manager = SqlLibraryManager()
        result = manager.start()

        # Assertions
        assert result is expected_result
        assert manager.started is expected_started
        mock_popen.assert_called_once()

        if thread_called:
            mock_thread.assert_called_once()
