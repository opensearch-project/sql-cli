"""
Tests for the error_formatter module.

This module contains tests for the enhanced error formatting functionality.
"""

import pytest
import json
from unittest.mock import MagicMock
from opensearchsql_cli.query.error_formatter import ErrorFormatter
from rich.text import Text


class TestErrorFormatter:
    """
    Test class for ErrorFormatter methods.
    """

    def test_is_error_report_valid(self, mock_error_report_syntax):
        """Test that is_error_report correctly identifies valid ErrorReports"""
        error_json = json.loads(mock_error_report_syntax.split("Exception: ", 1)[1])
        assert ErrorFormatter.is_error_report(error_json) is True

    def test_is_error_report_legacy_error(self, mock_syntax_error_response):
        """Test that is_error_report returns False for legacy errors"""
        # Legacy errors are just strings, not JSON
        assert ErrorFormatter.is_error_report(mock_syntax_error_response) is False

    def test_is_error_report_non_error_report_json(self):
        """Test that is_error_report returns False for JSON that isn't an ErrorReport"""
        non_error_json = {
            "error": {
                "type": "SomeOtherError",
                "message": "Something went wrong"
            }
        }
        assert ErrorFormatter.is_error_report(non_error_json) is False

    def test_is_error_report_invalid_structure(self):
        """Test that is_error_report handles invalid structures gracefully"""
        assert ErrorFormatter.is_error_report({}) is False
        assert ErrorFormatter.is_error_report({"error": "string"}) is False
        assert ErrorFormatter.is_error_report("not a dict") is False
        assert ErrorFormatter.is_error_report(None) is False

    def test_format_query_with_cursor_simple(self):
        """Test cursor formatting with simple single-line query"""
        query = "source=big5 | fieldz message"
        position = {"line": 1, "column": 14}
        offending_token = "fieldz"

        query_line, cursor_line = ErrorFormatter.format_query_with_cursor(
            query, position, offending_token
        )

        assert query_line == "source=big5 | fieldz message"
        assert cursor_line == "              ^^^^^^"  # 14 spaces + 6 carets

    def test_format_query_with_cursor_no_token(self):
        """Test cursor formatting without offending token (single caret)"""
        query = "source=big5 | fields message"
        position = {"line": 1, "column": 20}

        query_line, cursor_line = ErrorFormatter.format_query_with_cursor(
            query, position, None
        )

        assert query_line == "source=big5 | fields message"
        assert cursor_line == "                    ^"  # 20 spaces + 1 caret

    def test_format_query_with_cursor_multiline(self):
        """Test cursor formatting with multi-line query"""
        query = "source=big5\n| where host.name = 'test'\n| fields message"
        position = {"line": 2, "column": 8}
        offending_token = "host.name"

        query_line, cursor_line = ErrorFormatter.format_query_with_cursor(
            query, position, offending_token
        )

        assert query_line == "| where host.name = 'test'"
        assert cursor_line == "        ^^^^^^^^^"  # 8 spaces + 9 carets

    def test_format_query_with_cursor_field_name(self):
        """Test cursor formatting with field name (for field errors)"""
        query = "source=big5 | fields messag"
        position = {"line": 1, "column": 21}
        field_name = "messag"

        query_line, cursor_line = ErrorFormatter.format_query_with_cursor(
            query, position, field_name
        )

        assert query_line == "source=big5 | fields messag"
        assert cursor_line == "                     ^^^^^^"  # 21 spaces + 6 carets

    def test_format_error_report_syntax_error(self, mock_error_report_syntax):
        """Test formatting of syntax error ErrorReport"""
        error_json = json.loads(mock_error_report_syntax.split("Exception: ", 1)[1])

        result = ErrorFormatter.format_error_report(error_json)

        assert isinstance(result, Text)
        result_str = result.plain
        assert "Error [SYNTAX_ERROR]" in result_str
        assert "while parsing the query" in result_str
        assert "source=big5 | fieldz message" in result_str
        assert "^^^^^^" in result_str  # Cursor for "fieldz"
        assert "[fieldz] is not a valid term" in result_str
        assert "Offending token: 'fieldz'" in result_str
        assert "Expected one of 48 possible tokens" in result_str

    def test_format_error_report_field_error_with_query(self, mock_error_report_field):
        """Test formatting of field error ErrorReport with original query"""
        error_json = json.loads(mock_error_report_field.split("Exception: ", 1)[1])
        original_query = "source=big5 | fields messag"

        result = ErrorFormatter.format_error_report(error_json, original_query)

        assert isinstance(result, Text)
        result_str = result.plain
        assert "Error [FIELD_NOT_FOUND]" in result_str
        assert "while resolving field references" in result_str
        assert "source=big5 | fields messag" in result_str
        assert "^^^^^^" in result_str  # Cursor for "messag"
        assert "Field [messag] not found" in result_str
        assert "Field: 'messag'" in result_str
        assert "Available fields:" in result_str
        assert "Did you mean: 'message'?" in result_str

    def test_format_error_report_field_error_without_query(self, mock_error_report_field):
        """Test formatting of field error ErrorReport without original query"""
        error_json = json.loads(mock_error_report_field.split("Exception: ", 1)[1])

        result = ErrorFormatter.format_error_report(error_json)

        assert isinstance(result, Text)
        result_str = result.plain
        assert "Error [FIELD_NOT_FOUND]" in result_str
        # Should not have Query section or cursor
        assert "Query:" not in result_str
        assert "^^^^^^" not in result_str

    def test_format_error_report_field_removed(self, mock_error_report_field_removed):
        """Test formatting of field removed by fields command error"""
        error_json = json.loads(mock_error_report_field_removed.split("Exception: ", 1)[1])
        original_query = "source=big5 | fields message | where host.name = 'test'"

        result = ErrorFormatter.format_error_report(error_json, original_query)

        assert isinstance(result, Text)
        result_str = result.plain
        assert "Error [FIELD_NOT_FOUND]" in result_str
        assert "Field: 'host.name'" in result_str
        assert "Available fields: 'message'" in result_str
        assert "Note:" in result_str
        assert "fields' command" in result_str

    def test_format_error_success(self, mock_error_report_syntax):
        """Test that format_error returns True for valid ErrorReport"""
        mock_print = MagicMock()

        result = ErrorFormatter.format_error(
            mock_error_report_syntax,
            mock_print,
            None
        )

        assert result is True
        assert mock_print.call_count == 1
        # Check that a Panel was printed
        call_args = mock_print.call_args[0]
        assert len(call_args) > 0

    def test_format_error_with_original_query(self, mock_error_report_field):
        """Test that format_error passes original query correctly"""
        mock_print = MagicMock()
        original_query = "source=big5 | fields messag"

        result = ErrorFormatter.format_error(
            mock_error_report_field,
            mock_print,
            original_query
        )

        assert result is True
        assert mock_print.call_count == 1

    def test_format_error_legacy_error(self, mock_syntax_error_response):
        """Test that format_error returns False for legacy errors"""
        mock_print = MagicMock()

        result = ErrorFormatter.format_error(
            mock_syntax_error_response,
            mock_print,
            None
        )

        assert result is False
        assert mock_print.call_count == 0

    def test_format_error_invalid_json(self):
        """Test that format_error returns False for invalid JSON"""
        mock_print = MagicMock()

        result = ErrorFormatter.format_error(
            "Exception: not valid json {bad}",
            mock_print,
            None
        )

        assert result is False
        assert mock_print.call_count == 0

    def test_format_error_non_error_report_json(self):
        """Test that format_error returns False for non-ErrorReport JSON"""
        mock_print = MagicMock()
        error_response = """Exception: {
            "error": {
                "type": "SomeOtherError",
                "message": "Something went wrong"
            }
        }"""

        result = ErrorFormatter.format_error(
            error_response,
            mock_print,
            None
        )

        assert result is False
        assert mock_print.call_count == 0
