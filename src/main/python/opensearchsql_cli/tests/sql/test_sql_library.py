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
    @patch("opensearchsql_cli.sql.sql_library_manager.sql_version")
    @patch(
        "opensearchsql_cli.sql.sql_library_manager.SqlLibraryManager._kill_process_on_port"
    )
    @patch(
        "opensearchsql_cli.sql.sql_library_manager.SqlLibraryManager._check_port_in_use"
    )
    @patch("opensearchsql_cli.sql.sql_library_manager.os.path.join")
    @patch("opensearchsql_cli.sql.sql_library_manager.logging")
    @patch("opensearchsql_cli.sql.sql_library_manager.threading.Thread")
    @patch("opensearchsql_cli.sql.sql_library_manager.subprocess.Popen")
    @patch("opensearchsql_cli.sql.sql_library_manager.os.makedirs")
    @patch("opensearchsql_cli.sql.sql_library_manager.config_manager")
    def test_gateway_connection(
        self,
        mock_config_manager,
        mock_makedirs,
        mock_popen,
        mock_thread,
        mock_logging,
        mock_join,
        mock_check_port,
        mock_kill_port,
        mock_sql_version,
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
        mock_check_port.return_value = False  # Port is NOT in use to avoid early return
        mock_kill_port.return_value = True  # Successfully killed process
        mock_join.return_value = "/mock/path"
        mock_makedirs.return_value = None  # Mock os.makedirs
        mock_config_manager.get.return_value = ""  # Mock config_manager.get

        # Mock sql_version
        mock_sql_version.version = "3.1.0.0"
        mock_sql_version.get_jar_path.return_value = (
            "/mock/path/opensearchsql-v3.1.0.0.jar"
        )

        # Mock logger
        mock_logger = MagicMock()
        mock_logging.getLogger.return_value = mock_logger
        mock_file_handler = MagicMock()
        mock_logging.FileHandler.return_value = mock_file_handler

        # For test 1 (success), ensure the thread is called
        if test_id == 1:
            # Mock the thread
            thread_instance = MagicMock()
            mock_thread.return_value = thread_instance

            # Mock the process to return "Gateway Server Started"
            mock_process = MagicMock()
            mock_process.stdout.readline.side_effect = ["Gateway Server Started"]
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
        else:
            # For test 2 (timeout), use the fixture
            mock_process = request.getfixturevalue(process_fixture)
            mock_popen.return_value = mock_process

        # Create manager and start
        manager = SqlLibraryManager()
        result = manager.start()

        # Assertions
        assert result is expected_result
        assert manager.started is expected_started

        # Popen should be called in both cases
        mock_popen.assert_called_once()

        # Thread should only be called in the success case
        if thread_called:
            mock_thread.assert_called_once()
