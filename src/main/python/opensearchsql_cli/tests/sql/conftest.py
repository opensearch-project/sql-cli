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
    mock.stdout.readline.return_value = "Gateway Server Started"
    mock.poll.return_value = None
    return mock


@pytest.fixture
def mock_process_timeout():
    """
    Fixture that returns a mock subprocess.Popen instance that times out.
    """
    mock = MagicMock()
    mock.stdout.readline.return_value = "Some other output"
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
