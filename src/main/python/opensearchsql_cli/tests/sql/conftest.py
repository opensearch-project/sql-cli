"""
Pytest fixtures for SQL tests.

This module contains fixtures used by the SQL tests.
"""

import pytest
import subprocess
from unittest.mock import MagicMock, PropertyMock, patch


# Fixtures for test_sql_library.py
@pytest.fixture
def mock_process():
    """
    Fixture that returns a mock subprocess.Popen instance.
    """
    mock = MagicMock()
    mock.stdout.readline.side_effect = ["Gateway Server Started"]
    mock.poll.return_value = None
    return mock


@pytest.fixture
def mock_process_timeout():
    """
    Fixture that returns a mock subprocess.Popen instance that times out.
    """
    mock = MagicMock()
    mock.stdout.readline.side_effect = ["Some other output"]
    mock.poll.return_value = None
    return mock


# Fixtures for test_sql_connection.py
@pytest.fixture
def mock_java_gateway():
    """
    Fixture that returns a mock JavaGateway instance.
    """
    mock = MagicMock()
    mock.entry_point.initializeConnection.return_value = True
    mock.entry_point.initializeAwsConnection.return_value = True
    mock.entry_point.queryExecution.return_value = '{"result": "test data"}'
    return mock


@pytest.fixture
def mock_sql_library_manager():
    """
    Fixture that returns a mock SqlLibraryManager instance.
    """
    mock = MagicMock()
    mock.started = True
    mock.start.return_value = True
    return mock


# Fixtures for test_sql_version.py
@pytest.fixture
def mock_get_all_versions():
    """Mock the get_all_versions method to return a fixed list of versions."""
    with patch("opensearchsql_cli.sql.sql_version.SqlVersion.get_all_versions") as mock:
        mock.return_value = ["3.1.0.0", "2.19.0.0"]
        yield mock
