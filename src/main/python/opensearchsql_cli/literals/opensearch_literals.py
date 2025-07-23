"""
OpenSearch Literals

This module provides access to OpenSearch SQL and PPL keywords and functions for auto-completion.
"""

import os
import json
from rich.text import Text


class Literals:
    """Class for handling OpenSearch literals (keywords and functions)."""

    @staticmethod
    def get_literals(language="ppl"):
        """Parse literals JSON file based on language (sql or ppl).

        Args:
            language: The query language, either 'sql' or 'ppl' (default: 'ppl')

        Returns:
            A dict that is parsed from the corresponding literals JSON file
        """
        package_root = os.path.dirname(__file__)

        # Use different JSON files based on language
        if language.lower() == "ppl":
            literal_file = os.path.join(package_root, "opensearch_literals_ppl.json")
        else:
            literal_file = os.path.join(package_root, "opensearch_literals_sql.json")

        with open(literal_file) as f:
            literals = json.load(f)
            return literals

    @staticmethod
    def colorize_keywords(text, literals):
        """Colorize keywords and functions in the text.

        Args:
            text: The text to colorize
            literals: The literals dict containing keywords and functions

        Returns:
            The text with keywords and functions colorized
        """
        # Get keywords and functions
        keywords = literals.get("keywords", [])
        functions = literals.get("functions", [])

        # Convert text to lowercase for case-insensitive matching
        text_lower = text.lower()

        # Check if the text matches any keyword or function
        for keyword in keywords:
            if text_lower == keyword.lower():
                return Text(text, style="bold green")

        for function in functions:
            if text_lower == function.lower():
                return Text(text, style="green")

        return text
