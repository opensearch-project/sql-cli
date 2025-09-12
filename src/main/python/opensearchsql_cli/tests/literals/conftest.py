"""
Pytest fixtures for literals tests.

This module contains shared fixtures for testing the literals functionality.
"""

import os
import json
import pytest
from unittest.mock import patch, mock_open


@pytest.fixture
def mock_ppl_literals_data():
    """
    Fixture providing mock PPL literals data.
    """
    return {
        "keywords": ["source", "where", "fields"],
        "functions": ["count", "sum", "avg"],
    }


@pytest.fixture
def mock_sql_literals_data():
    """
    Fixture providing mock SQL literals data.
    """
    return {
        "keywords": ["SELECT", "FROM", "WHERE"],
        "functions": ["COUNT", "SUM", "AVG"],
    }


@pytest.fixture
def mock_literals_file(request):
    """
    Fixture providing a mock for the open function when reading literals files.

    Args:
        request: The pytest request object with a 'param' attribute specifying
                 which literals to use ('ppl' or 'sql')
    """
    language = request.param if hasattr(request, "param") else "sql"

    if language.lower() == "ppl":
        mock_data = {
            "keywords": ["source", "where", "fields"],
            "functions": ["count", "sum", "avg"],
        }
    else:  # sql
        mock_data = {
            "keywords": ["SELECT", "FROM", "WHERE"],
            "functions": ["COUNT", "SUM", "AVG"],
        }

    mock_file = mock_open(read_data=json.dumps(mock_data))
    with patch("builtins.open", mock_file):
        yield mock_file
