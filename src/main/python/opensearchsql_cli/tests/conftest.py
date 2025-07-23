"""
Pytest configuration file for opensearchsql-cli main tests.

This file contains fixtures and configuration for pytest tests.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_sql_connection():
    """
    Fixture that returns a mock SQL connection.
    """
    mock = MagicMock()
    mock.connect.return_value = True
    mock.verify_opensearch_connection.return_value = True
    mock.initialize_sql_library.return_value = True
    mock.version = "2.0.0"
    mock.url = "http://test:9200"
    mock.username = "admin"
    return mock


@pytest.fixture
def mock_sql_library_manager():
    """
    Fixture that returns a mock SQL library manager.
    """
    mock = MagicMock()
    mock.started = False
    return mock


@pytest.fixture
def mock_sql_version():
    """
    Fixture that returns a mock SQL version manager.
    """
    mock = MagicMock()
    mock.version = "1.0.0"
    mock.set_version.return_value = True
    return mock


@pytest.fixture
def mock_config_manager():
    """
    Fixture that returns a mock config manager.
    """
    mock = MagicMock()

    # Mock the get method
    def mock_get(section, key, default):
        config_values = {
            ("Query", "language", "ppl"): "ppl",
            ("Query", "format", "table"): "table",
            ("Connection", "endpoint", ""): "",
            ("Connection", "username", ""): "",
            ("Connection", "password", ""): "",
        }
        return config_values.get((section, key, default), default)

    mock.get.side_effect = mock_get

    # Mock the get_boolean method
    def mock_get_boolean(section, key, default):
        boolean_values = {
            ("Connection", "insecure", False): False,
            ("Connection", "aws_auth", False): False,
            ("Query", "vertical", False): False,
        }
        return boolean_values.get((section, key, default), default)

    mock.get_boolean.side_effect = mock_get_boolean

    return mock


@pytest.fixture
def mock_console():
    """
    Fixture that returns a mock console.
    """
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_figlet():
    """
    Fixture that returns a mock figlet.
    """
    mock = MagicMock()
    mock.return_value = "OpenSearch"
    return mock


@pytest.fixture
def mock_saved_queries():
    """
    Fixture that returns a mock SavedQueries instance.
    """
    mock = MagicMock()
    # Configure the loading_query mock to return expected values for tests
    mock.loading_query.return_value = (True, "select * from test", "result", "SQL")
    return mock


@pytest.fixture
def interactive_shell(mock_sql_connection, mock_saved_queries):
    """
    Fixture that returns an InteractiveShell instance with mocked dependencies.
    """
    from ..interactive_shell import InteractiveShell

    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", MagicMock()
    ):
        shell = InteractiveShell(mock_sql_connection, mock_saved_queries)
        return shell
