"""
Error Formatting

This module provides functionality for formatting enhanced error reports from OpenSearch SQL/PPL.
Inspired by the color-eyre Rust crate for beautiful error display.
"""

import json
from typing import Optional, Dict, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape

# Create a console instance for rich formatting
console = Console()


class ErrorFormatter:
    """
    Class for formatting enhanced error reports from OpenSearch SQL/PPL
    """

    @staticmethod
    def is_error_report(error_json: Dict[str, Any]) -> bool:
        """
        Check if the error JSON is an enhanced ErrorReport

        Args:
            error_json: Parsed error JSON

        Returns:
            bool: True if this is an enhanced ErrorReport, False otherwise
        """
        if not isinstance(error_json, dict):
            return False

        error = error_json.get("error", {})
        if not isinstance(error, dict):
            return False

        return error.get("type") == "ErrorReport"

    @staticmethod
    def format_query_with_cursor(query: str, position: Dict[str, int], offending_token: Optional[str] = None) -> Tuple[str, str]:
        """
        Format a query with a cursor pointing at the error position

        Args:
            query: The query string
            position: Dictionary with 'line' and 'column' keys (1-indexed)
            offending_token: Optional offending token to highlight

        Returns:
            tuple: (query_line, cursor_line) formatted strings
        """
        line_num = position.get("line", 1)
        column = position.get("column", 1)

        # Split query into lines
        lines = query.split("\n")

        # Get the line with the error (convert to 0-indexed)
        if line_num > 0 and line_num <= len(lines):
            error_line = lines[line_num - 1]
        else:
            # Fallback to the whole query if line number is invalid
            error_line = query

        # Create the cursor line with spaces and carets pointing at the error
        # Column is 1-indexed in the error report
        # We want the cursor to point exactly at that column
        cursor_position = column

        # If we have an offending token, span the cursor across it
        if offending_token:
            token_length = len(offending_token)
            cursor_line = " " * cursor_position + "^" * token_length
        else:
            # Just use a single caret
            cursor_line = " " * cursor_position + "^"

        return error_line, cursor_line

    @staticmethod
    def format_error_report(error_json: Dict[str, Any], original_query: Optional[str] = None) -> Text:
        """
        Format an enhanced ErrorReport into a beautiful, readable format

        Args:
            error_json: Parsed error JSON containing an ErrorReport
            original_query: Optional original query string (used if not in error context)

        Returns:
            Text: Rich Text object with formatted error
        """
        error = error_json.get("error", {})

        # Extract error components
        error_code = error.get("code", "UNKNOWN_ERROR")
        reason = error.get("reason", "Error")
        details = error.get("details", "")
        location = error.get("location", [])
        context = error.get("context", {})
        suggestion = error.get("suggestion", "")

        # Build the formatted output
        result = Text()

        # Error header with code
        result.append("Error", style="bold red")
        result.append(f" [{error_code}]", style="bold yellow")
        result.append("\n")

        # Location breadcrumb if available
        if location and isinstance(location, list):
            location_text = " → ".join(location)
            result.append("  ", style="dim")
            result.append(location_text, style="dim cyan")
            result.append("\n\n")

        # Query with cursor if position is available
        query = context.get("query") or original_query
        position = context.get("position")
        offending_token = context.get("offending_token")
        field_name = context.get("field_name")

        if query and position:
            result.append("  ", style="dim")
            result.append("Query:\n", style="bold white")

            # Use field_name for cursor width if available and no offending_token
            cursor_token = offending_token or field_name
            query_line, cursor_line = ErrorFormatter.format_query_with_cursor(query, position, cursor_token)

            # Display the query line
            result.append("    ")
            result.append(query_line, style="white")
            result.append("\n")

            # Display the cursor pointing at the error
            result.append("    ")
            result.append(cursor_line, style="bold red")
            result.append("\n\n")

        # Error details in a hierarchical format
        result.append("  ", style="dim")
        result.append("Details:\n", style="bold white")
        result.append("    ")
        # No need to escape when using Text.append() - it doesn't interpret markup
        result.append(details, style="red")
        result.append("\n")

        # Additional context information
        offending_token = context.get("offending_token")
        if offending_token:
            result.append("\n  ")
            result.append("Offending token: ", style="bold white")
            result.append(f"'{offending_token}'", style="yellow")
            result.append("\n")

        field_name = context.get("field_name")
        if field_name:
            result.append("\n  ")
            result.append("Field: ", style="bold white")
            result.append(f"'{field_name}'", style="yellow")
            result.append("\n")

        available_fields = context.get("available_fields")
        if available_fields and isinstance(available_fields, list):
            result.append("\n  ")
            result.append("Available fields: ", style="bold white")
            # Show first few fields
            fields_to_show = available_fields[:10]
            result.append(", ".join(f"'{f}'" for f in fields_to_show), style="dim cyan")
            if len(available_fields) > 10:
                result.append(f", ...{len(available_fields) - 10} more", style="dim")
            result.append("\n")

        fields_command_used = context.get("fields_command_used")
        if fields_command_used:
            result.append("\n  ")
            result.append("Note: ", style="bold yellow")
            result.append("A 'fields' command was used earlier in the query, which limited the available fields.", style="yellow")
            result.append("\n")

        # Suggestion at the end
        if suggestion:
            result.append("\n  ")
            result.append("Suggestion:\n", style="bold green")
            result.append("    ")
            # No need to escape when using Text.append() - it doesn't interpret markup
            result.append(suggestion, style="green")
            result.append("\n")

        return result

    @staticmethod
    def format_error(error_response: str, print_function=None, original_query: Optional[str] = None) -> bool:
        """
        Format an error response. If it's an enhanced ErrorReport, format it beautifully.
        Otherwise, return False to use default error handling.

        Args:
            error_response: Raw error response string (may include "Exception: " prefix)
            print_function: Function to use for printing (default: console.print)
            original_query: Optional original query string (used if not in error context)

        Returns:
            bool: True if this was an ErrorReport and was formatted, False otherwise
        """
        if print_function is None:
            print_function = console.print

        try:
            # Remove "Exception: " prefix if present
            error_str = error_response
            if error_str.startswith("Exception: "):
                error_str = error_str[len("Exception: "):]

            # Try to parse as JSON
            error_json = json.loads(error_str)

            # Check if it's an ErrorReport
            if not ErrorFormatter.is_error_report(error_json):
                return False

            # Format the error report
            formatted = ErrorFormatter.format_error_report(error_json, original_query)

            # Create a panel with the formatted error
            panel = Panel(
                formatted,
                title="[bold red]Query Error[/bold red]",
                border_style="red",
                padding=(1, 2),
            )

            # Print directly using the provided function
            print_function(panel)

            return True

        except (json.JSONDecodeError, KeyError, TypeError):
            # Not a JSON error or not an ErrorReport
            return False
