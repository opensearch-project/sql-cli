# OpenSearch SQL CLI Test Suite

This directory contains the test suite for the OpenSearch SQL CLI project. The tests are organized to validate the functionality of various components of the CLI tool, ensuring that it works correctly and reliably.

## Test Structure

The test suite is organized into the following structure:

```
tests/
├── __init__.py             # Package initialization
├── conftest.py             # Main pytest configuration and fixtures
├── pytest.init             # Pytest initialization file
├── test_interactive.py     # Tests for interactive shell functionality
├── test_main_commands.py   # Tests for main CLI commands
├── config/                 # Tests for configuration functionality
│   ├── __init__.py
│   ├── conftest.py         # Config-specific fixtures
│   └── test_config.py
├── literals/               # Tests for literals functionality
│   ├── __init__.py
│   ├── conftest.py         # Literals-specific fixtures
│   └── test_literals.py
├── query/                  # Tests for query functionality
│   ├── __init__.py
│   ├── conftest.py         # Query-specific fixtures
│   ├── test_query.py
│   └── test_saved_queries.py
└── sql/                    # Tests for SQL functionality
    ├── vcr_caessettes      # all saved HTTP responses for testing
    ├── __init__.py
    ├── conftest.py         # SQL-specific fixtures
    ├── test_sql_connection.py
    ├── test_sql_library.py
    ├── test_sql_version.py
    └── test_verify_cluster.py
```

## Test Components

The test suite covers the following components:

1. **Main Commands**: Tests for the main CLI commands and their behavior.

2. **Interactive Shell**: Tests for the interactive shell functionality, including command processing, query execution, and user interface elements.

3. **Configuration**: Tests for configuration loading, saving, and validation.

4. **Literals**: Tests for SQL and PPL literals handling and auto-completion.

5. **Query**: Tests for query execution, results formatting, and saved queries functionality.

6. **SQL**: Tests for SQL connection, library management, version handling, and cluster verification.

## Test Dependencies

The test suite uses the following dependencies:

1. **pytest**: The main testing framework.
2. **unittest.mock**: For mocking objects and functions during testing.
3. **Various fixtures**: Defined in `conftest.py` files to provide common test setup for each test.
4. **vcrpy**: For capturing real HTTP requests and reuse for testing

## Running Tests

To run the tests, you can use pytest from the project root directory:

```bash
# Run all tests
pytest src/main/python/opensearchsql_cli/tests/

# Run specific test file
pytest src/main/python/opensearchsql_cli/tests/test_main_commands.py

# Run specific test class
pytest src/main/python/opensearchsql_cli/tests/test_main_commands.py::TestCommands

# Run specific test method
pytest src/main/python/opensearchsql_cli/tests/test_main_commands.py::TestCommands::test_endpoint_command
```

## Warning Filters

The test suite includes warning filters defined in `pytest.init` to suppress specific deprecation warnings that are not relevant to the test functionality. These filters help keep the test output clean and focused on actual test results.

The following warnings are filtered:

```
[pytest]
filterwarnings =
    ignore::DeprecationWarning:requests_aws4auth.*
    ignore::DeprecationWarning:pkg_resources.*
    ignore::DeprecationWarning:typer.params.*
    ignore::DeprecationWarning:pyfiglet.*
    ignore:pkg_resources is deprecated as an API:DeprecationWarning
    ignore:The 'is_flag' and 'flag_value' parameters are not supported by Typer:DeprecationWarning
    ignore:datetime.datetime.utcnow.*:DeprecationWarning
```

These filters suppress deprecation warnings from third-party libraries that are used in the project but are not directly related to the functionality being tested.

## Writing New Tests

When writing new tests for the OpenSearch SQL CLI, follow these guidelines:

1. **Test Organization**: Place your tests in the appropriate subdirectory based on the component being tested.

2. **Test Classes**: Use classes to group related tests together, following the naming convention `Test<ComponentName>`.

3. **Test Methods**: Name test methods descriptively, starting with `test_` prefix.

4. **Fixtures**: Use fixtures from the appropriate `conftest.py` file to set up test dependencies.

5. **Parameterization**: Use `@pytest.mark.parametrize` for testing multiple scenarios with the same test logic.

6. **Documentation**: Include docstrings for test classes and methods to explain what they're testing.

Example:

```python
"""
Tests for Example Component.

This module contains tests for the ExampleComponent class.
"""

import pytest
from unittest.mock import patch, MagicMock

from ..example_component import ExampleComponent


class TestExampleComponent:
    """
    Test class for ExampleComponent functionality.
    """

    def test_init(self):
        """Test initialization of ExampleComponent."""
        component = ExampleComponent()
        assert component.attribute == expected_value

    @pytest.mark.parametrize(
        "input_value, expected_output",
        [
            ("value1", "result1"),
            ("value2", "result2"),
        ],
    )
    def test_method(self, input_value, expected_output):
        """Test method behavior with different inputs."""
        component = ExampleComponent()
        result = component.method(input_value)
        assert result == expected_output
```

## Mocking Strategy

The test suite uses extensive mocking to isolate components during testing. The main mocking strategies include:

1. **Mock Objects**: Using `MagicMock` to create mock objects that simulate the behavior of real objects.

2. **Patching**: Using `patch` to temporarily replace classes or functions with mock objects during testing.

3. **Fixtures**: Using pytest fixtures to provide common mock objects across tests.

## Test Coverage

The test suite aims to cover all critical functionality of the OpenSearch SQL CLI, including:

- Command-line argument parsing
- Configuration management
- Connection handling
- Query execution and results formatting
- Interactive shell functionality
- Error handling

When adding new features to the CLI, ensure that appropriate tests are added to maintain test coverage.
