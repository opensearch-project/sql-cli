"""
Pytest fixtures for configuration tests.

This module contains shared fixtures for testing the configuration functionality.
"""

import yaml
import pytest
from unittest.mock import patch, mock_open


@pytest.fixture
def mock_config_data():
    """
    Fixture providing mock configuration data.
    """
    return {
        "Connection": {
            "endpoint": "localhost:9200",
            "username": "",
            "password": "",
            "insecure": False,
            "aws_auth": False,
        },
        "Query": {
            "language": "ppl",
            "format": "table",
            "vertical": False,
            "version": "",
        },
        "SqlSettings": {"QUERY_SIZE_LIMIT": 200, "FIELD_TYPE_TOLERANCE": True},
    }


@pytest.fixture
def mock_config_file(mock_config_data):
    """
    Fixture providing a mock for the open function when reading config file.
    """
    mock_file = mock_open(read_data=yaml.dump(mock_config_data))
    with patch("builtins.open", mock_file):
        yield mock_file
